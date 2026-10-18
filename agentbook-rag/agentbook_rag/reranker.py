"""Cross-Encoder neural reranking for fused retrieval candidates."""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from .embedding import select_device
from .index import RetrievalResult


DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


def rerank_with_scores(
    candidates: Sequence[RetrievalResult],
    scores: Sequence[float],
    *,
    top_k: int | None = None,
) -> list[RetrievalResult]:
    """Apply model scores while preserving the candidate provenance fields."""
    if len(candidates) != len(scores):
        raise ValueError("candidates and scores must have matching length")
    if top_k is not None and top_k <= 0:
        return []

    ordered = sorted(
        zip(candidates, scores),
        key=lambda item: (-float(item[1]), item[0].rank or 0),
    )
    if top_k is not None:
        ordered = ordered[:top_k]
    return [
        RetrievalResult(
            chunk=result.chunk,
            score=float(score),
            rank=rank,
            retriever="reranker",
            dense_rank=result.dense_rank,
            bm25_rank=result.bm25_rank,
        )
        for rank, (result, score) in enumerate(ordered, start=1)
    ]


class CrossEncoderReranker:
    """Score query/document pairs with a local Hugging Face Cross-Encoder."""

    def __init__(
        self,
        model_name: str = DEFAULT_RERANKER_MODEL,
        *,
        device: torch.device | None = None,
        batch_size: int = 4,
        max_length: int = 512,
    ) -> None:
        self.model_name = model_name
        self.device = device or select_device()
        self.batch_size = batch_size
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name,
            dtype=torch.float32,
        )
        self.model.to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def _score_pairs(self, query: str, documents: list[str]) -> list[float]:
        scores: list[float] = []
        for start in range(0, len(documents), self.batch_size):
            batch = documents[start : start + self.batch_size]
            encoded = self.tokenizer(
                [query] * len(batch),
                batch,
                padding=True,
                truncation=True,
                max_length=self.max_length,
                return_tensors="pt",
            )
            encoded = {name: value.to(self.device) for name, value in encoded.items()}
            logits = self.model(**encoded).logits
            if logits.ndim == 2:
                logits = logits[:, 0]
            scores.extend(logits.reshape(-1).float().cpu().tolist())
        return scores

    def rerank(
        self,
        query: str,
        candidates: Iterable[RetrievalResult],
        *,
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        values = list(candidates)
        if not values or (top_k is not None and top_k <= 0):
            return []
        scores = self._score_pairs(query, [result.chunk.text for result in values])
        return rerank_with_scores(values, scores, top_k=top_k)
