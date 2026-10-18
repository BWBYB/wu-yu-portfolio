import json
from pathlib import Path

import pytest

from agentbook_rag.split_questions import SplitSpecError, split_questions


def _write_questions(path: Path) -> None:
    questions = [
        {
            "id": "q001",
            "question": "什么是工具调用？",
            "type": "fact",
            "gold_chunk_ids": ["book/chapter1.md#1"],
        },
        {
            "id": "q002",
            "question": "什么是 RRF？",
            "type": "term",
            "gold_chunk_ids": ["book/chapter1.md#2"],
        },
        {
            "id": "q003",
            "question": "资料是否回答了天气？",
            "type": "unanswerable",
            "gold_chunk_ids": [],
        },
    ]
    path.write_text(
        "\n".join(json.dumps(question, ensure_ascii=False) for question in questions) + "\n",
        encoding="utf-8",
    )


def _write_index(path: Path) -> None:
    path.mkdir()
    (path / "chunks.jsonl").write_text(
        "\n".join(
            json.dumps({"file": "book/chapter1.md", "chunk_index": index})
            for index in (1, 2)
        )
        + "\n",
        encoding="utf-8",
    )


def _write_manifest(path: Path, **overrides: object) -> None:
    manifest = {
        "version": "v1",
        "development_ids": ["q001"],
        "test_ids": ["q002"],
        "unanswerable_ids": ["q003"],
        "excluded_ids": [],
    }
    manifest.update(overrides)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def test_split_questions_writes_three_reviewed_sets(tmp_path: Path) -> None:
    question_path = tmp_path / "questions.jsonl"
    manifest_path = tmp_path / "splits.json"
    index_dir = tmp_path / "index"
    _write_questions(question_path)
    _write_index(index_dir)
    _write_manifest(manifest_path)

    summary = split_questions(
        question_path,
        manifest_path,
        tmp_path / "frozen",
        index_dir=index_dir,
    )

    assert summary["counts"] == {
        "development": 1,
        "test": 1,
        "unanswerable": 1,
        "excluded": 0,
    }
    assert (tmp_path / "frozen/questions.v1.development.jsonl").read_text().count("q001") == 1
    assert (tmp_path / "frozen/questions.v1.test.jsonl").read_text().count("q002") == 1
    assert (tmp_path / "frozen/questions.v1.unanswerable.jsonl").read_text().count("q003") == 1


def test_split_questions_rejects_unassigned_ids(tmp_path: Path) -> None:
    question_path = tmp_path / "questions.jsonl"
    manifest_path = tmp_path / "splits.json"
    _write_questions(question_path)
    _write_manifest(manifest_path, test_ids=[])

    with pytest.raises(SplitSpecError, match="development_ids and test_ids must both be non-empty"):
        split_questions(question_path, manifest_path, tmp_path / "frozen")


def test_split_questions_rejects_cross_group_duplicates(tmp_path: Path) -> None:
    question_path = tmp_path / "questions.jsonl"
    manifest_path = tmp_path / "splits.json"
    _write_questions(question_path)
    _write_manifest(manifest_path, test_ids=["q001", "q002"])

    with pytest.raises(SplitSpecError, match="multiple split groups"):
        split_questions(question_path, manifest_path, tmp_path / "frozen")


def test_split_questions_rejects_unanswerable_in_test(tmp_path: Path) -> None:
    question_path = tmp_path / "questions.jsonl"
    manifest_path = tmp_path / "splits.json"
    _write_questions(question_path)
    _write_manifest(
        manifest_path,
        test_ids=["q002", "q003"],
        unanswerable_ids=[],
    )

    with pytest.raises(SplitSpecError, match="cannot contain unanswerable"):
        split_questions(question_path, manifest_path, tmp_path / "frozen")
