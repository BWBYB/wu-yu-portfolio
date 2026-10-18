import json
from pathlib import Path

import pytest

from agentbook_rag.validate_questions import QuestionSetError, validate_questions


def _write_index(path: Path, chunk_ids: list[str]) -> None:
    path.mkdir()
    lines = []
    for chunk_id in chunk_ids:
        file, index = chunk_id.rsplit("#", 1)
        lines.append(json.dumps({"file": file, "chunk_index": int(index)}))
    (path / "chunks.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_questions(path: Path, questions: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(question, ensure_ascii=False) for question in questions) + "\n",
        encoding="utf-8",
    )


def test_validate_questions_returns_coverage_summary(tmp_path: Path) -> None:
    index_dir = tmp_path / "index"
    _write_index(index_dir, ["book/chapter1.md#1", "book/chapter1.md#2"])
    question_path = tmp_path / "questions.jsonl"
    _write_questions(
        question_path,
        [
            {
                "id": "q001",
                "question": "什么是工具调用？",
                "type": "fact",
                "gold_chunk_ids": ["book/chapter1.md#1"],
            },
            {
                "id": "q002",
                "question": "资料是否回答了天气？",
                "type": "unanswerable",
                "gold_chunk_ids": [],
            },
        ],
    )

    summary = validate_questions(question_path, index_dir)

    assert summary["question_count"] == 2
    assert summary["type_counts"] == {"fact": 1, "unanswerable": 1}
    assert summary["unique_gold_chunk_count"] == 1


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", "q001"),
        ("question", "什么是工具调用？"),
        ("type", "fact"),
        ("gold_chunk_ids", ["book/chapter1.md#1"]),
    ],
)
def test_validate_questions_rejects_duplicate_ids(
    tmp_path: Path, field: str, value: object
) -> None:
    index_dir = tmp_path / "index"
    _write_index(index_dir, ["book/chapter1.md#1"])
    question_path = tmp_path / "questions.jsonl"
    base = {
        "id": "q001",
        "question": "什么是工具调用？",
        "type": "fact",
        "gold_chunk_ids": ["book/chapter1.md#1"],
    }
    base[field] = value
    _write_questions(question_path, [base, {**base}])

    with pytest.raises(QuestionSetError, match="duplicate id"):
        validate_questions(question_path, index_dir)


def test_validate_questions_rejects_missing_gold_chunk(tmp_path: Path) -> None:
    index_dir = tmp_path / "index"
    _write_index(index_dir, ["book/chapter1.md#1"])
    question_path = tmp_path / "questions.jsonl"
    _write_questions(
        question_path,
        [
            {
                "id": "q001",
                "question": "问题",
                "type": "fact",
                "gold_chunk_ids": ["book/chapter1.md#99"],
            }
        ],
    )

    with pytest.raises(QuestionSetError, match="missing chunks"):
        validate_questions(question_path, index_dir)
