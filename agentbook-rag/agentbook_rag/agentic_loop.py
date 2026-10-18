"""Bounded Agentic RAG loop: assess evidence, rewrite once, then stop."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from .agentic import AgenticSearchResult, search_with_query_rewrites
from .parallel import ParallelRetriever
from .reranker import CrossEncoderReranker


@dataclass(frozen=True)
class EvidenceDecision:
    action: str
    reason: str
    best_score: float | None


@dataclass(frozen=True)
class AgenticLoopResult:
    search: AgenticSearchResult
    rounds: int
    decision: EvidenceDecision


def assess_evidence(
    result: AgenticSearchResult,
    *,
    min_score: float = 0.0,
) -> EvidenceDecision:
    """Use the reranker's best score as a bounded, inspectable stop rule."""
    best_score = result.reranked[0].score if result.reranked else None
    if best_score is not None and best_score >= min_score:
        return EvidenceDecision("answer", "reranker_score_sufficient", best_score)
    reason = "no_candidates" if best_score is None else "low_reranker_score"
    return EvidenceDecision("rewrite", reason, best_score)


def run_agentic_search(
    question: str,
    retriever: ParallelRetriever,
    reranker: CrossEncoderReranker,
    rewrite: Callable[[str], Iterable[str]],
    *,
    candidate_k: int = 20,
    top_k: int = 5,
    rrf_k: int = 60,
    max_rewrites: int = 2,
    min_score: float = 0.0,
) -> AgenticLoopResult:
    """Run E3, then at most one rewrite pass when evidence looks weak.

    The rewrite callable is intentionally injected so production can use the
    OpenAI-compatible rewriter while tests remain deterministic and offline.
    """
    initial = search_with_query_rewrites(
        question,
        (),
        retriever,
        reranker,
        candidate_k=candidate_k,
        top_k=top_k,
        rrf_k=rrf_k,
        max_rewrites=0,
    )
    decision = assess_evidence(initial, min_score=min_score)
    if decision.action == "answer":
        return AgenticLoopResult(initial, rounds=1, decision=decision)

    rewritten = tuple(rewrite(question))
    second = search_with_query_rewrites(
        question,
        rewritten,
        retriever,
        reranker,
        candidate_k=candidate_k,
        top_k=top_k,
        rrf_k=rrf_k,
        max_rewrites=max_rewrites,
    )
    final_decision = assess_evidence(second, min_score=min_score)
    stopped = EvidenceDecision("answer", "max_rounds", final_decision.best_score)
    return AgenticLoopResult(second, rounds=2, decision=stopped)
