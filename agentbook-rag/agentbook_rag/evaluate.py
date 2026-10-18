"""Run E0-E4 retrieval benchmarks and calculate ranking metrics with ranx."""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
from ranx import Qrels, Run, evaluate

from .agentic import search_with_query_rewrites
from .bm25 import BM25Index
from .embedding import DEFAULT_MODEL, QwenEmbedder
from .index import NumpyIndex, RetrievalResult
from .parallel import ParallelRetriever
from .reranker import CrossEncoderReranker, DEFAULT_RERANKER_MODEL
from .rrf import reciprocal_rank_fusion
from .validate_questions import validate_questions


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUESTIONS = PROJECT_ROOT / "evaluation/questions.v0.jsonl"
DEFAULT_DENSE_INDEX = PROJECT_ROOT / "artifacts/qwen-dense-v1"
DEFAULT_BM25_INDEX = PROJECT_ROOT / "artifacts/bm25-v1"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "artifacts/evaluation"
METRICS = (
    "recall@5",
    "recall@10",
    "recall@20",
    "hit_rate@5",
    "hit_rate@10",
    "hit_rate@20",
    "mrr@10",
    "ndcg@10",
)
CONFIGS = ("E0", "E1", "E2", "E3")


def _load_questions(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _load_rewrites(path: Path | None, question_ids: set[str]) -> dict[str, list[str]]:
    if path is None:
        return {}
    records = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rewrites: dict[str, list[str]] = {}
    for record in records:
        question_id = record.get("id")
        values = record.get("rewrites")
        if question_id not in question_ids:
            raise ValueError(f"rewrite file contains unknown question id: {question_id}")
        if question_id in rewrites:
            raise ValueError(f"rewrite file contains duplicate question id: {question_id}")
        if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
            raise ValueError(f"rewrites for {question_id} must be a string array")
        rewrites[question_id] = values
    missing = question_ids - rewrites.keys()
    if missing:
        raise ValueError(f"rewrite file is missing question ids: {sorted(missing)}")
    return rewrites


def document_id(result: RetrievalResult) -> str:
    """Return the stable qrels/run document ID for a retrieved chunk."""
    return f"{result.chunk.file}#{result.chunk.chunk_index}"


def _serialize_result(result: RetrievalResult) -> dict[str, Any]:
    return {
        "doc_id": document_id(result),
        "score": result.score,
        "rank": result.rank,
        "retriever": result.retriever,
        "dense_rank": result.dense_rank,
        "bm25_rank": result.bm25_rank,
    }


def _run_dict(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, float]]:
    return {
        question_id: {
            result["doc_id"]: float(result["score"])
            for result in record["results"]
        }
        for question_id, record in ((record["question_id"], record) for record in records)
    }


