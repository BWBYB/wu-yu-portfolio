from collections.abc import Sequence
from typing import Any

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover - exercised when optional runtime deps are absent
    SentenceTransformer = None  # type: ignore[assignment,misc]


class EmbeddingError(RuntimeError):
    """Raised when the local embedding model cannot encode text."""


class LocalEmbeddingProvider:
    """Lazy wrapper around a Sentence Transformers embedding model."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model: Any | None = None

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        values = [f"passage: {text}" for text in texts]
        encoded = self._encode(values)
        return _as_matrix(encoded)

    def embed_query(self, text: str) -> list[float]:
        encoded = self._encode([f"query: {text}"])
        rows = _as_matrix(encoded)
        if len(rows) != 1:
            raise EmbeddingError("local embedding unavailable")
        return rows[0]

    def _encode(self, values: list[str]) -> object:
        try:
            model = self._get_model()
            return model.encode(values, normalize_embeddings=True)
        except EmbeddingError:
            raise
        except Exception as error:
            raise EmbeddingError("local embedding unavailable") from error

    def _get_model(self) -> Any:
        if self._model is None:
            if SentenceTransformer is None:
                raise EmbeddingError("local embedding unavailable")
            self._model = SentenceTransformer(self.model_name)
        return self._model


def _as_matrix(encoded: object) -> list[list[float]]:
    value = encoded.tolist() if hasattr(encoded, "tolist") else encoded
    if not isinstance(value, list):
        raise EmbeddingError("local embedding unavailable")
    if value and isinstance(value[0], (int, float)):
        return [[float(item) for item in value]]
    if not all(isinstance(row, list) for row in value):
        raise EmbeddingError("local embedding unavailable")
    try:
        return [[float(item) for item in row] for row in value]
    except (TypeError, ValueError) as error:
        raise EmbeddingError("local embedding unavailable") from error
