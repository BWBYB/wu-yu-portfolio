"""Search the local BM25 index and print source-grounded chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .bm25 import BM25Index


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query")
    parser.add_argument("--index-dir", type=Path, default=PROJECT_ROOT / "artifacts/bm25-v1")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    index = BM25Index.load(args.index_dir)
    results = index.search(args.query, top_k=args.top_k)
    if args.as_json:
        print(
            json.dumps(
                [
                    {
                        "score": result.score,
                        "rank": result.rank,
                        "retriever": result.retriever,
                        "source": result.chunk.to_dict(),
                    }
                    for result in results
                ],
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    for result in results:
        chunk = result.chunk
        heading = " > ".join(chunk.heading_path) or "(document root)"
        print(
            f"[{result.rank}] score={result.score:.4f} {chunk.file}#{chunk.chunk_index} · {heading}"
        )
        print(chunk.text.strip())
        print()


if __name__ == "__main__":
    main()