def _qrels_dict(questions: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    return {
        question["id"]: {chunk_id: 1 for chunk_id in question["gold_chunk_ids"]}
        for question in questions
        if question["gold_chunk_ids"]
    }


def _percentile(values: list[float], percentile: float) -> float | None:
    return round(float(np.percentile(values, percentile)), 3) if values else None


def _required_evidence_metrics(
    questions: list[dict[str, Any]],
    records: list[dict[str, Any]],
    *,
    cutoffs: tuple[int, ...] = (5, 20),
) -> dict[str, dict[str, float | int]]:
    """Measure multi-evidence coverage without treating one hit as complete."""
    questions_by_id = {
        question["id"]: question
        for question in questions
        if question["gold_chunk_ids"]
    }
    values: dict[str, dict[str, float | int]] = {}
    for cutoff in cutoffs:
        coverages: list[float] = []
        complete = 0
        for record in records:
            question = questions_by_id.get(record["question_id"])
            if question is None:
                continue
            gold = set(question["gold_chunk_ids"])
            retrieved = {
                result["doc_id"]
                for result in record.get("results", [])[:cutoff]
            }
            coverage = len(gold & retrieved) / len(gold)
            coverages.append(coverage)
            complete += coverage == 1.0
        values[f"@{cutoff}"] = {
            "mean_coverage": round(float(np.mean(coverages)), 6) if coverages else 0.0,
            "complete_rate": round(complete / len(coverages), 6) if coverages else 0.0,
            "question_count": len(coverages),
        }
    return values


def _metrics(
    questions: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    qrels_data = _qrels_dict(questions)
    eligible_ids = set(qrels_data)
    eligible_records = [record for record in records if record["question_id"] in eligible_ids]
    runs = _run_dict(eligible_records)
    if not runs:
        return {"overall": {}, "by_type": {}}

    qrels = Qrels(qrels_data)
    run = Run(runs)
    overall = {
        metric: round(float(evaluate(qrels, run, metric)), 6)
        for metric in METRICS
    }
    by_type: dict[str, dict[str, float]] = {}
    questions_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for question in questions:
        if question["id"] in eligible_ids:
            questions_by_type[question["type"]].append(question)
    records_by_id = {record["question_id"]: record for record in eligible_records}
    for question_type, typed_questions in sorted(questions_by_type.items()):
        typed_qrels = _qrels_dict(typed_questions)
        typed_runs = {
            question["id"]: runs[question["id"]]
            for question in typed_questions
            if question["id"] in runs
        }
        typed_qrels_obj = Qrels(typed_qrels)
        typed_run_obj = Run(typed_runs)
        by_type[question_type] = {
            metric: round(float(evaluate(typed_qrels_obj, typed_run_obj, metric)), 6)
            for metric in METRICS
        }
    return {
        "overall": overall,
        "by_type": by_type,
        "required_evidence": _required_evidence_metrics(questions, eligible_records),
    }


def _timing(records: list[dict[str, Any]]) -> dict[str, float | None]:
    latencies = [float(record["latency_ms"]) for record in records]
    return {
        "p50_ms": _percentile(latencies, 50),
        "p95_ms": _percentile(latencies, 95),
    }


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def run_benchmark(
    questions_path: Path,
    *,
    dense_index_path: Path = DEFAULT_DENSE_INDEX,
    bm25_index_path: Path = DEFAULT_BM25_INDEX,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    candidate_k: int = 20,
    context_k: int = 5,
    reranker_model: str = DEFAULT_RERANKER_MODEL,
    rewrite_path: Path | None = None,
    max_rewrites: int = 2,
) -> dict[str, Any]:
    """Run all retrieval configurations and save machine-readable artifacts."""
    if candidate_k <= 0 or context_k <= 0 or context_k > candidate_k:
        raise ValueError("candidate_k must be >= context_k and both must be positive")
    validation = validate_questions(questions_path, dense_index_path)
    questions = _load_questions(questions_path)
    rewrites_by_id = _load_rewrites(rewrite_path, {question["id"] for question in questions})
    dense_index = NumpyIndex.load(dense_index_path)
    bm25_index = BM25Index.load(bm25_index_path)
    embedder = QwenEmbedder(model_name=dense_index.manifest.get("model", DEFAULT_MODEL))
    parallel = ParallelRetriever(dense_index=dense_index, bm25_index=bm25_index, embedder=embedder)
    reranker = CrossEncoderReranker(model_name=reranker_model)

    configs = (*CONFIGS, "E4") if rewrite_path is not None else CONFIGS
    records_by_config: dict[str, list[dict[str, Any]]] = {config: [] for config in configs}
    for question in questions:
        question_id = question["id"]
        query = question["question"]

        started = time.perf_counter()
        query_embedding = embedder.encode_query(query).numpy()
        dense_results = dense_index.search(query_embedding, top_k=candidate_k)
        dense_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        bm25_results = bm25_index.search(query, top_k=candidate_k)
        bm25_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        parallel_results = parallel.search(query, top_k=candidate_k)
        rrf_results = reciprocal_rank_fusion(
            parallel_results.dense,
            parallel_results.bm25,
            top_k=candidate_k,
        )
        hybrid_ms = (time.perf_counter() - started) * 1000

        started = time.perf_counter()
        reranked_results = reranker.rerank(query, rrf_results, top_k=None)
        rerank_ms = (time.perf_counter() - started) * 1000

        result_sets: dict[str, tuple[list[RetrievalResult], float, float | None, Any | None]] = {
            "E0": (dense_results, dense_ms, None, None),
            "E1": (bm25_results, bm25_ms, None, None),
            "E2": (rrf_results, hybrid_ms, None, None),
            "E3": (reranked_results, hybrid_ms + rerank_ms, rerank_ms, None),
        }
        if rewrite_path is not None:
            started = time.perf_counter()
            agentic = search_with_query_rewrites(
                query,
                rewrites_by_id[question_id],
                parallel,
                reranker,
                candidate_k=candidate_k,
                top_k=candidate_k,
                rrf_k=60,
                max_rewrites=max_rewrites,
            )
            agentic_ms = (time.perf_counter() - started) * 1000
            result_sets["E4"] = (agentic.reranked, agentic_ms, None, agentic)
        for config, (results, latency_ms, rerank_latency_ms, agentic) in result_sets.items():
            queries = list(agentic.queries) if agentic is not None else [query]
            records_by_config[config].append(
                {
                    "config": config,
                    "question_id": question_id,
                    "question": query,
                    "type": question["type"],
                    "gold_chunk_ids": question["gold_chunk_ids"],
                    "latency_ms": round(latency_ms, 3),
                    "rerank_latency_ms": (
                        round(rerank_latency_ms, 3) if rerank_latency_ms is not None else None
                    ),
                    "queries": queries,
                    "rewrite_count": max(0, len(queries) - 1),
                    "fused_context_doc_ids": (
                        [document_id(result) for result in agentic.fused[:context_k]]
                        if agentic is not None
                        else None
                    ),
                    "context_doc_ids": [
                        document_id(result) for result in results[:context_k]
                    ],
                    "results": [_serialize_result(result) for result in results],
                }
            )

    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S")
    manifest = {
        "run_id": run_id,
        "question_set": str(questions_path),
        "question_set_summary": validation,
        "candidate_k": candidate_k,
        "context_k": context_k,
        "reranker_model": reranker_model,
        "configs": list(configs),
        "rewrite_file": str(rewrite_path) if rewrite_path is not None else None,
        "max_rewrites": max_rewrites if rewrite_path is not None else None,
        "metrics": list(METRICS),
        "status": "smoke_benchmark" if questions_path.name.endswith("v0.jsonl") else "benchmark",
    }
    summary: dict[str, Any] = {"manifest": manifest, "configs": {}}
    for config, records in records_by_config.items():
        _write_jsonl(output_dir / f"{run_id}-{config}.jsonl", records)
        summary["configs"][config] = {
            "timing": _timing(records),
            "metrics": _metrics(questions, records),
            "record_count": len(records),
        }
    (output_dir / f"{run_id}-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--dense-index", type=Path, default=DEFAULT_DENSE_INDEX)
    parser.add_argument("--bm25-index", type=Path, default=DEFAULT_BM25_INDEX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--context-k", type=int, default=5)
    parser.add_argument("--reranker-model", default=DEFAULT_RERANKER_MODEL)
    parser.add_argument("--rewrites", type=Path, default=None)
    parser.add_argument("--max-rewrites", type=int, default=2)
    args = parser.parse_args()
    summary = run_benchmark(
        args.questions,
        dense_index_path=args.dense_index,
        bm25_index_path=args.bm25_index,
        output_dir=args.output_dir,
        candidate_k=args.candidate_k,
        context_k=args.context_k,
        reranker_model=args.reranker_model,
        rewrite_path=args.rewrites,
        max_rewrites=args.max_rewrites,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
