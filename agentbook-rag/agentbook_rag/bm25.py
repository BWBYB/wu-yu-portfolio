"""BM25 sparse index for the fixed Agent Book chunks."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from rank_bm25 import BM25Okapi

from .chunking import Chunk
from .index import RetrievalResult


# shortcut: Chinese uses character tokens, which can overmatch; replace with a
# word segmenter if evaluation shows that precision is insufficient.
_TOKEN_RE = re.compile(r"[a-z0-9_]+|[\u4e00-\u9fff]", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Tokenize English identifiers and Chinese characters deterministically."""
    return [token.lower() for token in _TOKEN_RE.findall(text)]


class BM25Index:
    """Disk-backed BM25 index that returns the shared retrieval result type."""

    def __init__(
        self,
        chunks: list[Chunk],
        tokenized_documents: list[list[str]],
        manifest: dict[str, Any],
    ) -> None:
        if len(chunks) != len(tokenized_documents):
            raise ValueError("chunks and tokenized_documents must have matching length")
        self.chunks = chunks
        self.tokenized_documents = tokenized_documents
        self.manifest = manifest
        self._bm25 = BM25Okapi(tokenized_documents) if tokenized_documents else None

    @classmethod
    def from_chunks(
        cls,
        chunks: Iterable[Chunk],
        *,
        manifest: dict[str, Any] | None = None,
    ) -> "BM25Index":
        values = list(chunks)
        tokenized_documents = [tokenize(chunk.text) for chunk in values]
        index_manifest = {
            "retriever": "bm25",
            "metric": "bm25",
            "tokenizer": "ascii_words_and_cjk_unigrams",
            "k1": 1.5,
            "b": 0.75,
        }
        if manifest:
            index_manifest.update(manifest)
        return cls(values, tokenized_documents, index_manifest)

    def search(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        if top_k <= 0 or self._bm25 is None:
            return []
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self._bm25.get_scores(query_tokens)
        ranked = sorted(
            (
                (index, float(score))
                for index, score in enumerate(scores)
                if any(token in self.tokenized_documents[index] for token in query_tokens)
            ),
            key=lambda item: (-item[1], item[0]),
        )[:top_k]
        return [
            RetrievalResult(
                chunk=self.chunks[index],
                score=score,
                rank=rank,
                retriever="bm25",
            )
            for rank, (index, score) in enumerate(ranked, start=1)
        ]

    def save(self, directory: str | Path) -> None:
        path = Path(directory)
        path.mkdir(parents=True, exist_ok=True)
        with (path / "chunks.jsonl").open("w", encoding="utf-8") as handle:
            for chunk in self.chunks:
                handle.write(json.dumps(chunk.to_dict(), ensure_ascii=False) + "\n")
        with (path / "tokens.jsonl").open("w", encoding="utf-8") as handle:
            for tokens in self.tokenized_documents:
                handle.write(json.dumps(tokens, ensure_ascii=False) + "\n")
        saved_manifest = dict(self.manifest)
        saved_manifest["chunk_count"] = len(self.chunks)
        (path / "manifest.json").write_text(
            json.dumps(saved_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    @classmethod
    def load(cls, directory: str | Path) -> "BM25Index":
        path = Path(directory)
        chunks = [
            Chunk(**json.loads(line))
            for line in (path / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        tokenized_documents = [
            json.loads(line)
            for line in (path / "tokens.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        manifest = json.loads((path / "manifest.json").read_text(encoding="utf-8"))
        return cls(chunks, tokenized_documents, manifest)
