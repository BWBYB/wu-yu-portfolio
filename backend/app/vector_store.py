from pathlib import Path
from typing import Any

from .knowledge import KnowledgeChunk

try:
    import chromadb
except ImportError:  # pragma: no cover - runtime dependency is installed for local use
    chromadb = None  # type: ignore[assignment]


class VectorStoreError(RuntimeError):
    """Raised when the local ChromaDB store cannot be used."""


def resolve_chroma_path(configured_path: str) -> Path:
    path = Path(configured_path)
    if path.is_absolute():
        return path
    return Path(__file__).resolve().parents[1] / path


class ChromaVectorStore:
    """Small adapter that keeps ChromaDB response details out of the API layer."""

    def __init__(self, path: str | Path, collection_name: str, *, client: Any | None = None) -> None:
        self.path = Path(path)
        self.collection_name = collection_name
        self._client = client or self._create_client(self.path)
        self._collection = self._get_collection()

    def rebuild(
        self,
        chunks: tuple[KnowledgeChunk, ...],
        embeddings: list[list[float]],
    ) -> int:
        if len(chunks) != len(embeddings):
            raise VectorStoreError("vector index input mismatch")
        try:
            self._client.delete_collection(self.collection_name)
            self._collection = self._get_collection()
            if chunks:
                self._collection.add(
                    ids=[chunk.chunk_id for chunk in chunks],
                    documents=[chunk.content for chunk in chunks],
                    embeddings=embeddings,
                    metadatas=[
                        {"source": chunk.source, "heading": chunk.heading}
                        for chunk in chunks
                    ],
                )
            return len(chunks)
        except VectorStoreError:
            raise
        except Exception as error:
            raise VectorStoreError("vector store unavailable") from error

    def query(
        self,
        query_embedding: list[float],
        chunks_by_id: dict[str, KnowledgeChunk],
        top_k: int,
        max_distance: float,
    ) -> tuple[KnowledgeChunk, ...]:
        try:
            result = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )
            ids = _first_row(result.get("ids"))
            distances = _first_row(result.get("distances"))
            selected: list[KnowledgeChunk] = []
            for chunk_id, distance in zip(ids, distances):
                if float(distance) <= max_distance and chunk_id in chunks_by_id:
                    selected.append(chunks_by_id[chunk_id])
            return tuple(selected)
        except Exception as error:
            raise VectorStoreError("vector store unavailable") from error

    @staticmethod
    def _create_client(path: Path) -> Any:
        if chromadb is None:
            raise VectorStoreError("vector store unavailable")
        try:
            path.mkdir(parents=True, exist_ok=True)
            return chromadb.PersistentClient(path=str(path))
        except Exception as error:
            raise VectorStoreError("vector store unavailable") from error

    def _get_collection(self) -> Any:
        try:
            return self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        except Exception as error:
            raise VectorStoreError("vector store unavailable") from error


def _first_row(value: object) -> list[object]:
    if not isinstance(value, list) or not value:
        return []
    first = value[0]
    return first if isinstance(first, list) else []
