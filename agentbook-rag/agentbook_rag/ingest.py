"""Build the local Qwen dense index from the checked-in source snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from transformers import AutoTokenizer

from .chunking import chunk_markdown
from .embedding import DEFAULT_MODEL, QwenEmbedder
from .index import NumpyIndex


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def build_index(
    *,
    source_dir: Path,
    output_dir: Path,
    manifest_path: Path,
    model_name: str = DEFAULT_MODEL,
    chunk_size: int = 512,
    overlap: int = 64,
) -> NumpyIndex:
    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    chunks = []
    for file_name in source_manifest["files"]:
        source_path = source_dir / file_name
        text = source_path.read_text(encoding="utf-8")
        chunks.extend(
            chunk_markdown(
                text,
                tokenizer,
                source_repo=source_manifest["source_repo"],
                commit=source_manifest["commit"],
                file=f"book/{file_name}",
                chunk_size=chunk_size,
                overlap=overlap,
            )
        )

    embedder = QwenEmbedder(model_name=model_name)
    embeddings = embedder.encode_documents(chunk.embedding_text for chunk in chunks).numpy()
    index = NumpyIndex(
        chunks,
        embeddings,
        {
            "source_repo": source_manifest["source_repo"],
            "source_url": source_manifest["source_url"],
            "source_commit": source_manifest["commit"],
            "model": model_name,
            "device": str(embedder.device),
            "chunk_size_tokens": chunk_size,
            "overlap_tokens": overlap,
            "metric": "cosine",
            "embedding_text": "static source/commit/file/heading prefix plus raw chunk",
        },
    )
    index.save(output_dir)
    return index


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=PROJECT_ROOT / "data/source")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "artifacts/qwen-dense-v1")
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "source-manifest.json")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--chunk-size", type=int, default=512)
    parser.add_argument("--overlap", type=int, default=64)
    args = parser.parse_args()
    index = build_index(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        manifest_path=args.manifest,
        model_name=args.model,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
    )
    print(f"built {len(index.chunks)} chunks -> {args.output_dir}")


if __name__ == "__main__":
    main()
