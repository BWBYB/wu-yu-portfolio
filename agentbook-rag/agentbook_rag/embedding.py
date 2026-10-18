"""Qwen3-Embedding inference with MPS-first device selection."""

from __future__ import annotations

from typing import Iterable

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


DEFAULT_MODEL = "Qwen/Qwen3-Embedding-0.6B"
DEFAULT_QUERY_INSTRUCTION = (
    "Given a question, retrieve relevant passages from the ai-agent-book knowledge base"
)


def select_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cpu")


def _last_token_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    sequence_lengths = attention_mask.sum(dim=1) - 1
    batch_indices = torch.arange(last_hidden_state.shape[0], device=last_hidden_state.device)
    return last_hidden_state[batch_indices, sequence_lengths]


class QwenEmbedder:
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        device: torch.device | None = None,
        batch_size: int = 4,
        max_length: int = 8192,
    ) -> None:
        self.model_name = model_name
        self.device = device or select_device()
        self.batch_size = batch_size
        self.max_length = max_length
        self.tokenizer = AutoTokenizer.from_pretrained(model_name, padding_side="left")
        self.model = AutoModel.from_pretrained(model_name, dtype=torch.float32)
        self.model.to(self.device)
        self.model.eval()

    @torch.inference_mode()
    def _encode(self, texts: list[str]) -> torch.Tensor:
        encoded = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        encoded = {name: value.to(self.device) for name, value in encoded.items()}
        outputs = self.model(**encoded)
        pooled = _last_token_pool(outputs.last_hidden_state, encoded["attention_mask"])
        return F.normalize(pooled, p=2, dim=1).float().cpu()

    def encode_documents(self, texts: Iterable[str]) -> torch.Tensor:
        values = list(texts)
        if not values:
            return torch.empty((0, 0), dtype=torch.float32)
        batches = [self._encode(values[i : i + self.batch_size]) for i in range(0, len(values), self.batch_size)]
        return torch.cat(batches, dim=0)

    def encode_query(self, query: str, instruction: str = DEFAULT_QUERY_INSTRUCTION) -> torch.Tensor:
        prompt = f"Instruct: {instruction}\nQuery: {query}"
        return self._encode([prompt])[0]
