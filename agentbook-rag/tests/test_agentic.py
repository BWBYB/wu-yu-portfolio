from __future__ import annotations

from dataclasses import dataclass

from agentbook_rag.agentic import build_query_set, search_with_query_rewrites
from agentbook_rag.chunking import Chunk
from agentbook_rag.index import RetrievalResult


def _result(index: int, rank: int, retriever: str = "dense") -> RetrievalResult:
    chunk = Chunk("repo", "commit", "book.md", [], index, f"chunk {index}", f"chunk {index}")
    return RetrievalResult(chunk, 1.0, rank, retriever)


def test_build_query_set_keeps_original_and_deduplicates():
    assert build_query_set("  原始问题 ", ["改写", "原始问题", "第二个"], max_rewrites=2) == (
        "原始问题",
        "改写",
        "第二个",
    )


@dataclass
class FakeParallel:
    def search(self, query: str, top_k: int):
        return type(
            "ParallelResult",
            (),
            {"dense": [_result(0 if query == "原始" else 1, 1)], "bm25": []},
        )()


class FakeReranker:
    def rerank(self, query, candidates, *, top_k=None):
        return list(candidates)[:top_k] if top_k is not None else list(candidates)


def test_multi_query_retrieval_fuses_rewrite_branch():
    result = search_with_query_rewrites(
        "原始",
        ["改写"],
        FakeParallel(),
        FakeReranker(),
        candidate_k=5,
        top_k=2,
    )

    assert result.queries == ("原始", "改写")
    assert {item.chunk.chunk_index for item in result.fused} == {0, 1}
