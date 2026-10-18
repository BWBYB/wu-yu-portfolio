from __future__ import annotations

from agentbook_rag.chunking import Chunk
from agentbook_rag.index import RetrievalResult
from agentbook_rag.reranker import rerank_with_scores


def make_result(index: int, rank: int) -> RetrievalResult:
    chunk = Chunk("repo", "commit", "book/chapter1.md", [], index, f"chunk {index}", f"chunk {index}")
    return RetrievalResult(chunk, 0.1, rank, "rrf", dense_rank=rank, bm25_rank=None)


def test_rerank_reorders_by_cross_encoder_scores_and_keeps_provenance():
    results = rerank_with_scores(
        [make_result(0, 1), make_result(1, 2)],
        [0.2, 0.9],
    )

    assert [item.chunk.chunk_index for item in results] == [1, 0]
    assert [item.rank for item in results] == [1, 2]
    assert [item.score for item in results] == [0.9, 0.2]
    assert results[0].retriever == "reranker"
    assert results[0].dense_rank == 2


def test_rerank_supports_top_k_and_validates_lengths():
    assert len(rerank_with_scores([make_result(0, 1), make_result(1, 2)], [0.1, 0.2], top_k=1)) == 1
    try:
        rerank_with_scores([make_result(0, 1)], [])
    except ValueError as error:
        assert "matching length" in str(error)
    else:
        raise AssertionError("expected a ValueError for mismatched scores")
