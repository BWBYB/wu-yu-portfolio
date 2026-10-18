"""Parallel Dense and BM25 retrieval for the local Agent Book corpus."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np

from .bm25 import BM25Index
from .index import NumpyIndex, RetrievalResult


class QueryEmbedder(Protocol):
    def encode_query(self, query: str) -> Any: ...


@dataclass(frozen=True)
class ParallelSearchResults:
    query: str
    dense: list[RetrievalResult]
    bm25: list[RetrievalResult]


class ParallelRetriever:
    """Run both retrievers for the same query and keep their rankings separate."""

    def __init__(
        self,
        dense_index: NumpyIndex,
        bm25_index: BM25Index,
        embedder: QueryEmbedder,
    ) -> None:
        self.dense_index = dense_index
        self.bm25_index = bm25_index
        self.embedder = embedder

    def search(self, query: str, top_k: int = 5) -> ParallelSearchResults:
        if top_k <= 0:
            return ParallelSearchResults(query=query, dense=[], bm25=[])

        query_embedding = np.asarray(self.embedder.encode_query(query).numpy())
        with ThreadPoolExecutor(max_workers=2, thread_name_prefix="rag-retrieval") as executor:
            dense_future = executor.submit(self.dense_index.search, query_embedding, top_k)
            bm25_future = executor.submit(self.bm25_index.search, query, top_k)
            return ParallelSearchResults(
                query=query,
                dense=dense_future.result(),
                bm25=bm25_future.result(),
            )
