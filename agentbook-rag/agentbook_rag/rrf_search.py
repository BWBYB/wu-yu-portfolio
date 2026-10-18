"""Run parallel retrieval and print the RRF-fused candidate list."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bm25 import BM25Index
from .embedding import DEFAULT_MODEL, QwenEmbedder
from .index import NumpyIndex, RetrievalResult
from .parallel import ParallelRetriever
from .rrf import reciprocal_rank_fusion


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _serialize(results: list[RetrievalResult]) -> list[dict[str, object]]:
    return [
        {
            "score": result.score,
            "rank": result.rank,
            "retriever": result.retriever,
            "dense_rank": result.dense_rank,
            "bm25_rank": result.bm25_rank,
            "source": result.chunk.to_dict(),
        }
        for result in results
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument(
        "--dense-index", type=Path, default=PROJECT_ROOT / "artifacts/qwen-dense-v1"
    )
    parser.add_argument("--bm25-index", type=Path, default=PROJECT_ROOT / "artifacts/bm25-v1")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    dense_index = NumpyIndex.load(args.dense_index)
    bm25_index = BM25Index.load(args.bm25_index)
    model_name = dense_index.manifest.get("model", DEFAULT_MODEL)
    parallel = ParallelRetriever(
        dense_index=dense_index,
        bm25_index=bm25_index,
        embedder=QwenEmbedder(model_name=model_name),
    ).search(args.query, top_k=args.top_k)
    results = reciprocal_rank_fusion(
        parallel.dense,
        parallel.bm25,
        top_k=args.top_k,
        k=args.rrf_k,
    )
    if args.as_json:
        print(json.dumps({"query": args.query, "rrf": _serialize(results)}, ensure_ascii=False, indent=2))
        return

    print(f"query: {args.query}\n")
    print("== RRF ==")
    for result in results:
        chunk = result.chunk
        heading = " > ".join(chunk.heading_path) or "(document root)"
        print(
            f"[{result.rank}] score={result.score:.6f} "
            f"dense={result.dense_rank or '-'} bm25={result.bm25_rank or '-'} "
            f"{chunk.file}#{chunk.chunk_index} · {heading}"
        )
        print(chunk.text.strip())
        print()


if __name__ == "__main__":
    main()
