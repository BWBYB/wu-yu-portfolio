"""Retrieve Agent Book passages and answer through an OpenAI-compatible provider."""

from __future__ import annotations

import argparse
from pathlib import Path

from .embedding import DEFAULT_MODEL, QwenEmbedder
from .index import NumpyIndex
from .qa import answer_question


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument("--index-dir", type=Path, default=PROJECT_ROOT / "artifacts/qwen-dense-v1")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model", default=None)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    index = NumpyIndex.load(args.index_dir)
    embedder = QwenEmbedder(model_name=index.manifest.get("model", DEFAULT_MODEL))
    result = answer_question(
        args.question,
        index,
        embedder,
        top_k=args.top_k,
        base_url=args.base_url,
        model=args.model,
    )
    print(result.answer)
    print("\n检索来源：")
    for rank, item in enumerate(result.results, start=1):
        chunk = item.chunk
        heading = " > ".join(chunk.heading_path) or "(document root)"
        print(f"[{rank}] {item.score:.4f} · {chunk.file}#{chunk.chunk_index} · {heading}")


if __name__ == "__main__":
    main()
