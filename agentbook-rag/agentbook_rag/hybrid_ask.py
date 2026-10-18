"""Answer with the complete local Hybrid RAG retrieval chain."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bm25 import BM25Index
from .embedding import DEFAULT_MODEL, QwenEmbedder
from .index import NumpyIndex
from .qa import answer_hybrid_question
from .reranker import DEFAULT_RERANKER_MODEL, CrossEncoderReranker


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument(
        "--dense-index", type=Path, default=PROJECT_ROOT / "artifacts/qwen-dense-v1"
    )
    parser.add_argument("--bm25-index", type=Path, default=PROJECT_ROOT / "artifacts/bm25-v1")
    parser.add_argument("--candidate-k", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--reranker-model", default=DEFAULT_RERANKER_MODEL)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    dense_index = NumpyIndex.load(args.dense_index)
    bm25_index = BM25Index.load(args.bm25_index)
    embedder = QwenEmbedder(model_name=dense_index.manifest.get("model", DEFAULT_MODEL))
    reranker = CrossEncoderReranker(model_name=args.reranker_model)
    result = answer_hybrid_question(
        args.question,
        dense_index,
        bm25_index,
        embedder,
        reranker,
        candidate_k=args.candidate_k,
        top_k=args.top_k,
        rrf_k=args.rrf_k,
        model=args.model,
        base_url=args.base_url,
    )
    print(result.answer)
    print("\nHybrid RAG 来源：")
    for item in result.results:
        chunk = item.chunk
        heading = " > ".join(chunk.heading_path) or "(document root)"
        print(
            f"[{item.rank}] {item.score:.4f} · {chunk.file}#{chunk.chunk_index} · {heading} "
            f"(dense={item.dense_rank or '-'}, bm25={item.bm25_rank or '-'})"
        )


if __name__ == "__main__":
    main()
