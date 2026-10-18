"""Disk-backed NumPy cosine index and shared retrieval result contract."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

import numpy as np

from .chunking import Chunk


@dataclass(frozen=True)
class RetrievalResult:
    """One ranked passage returned by any retriever."""

    chunk: Chunk
    score: float
    rank: int | None = None
    retriever: str = "dense"
    dense_rank: int | None = None
    bm25_rank: int | None = None


# Keep the original import name stable for the current QA layer and callers.
SearchResult = RetrievalResult


class NumpyIndex:
    def __init__(self, chunks: list[Chunk], embeddings: np.ndarray, manifest: dict[str, Any]) -> None:
        if embeddings.ndim != 2 or len(chunks) != embeddings.shape[0]:
            raise ValueError("chunks and embeddings must have matching two-dimensional shape")
        self.chunks = chunks
        self.embeddings = embeddings.astype(np.float32, copy=False)
        self.manifest = manifest

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        query = np.asarray(query_embedding, dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.embeddings.shape[1]:
            raise ValueError("query embedding dimension does not match the index")
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            raise ValueError("query embedding must not be zero")
        query = query / query_norm
        scores = self.embeddings @ query
        order = np.argsort(-scores, kind="stable")[: min(top_k, len(scores))]
        return [
            RetrievalResult(
                chunk=self.chunks[i],
                score=float(scores[i]),
                rank=rank,
                retriever="dense",
            )
            for rank, i in enumerate(order, start=1)
        ]

    def save(self, directory: str | Path) -> None:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        with (path / "chunks.jsonl").open("w", encoding="utf-8") as handle:
            for chunk in self.chunks:
                handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
        np.save(path / "embeddings.npy", self.embeddings)
        manifest = dict(self.manifest)
        manifest.update({"chunk_count": len(self.chunks), "embedding_dimension": self.embeddings.shape[1]})
        (path / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: str | Path) -> "NumpyIndex":
        path = Path(directory)
        chunks = [
            Chunk(**json.loads(line))
            for line in (path / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        embeddings = np.load(path / "embeddings.npy")
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        index = cls(chunks, embeddings, manifest)
        expected_dimension = manifest.get("embedding_dimension")
        if expected_dimension is not None and expected_dimension != embeddings.shape[1]:
            raise ValueError("manifest embedding dimension does not match embeddings.npy")
        return index
