"""Reciprocal Rank Fusion for Dense and BM25 result lists."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from .index import RetrievalResult


def _chunk_key(result: RetrievalResult) -> tuple[str, int]:
    return result.chunk.file, result.chunk.chunk_index


def _rank(result: RetrievalResult, position: int) -> int:
    return result.rank if result.rank is not None else position


def reciprocal_rank_fusion_many(
    branches: Sequence[Iterable[RetrievalResult]],
    *,
    top_k: int | None = None,
    k: int = 60,
) -> list[RetrievalResult]:
    """Merge any number of ranked branches using RRF's rank-only score.

    Multi-query retrieval uses one Dense and one BM25 branch per query. The
    provenance fields keep the best Dense/BM25 rank seen across all branches.
    """
    if k <= 0:
        raise ValueError("RRF smoothing constant k must be positive")
    if top_k is not None and top_k <= 0:
        return []

    merged: dict[tuple[str, int], dict[str, object]] = {}
    for results in branches:
        for position, result in enumerate(results, start=1):
            key = _chunk_key(result)
            rank = _rank(result, position)
            branch = result.retriever if result.retriever in {"dense", "bm25"} else None
            entry = merged.setdefault(
                key,
                {
                    "chunk": result.chunk,
                    "score": 0.0,
                    "dense_rank": None,
                    "bm25_rank": None,
                },
            )
            if branch is not None:
                previous_rank = entry[f"{branch}_rank"]
                if previous_rank is None or rank < int(previous_rank):
                    entry[f"{branch}_rank"] = rank
            entry["score"] = float(entry["score"]) + 1 / (k + rank)

    ordered = sorted(
        merged.values(),
        key=lambda entry: (
            -float(entry["score"]),
            min(
                rank
                for rank in (entry["dense_rank"], entry["bm25_rank"])
                if rank is not None
            ),
            entry["chunk"].file,
            entry["chunk"].chunk_index,
        ),
    )
    if top_k is not None:
        ordered = ordered[:top_k]

    return [
        RetrievalResult(
            chunk=entry["chunk"],
            score=float(entry["score"]),
            rank=rank,
            retriever="rrf",
            dense_rank=entry["dense_rank"],
            bm25_rank=entry["bm25_rank"],
        )
        for rank, entry in enumerate(ordered, start=1)
    ]


def reciprocal_rank_fusion(
    dense_results: Iterable[RetrievalResult],
    bm25_results: Iterable[RetrievalResult],
    *,
    top_k: int | None = None,
    k: int = 60,
) -> list[RetrievalResult]:
    """Merge the Dense and BM25 ranked lists using RRF."""
    return reciprocal_rank_fusion_many(
        [dense_results, bm25_results],
        top_k=top_k,
        k=k,
    )


# Short name for callers that already know the operation is RRF.
fuse_results = reciprocal_rank_fusion
