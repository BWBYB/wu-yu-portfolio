import pytest

from app.embeddings import EmbeddingError, LocalEmbeddingProvider


class FakeModel:
    def __init__(self) -> None:
        self.calls: list[tuple[list[str], dict[str, object]]] = []

    def encode(self, values: list[str], **kwargs: object) -> list[list[float]]:
        self.calls.append((values, kwargs))
        return [[1.0, 0.0] for _ in values]


def test_provider_prefixes_documents_and_queries(monkeypatch) -> None:
    model = FakeModel()
    monkeypatch.setattr("app.embeddings.SentenceTransformer", lambda name: model)
    provider = LocalEmbeddingProvider("test-model")

    assert provider.embed_documents(["技术栈", "项目"]) == [[1.0, 0.0], [1.0, 0.0]]
    assert provider.embed_query("我的技术栈") == [1.0, 0.0]
    assert model.calls == [
        (["passage: 技术栈", "passage: 项目"], {"normalize_embeddings": True}),
        (["query: 我的技术栈"], {"normalize_embeddings": True}),
    ]


def test_provider_maps_model_failures_to_stable_error(monkeypatch) -> None:
    def fail_model(name: str) -> object:
        raise RuntimeError("provider details must not escape")

    monkeypatch.setattr("app.embeddings.SentenceTransformer", fail_model)
    provider = LocalEmbeddingProvider("test-model")

    with pytest.raises(EmbeddingError, match="local embedding unavailable"):
        provider.embed_query("问题")


def test_provider_returns_empty_list_for_empty_documents(monkeypatch) -> None:
    model = FakeModel()
    monkeypatch.setattr("app.embeddings.SentenceTransformer", lambda name: model)

    assert LocalEmbeddingProvider("test-model").embed_documents([]) == []
    assert model.calls == []
