"""Validate an evaluation question JSONL file against a built chunk index."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_INDEX_DIR = Path(__file__).resolve().parents[1] / "artifacts/qwen-dense-v1"
QUESTION_TYPES = {
    "fact",
    "term",
    "semantic_rewrite",
    "multi_hop",
    "code_flow",
    "mixed",
    "unanswerable",
    "adversarial",
}


class QuestionSetError(ValueError):
    """Raised when an evaluation question set is malformed or inconsistent."""


def _load_chunks(index_dir: Path) -> set[str]:
    chunks_path = index_dir / "chunks.jsonl"
    try:
        lines = chunks_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise QuestionSetError(f"cannot read chunk index: {chunks_path}") from exc

    chunk_ids: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            chunk = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QuestionSetError(f"invalid chunk JSON at line {line_number}") from exc
        if not isinstance(chunk, dict) or not isinstance(chunk.get("file"), str):
            raise QuestionSetError(f"chunk at line {line_number} has no valid file")
        chunk_index = chunk.get("chunk_index")
        if not isinstance(chunk_index, int) or isinstance(chunk_index, bool):
            raise QuestionSetError(f"chunk at line {line_number} has no valid chunk_index")
        chunk_ids.add(f"{chunk['file']}#{chunk_index}")
    if not chunk_ids:
        raise QuestionSetError(f"chunk index is empty: {chunks_path}")
    return chunk_ids


def validate_questions(question_path: Path, index_dir: Path = DEFAULT_INDEX_DIR) -> dict[str, Any]:
    """Validate questions and return a compact coverage summary."""
    try:
        lines = question_path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise QuestionSetError(f"cannot read question set: {question_path}") from exc

    chunk_ids = _load_chunks(index_dir)
    questions: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            question = json.loads(line)
        except json.JSONDecodeError as exc:
            raise QuestionSetError(f"invalid JSON at line {line_number}") from exc
        if not isinstance(question, dict):
            raise QuestionSetError(f"line {line_number} must contain a JSON object")

        missing = {"id", "question", "type", "gold_chunk_ids"} - question.keys()
        if missing:
            raise QuestionSetError(
                f"line {line_number} is missing fields: {', '.join(sorted(missing))}"
            )

        question_id = question["id"]
        question_text = question["question"]
        question_type = question["type"]
        gold_chunk_ids = question["gold_chunk_ids"]
        if not isinstance(question_id, str) or not question_id.strip():
            raise QuestionSetError(f"line {line_number} has an invalid id")
        if question_id in seen_ids:
            raise QuestionSetError(f"duplicate id at line {line_number}: {question_id}")
        if not isinstance(question_text, str) or not question_text.strip():
            raise QuestionSetError(f"line {line_number} has an empty question")
        if question_type not in QUESTION_TYPES:
            allowed = ", ".join(sorted(QUESTION_TYPES))
            raise QuestionSetError(
                f"line {line_number} has unknown type {question_type!r}; allowed: {allowed}"
            )
        if not isinstance(gold_chunk_ids, list) or any(
            not isinstance(chunk_id, str) or not chunk_id.strip() for chunk_id in gold_chunk_ids
        ):
            raise QuestionSetError(f"line {line_number} has invalid gold_chunk_ids")
        if question_type != "unanswerable" and not gold_chunk_ids:
            raise QuestionSetError(
                f"line {line_number} needs at least one gold chunk for type {question_type}"
            )
        missing_chunks = sorted(set(gold_chunk_ids) - chunk_ids)
        if missing_chunks:
            raise QuestionSetError(
                f"line {line_number} references missing chunks: {', '.join(missing_chunks)}"
            )

        seen_ids.add(question_id)
        questions.append(question)

    if not questions:
        raise QuestionSetError(f"question set is empty: {question_path}")

    type_counts = Counter(question["type"] for question in questions)
    return {
        "path": str(question_path),
        "question_count": len(questions),
        "type_counts": dict(sorted(type_counts.items())),
        "unique_gold_chunk_count": len(
            {chunk_id for question in questions for chunk_id in question["gold_chunk_ids"]}
        ),
        "index_dir": str(index_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question_path", type=Path)
    parser.add_argument("--index-dir", type=Path, default=DEFAULT_INDEX_DIR)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    try:
        summary = validate_questions(args.question_path, args.index_dir)
    except QuestionSetError as exc:
        parser.error(str(exc))

    if args.as_json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return
    print(f"valid: {summary['path']}")
    print(f"questions: {summary['question_count']}")
    print(f"types: {json.dumps(summary['type_counts'], ensure_ascii=False, sort_keys=True)}")
    print(f"unique gold chunks: {summary['unique_gold_chunk_count']}")


if __name__ == "__main__":
    main()
