from __future__ import annotations

from agentbook_rag.chunking import Chunk
from agentbook_rag.index import RetrievalResult
from agentbook_rag.rrf import reciprocal_rank_fusion, reciprocal_rank_fusion_many


def make_chunk(index: int, text: str | None = None) -> Chunk:
    value = text or f"chunk {index}"
    return Chunk("repo", "commit", "book/chapter1.md", [], index, value, value)


def result(index: int, rank: int, retriever: str = "dense") -> RetrievalResult:
    return RetrievalResult(make_chunk(index), 1.0, rank, retriever)


def test_rrf_merges_shared_chunks_and_keeps_branch_ranks():
    fused = reciprocal_rank_fusion(
        [result(0, 1), result(1, 2)],
        [result(1, 1, "bm25"), result(2, 2, "bm25")],
        top_k=3,
    )

    assert [item.chunk.chunk_index for item in fused] == [1, 0, 2]
    assert fused[0].retriever == "rrf"
    assert fused[0].dense_rank == 2
    assert fused[0].bm25_rank == 1
    assert fused[1].dense_rank == 1
    assert fused[1].bm25_rank is None


def test_rrf_uses_one_based_rank_and_custom_k():
    fused = reciprocal_rank_fusion([result(0, 1)], [], k=9)

    assert fused[0].score == 1 / 10
    assert fused[0].rank == 1


def test_rrf_validates_k_and_non_positive_top_k():
    try:
        reciprocal_rank_fusion([], [], k=0)
    except ValueError as error:
        assert "positive" in str(error)
    else:
        raise AssertionError("expected a ValueError for k=0")

    assert reciprocal_rank_fusion([result(0, 1)], [], top_k=0) == []


def test_rrf_many_accumulates_multiple_query_branches():
    fused = reciprocal_rank_fusion_many(
        [
            [result(0, 1)],
            [result(0, 2)],
            [result(1, 1, "bm25")],
        ],
        top_k=2,
        k=60,
    )

    assert [item.chunk.chunk_index for item in fused] == [0, 1]
    assert fused[0].dense_rank == 1
    assert fused[0].bm25_rank is None
