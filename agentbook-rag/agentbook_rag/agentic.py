"""Small, bounded multi-query retrieval building block for Agentic RAG."""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Iterable, Sequence

from .index import RetrievalResult
from .parallel import ParallelRetriever
from .reranker import CrossEncoderReranker
from .rrf import reciprocal_rank_fusion_many


@dataclass(frozen=True)
class AgenticSearchResult:
    """Retrieval output plus the query set used for this bounded pass."""

    queries: tuple[str, ...]
    fused: list[RetrievalResult]
    reranked: list[RetrievalResult]


def build_query_set(
    original_query: str,
    rewrites: Iterable[str],
    *,
    max_rewrites: int = 2,
) -> tuple[str, ...]:
    """Keep the original query and at most two unique non-empty rewrites."""
    if max_rewrites < 0:
        raise ValueError("max_rewrites must be non-negative")
    values: list[str] = []
    for query in (original_query, *rewrites):
        normalized = " ".join(query.split())
        if normalized and normalized not in values:
            values.append(normalized)
        if len(values) >= max_rewrites + 1:
            break
    if not values:
        raise ValueError("original_query must not be empty")
    return tuple(values)


def search_with_query_rewrites(
    original_query: str,
    rewrites: Iterable[str],
    retriever: ParallelRetriever,
    reranker: CrossEncoderReranker,
    *,
    candidate_k: int = 20,
    top_k: int = 5,
    rrf_k: int = 60,
    max_rewrites: int = 2,
) -> AgenticSearchResult:
    """Run one bounded multi-query pass, then rerank against the user query.

    The original query is always retained. All Dense/BM25 branches are fused
    together, while the reranker still judges relevance to the original user
    question so a rewrite cannot silently change the requested intent.
    """
    if candidate_k <= 0 or top_k <= 0 or top_k > candidate_k:
        raise ValueError("candidate_k must be >= top_k and both must be positive")
    queries = build_query_set(original_query, rewrites, max_rewrites=max_rewrites)
    dense_branches: list[list[RetrievalResult]] = []
    bm25_branches: list[list[RetrievalResult]] = []
    for query in queries:
        results = retriever.search(query, top_k=candidate_k)
        dense_branches.append(results.dense)
        bm25_branches.append(results.bm25)
    fused = reciprocal_rank_fusion_many(
        [*dense_branches, *bm25_branches],
        top_k=candidate_k,
        k=rrf_k,
    )
    reranked = reranker.rerank(original_query, fused, top_k=top_k)
    return AgenticSearchResult(queries=queries, fused=fused, reranked=reranked)
