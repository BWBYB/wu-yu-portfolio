import json
from pathlib import Path

from agentbook_rag.evaluate import _metrics, _required_evidence_metrics, document_id
from agentbook_rag.chunking import Chunk
from agentbook_rag.index import RetrievalResult


def _chunk(index: int) -> Chunk:
    return Chunk(
        source_repo="repo",
        commit="commit",
        file="book/chapter1.md",
        heading_path=["Heading"],
        chunk_index=index,
        text=f"chunk {index}",
        embedding_text=f"chunk {index}",
    )


def test_document_id_is_stable() -> None:
    result = RetrievalResult(chunk=_chunk(3), score=0.5, rank=1)
    assert document_id(result) == "book/chapter1.md#3"


def test_metrics_use_gold_chunk_ids() -> None:
    questions = [
        {
            "id": "q1",
            "question": "问题",
            "type": "fact",
            "gold_chunk_ids": ["book/chapter1.md#3"],
        }
    ]
    records = [
        {
            "question_id": "q1",
            "results": [
                {"doc_id": "book/chapter1.md#3", "score": 1.0},
                {"doc_id": "book/chapter1.md#4", "score": 0.1},
            ],
        }
    ]

    metrics = _metrics(questions, records)

    assert metrics["overall"]["recall@5"] == 1.0
    assert metrics["overall"]["hit_rate@5"] == 1.0
    assert metrics["by_type"]["fact"]["mrr@10"] == 1.0


def test_required_evidence_metrics_distinguish_partial_and_complete() -> None:
    questions = [
        {
            "id": "q1",
            "question": "问题",
            "type": "multi_hop",
            "gold_chunk_ids": ["book/chapter1.md#3", "book/chapter1.md#4"],
        }
    ]
    records = [
        {
            "question_id": "q1",
            "results": [
                {"doc_id": "book/chapter1.md#3", "score": 1.0},
                {"doc_id": "book/chapter1.md#9", "score": 0.1},
            ],
        }
    ]

    metrics = _required_evidence_metrics(questions, records)

    assert metrics["@5"]["mean_coverage"] == 0.5
    assert metrics["@5"]["complete_rate"] == 0.0
