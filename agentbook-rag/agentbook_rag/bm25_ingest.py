"""Build a BM25 index from the existing checked-in Dense chunks."""

from __future__ import annotations

import argparse
from pathlib import Path

from .bm25 import BM25Index
from .index import NumpyIndex


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_index(*, source_index_dir: Path, output_dir: Path) -> BM25Index:
    dense_index = NumpyIndex.load(source_index_dir)
    index = BM25Index.from_chunks(
        dense_index.chunks,
        manifest={
            "source_repo": dense_index.manifest.get("source_repo"),
            "source_url": dense_index.manifest.get("source_url"),
            "source_commit": dense_index.manifest.get("source_commit"),
            "source_index": source_index_dir.name,
        },
    )
    index.save(output_dir)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-index",
        type=Path,
        default=PROJECT_ROOT / "artifacts/qwen-dense-v1",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/bm25-v1",
    )
    args = parser.parse_args()
    index = build_index(source_index_dir=args.source_index, output_dir=args.output_dir)
    print(f"built {len(index.chunks)} BM25 chunks -> {args.output_dir}")


if __name__ == "__main__":
    main()
