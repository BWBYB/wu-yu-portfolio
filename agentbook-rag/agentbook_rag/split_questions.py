"""Split a reviewed candidate question set into reproducible evaluation sets."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .validate_questions import QuestionSetError, validate_questions


class SplitSpecError(ValueError):
    """Raised when a review split manifest is incomplete or inconsistent."""


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SplitSpecError(f"cannot read question set: {path}") from exc

    questions: list[dict[str, Any]] = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            question = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SplitSpecError(f"invalid JSON at line {line_number}") from exc
        if not isinstance(question, dict):
            raise SplitSpecError(f"line {line_number} must contain a JSON object")
        questions.append(question)
    if not questions:
        raise SplitSpecError(f"question set is empty: {path}")
    return questions


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SplitSpecError(f"cannot read split manifest: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SplitSpecError(f"invalid split manifest JSON: {path}") from exc
    if not isinstance(manifest, dict):
        raise SplitSpecError("split manifest must be a JSON object")
    return manifest


def _ids(manifest: dict[str, Any], key: str) -> list[str]:
    value = manifest.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise SplitSpecError(f"{key} must be a list of non-empty question IDs")
    if len(set(value)) != len(value):
        raise SplitSpecError(f"{key} contains duplicate question IDs")
    return value


def _validate_split(
    questions: list[dict[str, Any]], manifest: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    by_id = {question.get("id"): question for question in questions}
    if len(by_id) != len(questions) or any(not isinstance(question.get("id"), str) for question in questions):
        raise SplitSpecError("question set must contain unique string IDs")

    groups = {
        "development_ids": _ids(manifest, "development_ids"),
        "test_ids": _ids(manifest, "test_ids"),
        "unanswerable_ids": _ids(manifest, "unanswerable_ids"),
        "excluded_ids": _ids(manifest, "excluded_ids"),
    }
    if not groups["development_ids"] or not groups["test_ids"]:
        raise SplitSpecError("development_ids and test_ids must both be non-empty")

    assigned: list[str] = [question_id for ids in groups.values() for question_id in ids]
    unknown = sorted(set(assigned) - set(by_id))
    if unknown:
        raise SplitSpecError(f"manifest references unknown question IDs: {', '.join(unknown)}")
    if len(set(assigned)) != len(assigned):
        duplicates = sorted({question_id for question_id in assigned if assigned.count(question_id) > 1})
        raise SplitSpecError(f"question IDs appear in multiple split groups: {', '.join(duplicates)}")

    unassigned = sorted(set(by_id) - set(assigned))
    if unassigned:
        raise SplitSpecError(f"manifest does not assign question IDs: {', '.join(unassigned)}")

    for question_id in groups["unanswerable_ids"]:
        if by_id[question_id].get("type") != "unanswerable":
            raise SplitSpecError(f"{question_id} is not marked unanswerable")
    for group_name in ("development_ids", "test_ids"):
        invalid = [
            question_id
            for question_id in groups[group_name]
            if by_id[question_id].get("type") == "unanswerable"
        ]
        if invalid:
            raise SplitSpecError(
                f"{group_name} cannot contain unanswerable questions: {', '.join(invalid)}"
            )

    return {
        group_name.removesuffix("_ids"): [by_id[question_id] for question_id in ids]
        for group_name, ids in groups.items()
    }


def _write_jsonl(path: Path, questions: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(question, ensure_ascii=False) + "\n" for question in questions),
        encoding="utf-8",
    )


def split_questions(
    questions_path: Path,
    manifest_path: Path,
    output_dir: Path,
    *,
    index_dir: Path | None = None,
) -> dict[str, Any]:
    """Validate a reviewed split manifest and write its three output JSONL files."""
    questions = _load_jsonl(questions_path)
    manifest = _load_manifest(manifest_path)
    if index_dir is not None:
        validate_questions(questions_path, index_dir)
    groups = _validate_split(questions, manifest)

    output_dir.mkdir(parents=True, exist_ok=True)
    for group_name in ("development", "test", "unanswerable", "excluded"):
        _write_jsonl(output_dir / f"questions.v1.{group_name}.jsonl", groups[group_name])

    return {
        "source": str(questions_path),
        "manifest": str(manifest_path),
        "output_dir": str(output_dir),
        "counts": {group_name: len(group) for group_name, group in groups.items()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--index-dir", type=Path, default=None)
    args = parser.parse_args()
    try:
        summary = split_questions(
            args.questions,
            args.manifest,
            args.output_dir,
            index_dir=args.index_dir,
        )
    except (QuestionSetError, SplitSpecError) as exc:
        parser.error(str(exc))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
