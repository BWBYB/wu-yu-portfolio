from __future__ import annotations

import numpy as np

from agentbook_rag.chunking import Chunk
from agentbook_rag.index import NumpyIndex


def make_chunk(index: int) -> Chunk:
    return Chunk("repo", "commit", "book/chapter1.md", [], index, f"chunk {index}", f"chunk {index}")


def test_index_saves_loads_and_sorts(tmp_path):
    index = NumpyIndex(
        [make_chunk(0), make_chunk(1), make_chunk(2)],
        np.array([[1, 0], [0, 1], [0.8, 0.2]], dtype=np.float32),
        {"model": "test-model"},
    )
    index.save(tmp_path)
    loaded = NumpyIndex.load(tmp_path)

    results = loaded.search(np.array([1, 0], dtype=np.float32), top_k=2)
    assert [result.chunk.chunk_index for result in results] == [0, 2]
    assert [result.rank for result in results] == [1, 2]
    assert {result.retriever for result in results} == {"dense"}
    assert loaded.manifest["chunk_count"] == 3
    assert loaded.manifest["embedding_dimension"] == 2
