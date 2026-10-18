from __future__ import annotations

from dataclasses import dataclass

from agentbook_rag.agentic_loop import assess_evidence, run_agentic_search
from agentbook_rag.chunking import Chunk
from agentbook_rag.index import RetrievalResult


def _result(index: int, score: float) -> RetrievalResult:
    chunk = Chunk("repo", "commit", "book.md", [], index, f"chunk {index}", f"chunk {index}")
    return RetrievalResult(chunk, score, 1, "dense")


@dataclass
class FakeRetriever:
    calls: list[str]

    def search(self, query: str, top_k: int):
        self.calls.append(query)
        item = _result(0 if query == "原始" else 1, 0.1)
        return type("ParallelResult", (), {"dense": [item], "bm25": []})()


class FakeReranker:
    def __init__(self, scores: list[float]):
        self.scores = iter(scores)

    def rerank(self, query, candidates, *, top_k=None):
        values = list(candidates)
        score = next(self.scores)
        return [
            RetrievalResult(values[0].chunk, score, 1, "reranker")
        ][:top_k]


def test_sufficient_evidence_stops_after_first_round():
    result = run_agentic_search(
        "原始", FakeRetriever([]), FakeReranker([0.8]), lambda _: ["改写"], min_score=0.5
    )
    assert result.rounds == 1
    assert result.decision.action == "answer"


def test_low_score_triggers_one_rewrite_then_stops():
    retriever = FakeRetriever([])
    result = run_agentic_search(
        "原始", retriever, FakeReranker([-0.2, 0.4]), lambda _: ["改写"], min_score=0.5
    )
    assert result.rounds == 2
    assert result.decision.reason == "max_rounds"
    assert retriever.calls == ["原始", "原始", "改写"]


def test_empty_results_need_rewrite():
    empty = type("Result", (), {"reranked": []})()
    assert assess_evidence(empty).reason == "no_candidates"
