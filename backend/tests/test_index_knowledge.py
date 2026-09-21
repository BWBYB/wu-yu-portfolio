from app.knowledge import KnowledgeChunk, KnowledgeDocument
from app.config import Settings


def test_build_index_loads_chunks_and_returns_count(monkeypatch) -> None:
    chunks = (
        KnowledgeChunk("资料:0", "个人资料", "技术栈", "React"),
        KnowledgeChunk("资料:1", "个人资料", "项目", "SPMTrack"),
    )
    captured: dict[str, object] = {}

    class FakeProvider:
        def __init__(self, model_name: str) -> None:
            captured["model_name"] = model_name

        def embed_documents(self, texts: list[str]) -> list[list[float]]:
            captured["texts"] = texts
            return [[1.0, 0.0] for _ in texts]

    class FakeStore:
        def __init__(self, path: str, collection: str) -> None:
            captured["path"] = path
            captured["collection"] = collection

        def rebuild(self, actual_chunks, embeddings) -> int:
            captured["chunks"] = actual_chunks
            captured["embeddings"] = embeddings
            return len(actual_chunks)

    monkeypatch.setattr(
        "app.index_knowledge.load_knowledge",
        lambda: [KnowledgeDocument("个人资料", "资料")],
    )
    monkeypatch.setattr("app.index_knowledge.build_chunks", lambda documents: chunks)
    monkeypatch.setattr("app.index_knowledge.LocalEmbeddingProvider", FakeProvider)
    monkeypatch.setattr("app.index_knowledge.ChromaVectorStore", FakeStore)

    from app.index_knowledge import build_index

    assert build_index(Settings(_env_file=None)) == 2
    assert captured["model_name"] == "intfloat/multilingual-e5-small"
    assert captured["texts"] == ["React", "SPMTrack"]
    assert captured["chunks"] == chunks
    assert captured["embeddings"] == [[1.0, 0.0], [1.0, 0.0]]
