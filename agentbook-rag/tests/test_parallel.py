from __future__ import annotations

import numpy as np

from agentbook_rag.bm25 import BM25Index
from agentbook_rag.chunking import Chunk
from agentbook_rag.index import NumpyIndex
from agentbook_rag.parallel import ParallelRetriever


class FakeVector:
    def numpy(self) -> np.ndarray:
        return np.array([1, 0], dtype=np.float32)


class FakeEmbedder:
    def encode_query(self, query: str) -> FakeVector:
        assert query == "BM25"
        return FakeVector()


def make_chunk(index: int, text: str) -> Chunk:
    return Chunk("repo", "commit", "book/chapter1.md", [], index, text, text)


def test_parallel_retriever_keeps_dense_and_bm25_branches():
    chunks = [make_chunk(0, "Dense semantic passage"), make_chunk(1, "BM25 keyword passage")]
    dense = NumpyIndex(
        chunks,
        np.array([[1, 0], [0, 1]], dtype=np.float32),
        {"model": "test-model"},
    )
    bm25 = BM25Index.from_chunks(chunks)

    results = ParallelRetriever(dense, bm25, FakeEmbedder()).search("BM25", top_k=1)

    assert results.query == "BM25"
    assert len(results.dense) == 1
    assert len(results.bm25) == 1
    assert results.dense[0].retriever == "dense"
    assert results.bm25[0].retriever == "bm25"
    assert results.bm25[0].chunk.chunk_index == 1


def test_parallel_retriever_handles_non_positive_top_k():
    chunks = [make_chunk(0, "Dense semantic passage")]
    dense = NumpyIndex(chunks, np.array([[1, 0]], dtype=np.float32), {})
    bm25 = BM25Index.from_chunks(chunks)

    results = ParallelRetriever(dense, bm25, FakeEmbedder()).search("BM25", top_k=0)

    assert results.dense == []
    assert results.bm25 == []
