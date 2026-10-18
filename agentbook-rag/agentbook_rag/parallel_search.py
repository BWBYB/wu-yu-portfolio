"""Run Dense and BM25 retrieval together and print both result branches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .bm25 import BM25Index
from .embedding import DEFAULT_MODEL, QwenEmbedder
from .index import NumpyIndex, RetrievalResult
from .parallel import ParallelRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _serialize(results: Iterable[RetrievalResult]) -> list[dict[str, object]]:
    return [
        {
            "score": result.score,
            "rank": result.rank,
            "retriever": result.retriever,
            "source": result.chunk.to_dict(),
        }
        for result in results
    ]


def _print_branch(name: str, results: list[RetrievalResult]) -> None:
    print(f"== {name} ==")
    if not results:
        print("(no matches)\n")
        return
    for result in results:
        chunk = result.chunk
        heading = " > ".join(chunk.heading_path) or "(document root)"
        print(
            f"[{result.rank}] score={result.score:.4f} "
            f"{chunk.file}#{chunk.chunk_index} · {heading}"
        )
        print(chunk.text.strip())
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument(
        "--dense-index", type=Path, default=PROJECT_ROOT / "artifacts/qwen-dense-v1"
    )
    parser.add_argument("--bm25-index", type=Path, default=PROJECT_ROOT / "artifacts/bm25-v1")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    dense_index = NumpyIndex.load(args.dense_index)
    bm25_index = BM25Index.load(args.bm25_index)
    model_name = dense_index.manifest.get("model", DEFAULT_MODEL)
    retriever = ParallelRetriever(
        dense_index=dense_index,
        bm25_index=bm25_index,
        embedder=QwenEmbedder(model_name=model_name),
    )
    results = retriever.search(args.query, top_k=args.top_k)
    if args.as_json:
        print(
            json.dumps(
                {
                    "query": results.query,
                    "dense": _serialize(results.dense),
                    "bm25": _serialize(results.bm25),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(f"query: {results.query}\n")
    _print_branch("DENSE", results.dense)
    _print_branch("BM25", results.bm25)


if __name__ == "__main__":
    main()
