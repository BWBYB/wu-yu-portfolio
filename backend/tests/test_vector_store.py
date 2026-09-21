from pathlib import Path

from app.knowledge import KnowledgeChunk
from app.vector_store import ChromaVectorStore, resolve_chroma_path


class FakeCollection:
    def __init__(self) -> None:
        self.added: list[dict[str, object]] = []
        self.query_result: dict[str, list[list[object]]] = {
            "ids": [[]],
            "distances": [[]],
        }

    def add(self, **kwargs: object) -> None:
        self.added.append(kwargs)

    def query(self, **kwargs: object) -> dict[str, list[list[object]]]:
        return self.query_result


class FakeClient:
    def __init__(self) -> None:
        self.collection = FakeCollection()
        self.deleted: list[str] = []
        self.metadata: dict[str, object] | None = None

    def delete_collection(self, name: str) -> None:
        self.deleted.append(name)

    def get_or_create_collection(self, name: str, metadata: dict[str, object]):
        self.metadata = metadata
        return self.collection


def _chunks() -> tuple[KnowledgeChunk, ...]:
    return (
        KnowledgeChunk("资料:0", "个人资料", "技术栈", "React、FastAPI"),
        KnowledgeChunk("资料:1", "个人资料", "项目", "SPMTrack"),
    )


def test_rebuild_uses_chunk_ids_and_source_metadata() -> None:
    client = FakeClient()
    chunks = _chunks()
    store = ChromaVectorStore("/tmp/chroma", "test_collection", client=client)

    assert store.rebuild(chunks, [[1.0, 0.0], [0.0, 1.0]]) == 2
    record = client.collection.added[-1]

    assert client.deleted == ["test_collection"]
    assert client.metadata == {"hnsw:space": "cosine"}
    assert record["ids"] == [chunk.chunk_id for chunk in chunks]
    assert record["metadatas"] == [
        {"source": "个人资料", "heading": "技术栈"},
        {"source": "个人资料", "heading": "项目"},
    ]
    assert record["documents"] == [chunk.content for chunk in chunks]


def test_query_filters_distances_and_maps_chunks() -> None:
    client = FakeClient()
    client.collection.query_result = {
        "ids": [["资料:0", "资料:1"]],
        "distances": [[0.04, 0.2]],
    }
    chunks = _chunks()
    store = ChromaVectorStore("/tmp/chroma", "test_collection", client=client)

    result = store.query(
        [1.0, 0.0],
        {chunk.chunk_id: chunk for chunk in chunks},
        top_k=4,
        max_distance=0.1,
    )

    assert [chunk.chunk_id for chunk in result] == ["资料:0"]


def test_relative_chroma_path_is_under_backend_directory() -> None:
    path = resolve_chroma_path("data/chroma")

    assert path == Path(__file__).resolve().parents[1] / "data" / "chroma"
