"""Adapter between the FastAPI app and the local Agent Book RAG package."""

from __future__ import annotations

import sys
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any

from .config import Settings


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAG_ROOT = PROJECT_ROOT / "agentbook-rag"
if str(RAG_ROOT) not in sys.path:
    sys.path.insert(0, str(RAG_ROOT))


class AgentBookConfigurationError(Exception):
    """Raised when the local RAG or model configuration is incomplete."""


class AgentBookUnavailableError(Exception):
    """Raised when local retrieval fails."""


@lru_cache(maxsize=1)
def _load_pipeline() -> tuple[Any, Any, Any, Any]:
    from agentbook_rag.agentic_loop import run_agentic_search
    from agentbook_rag.bm25 import BM25Index
    from agentbook_rag.embedding import QwenEmbedder
    from agentbook_rag.index import NumpyIndex
    from agentbook_rag.parallel import ParallelRetriever
    from agentbook_rag.reranker import CrossEncoderReranker

    dense = NumpyIndex.load(RAG_ROOT / "artifacts/qwen-dense-v1")
    bm25 = BM25Index.load(RAG_ROOT / "artifacts/bm25-v1")
    embedder = QwenEmbedder(model_name=dense.manifest.get("model"))
    retriever = ParallelRetriever(dense, bm25, embedder)
    reranker = CrossEncoderReranker()
    return run_agentic_search, retriever, reranker, embedder


async def answer_agentbook(question: str, settings: Settings) -> tuple[str, list[str], str]:
    """Run bounded Agentic RAG and generate an answer from its final context."""
    if not settings.openai_api_key:
        raise AgentBookConfigurationError("OPENAI_API_KEY is not configured")

    try:
        run_agentic_search, retriever, reranker, _ = _load_pipeline()
        from agentbook_rag.rewrite import rewrite_query
        from agentbook_rag.qa import build_messages
        from .llm import generate_answer

        def rewrite(query: str) -> list[str]:
            return rewrite_query(
                query,
                api_key=settings.openai_api_key,
                base_url=settings.openai_base_url,
                model=settings.openai_model,
                max_rewrites=2,
                timeout_seconds=settings.llm_timeout_seconds,
            )

        result = run_agentic_search(
            question,
            retriever,
            reranker,
            rewrite,
            candidate_k=20,
            top_k=5,
            rrf_k=60,
            max_rewrites=2,
            min_score=0.0,
        )
        messages = build_messages(question, result.search.reranked)
        sources = [
            f"{item.chunk.file}#{item.chunk.chunk_index}"
            + (f" · {' > '.join(item.chunk.heading_path)}" if item.chunk.heading_path else "")
            for item in result.search.reranked
        ]
        answer = await generate_answer(messages, settings)
        return answer, sources, str(uuid.uuid4())
    except AgentBookConfigurationError:
        raise
    except Exception as error:
        raise AgentBookUnavailableError("local Agent Book RAG unavailable") from error
