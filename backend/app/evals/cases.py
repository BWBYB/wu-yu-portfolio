from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


_CATEGORIES = frozenset(
    {"profile_fact", "project_fact", "paraphrase", "out_of_scope", "adversarial"}
)
_REQUIRED_FIELDS = frozenset(
    {
        "id",
        "question",
        "category",
        "expected_sources",
        "required_facts",
        "should_answer",
        "expected_model_call",
    }
)


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    question: str
    category: str
    expected_sources: tuple[str, ...]
    required_facts: tuple[str, ...]
    should_answer: bool
    expected_model_call: bool


def load_cases(path: Path | None = None) -> tuple[EvaluationCase, ...]:
    case_path = path or (Path(__file__).resolve().parents[2] / "evals" / "cases.json")
    try:
        raw_cases = json.loads(case_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"case file not found: {case_path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"case file is not valid JSON: {error.msg}") from error

    if not isinstance(raw_cases, list):
        raise ValueError("case file must contain a JSON list")

    cases: list[EvaluationCase] = []
    seen_ids: set[str] = set()
    for index, raw_case in enumerate(raw_cases):
        cases.append(_parse_case(raw_case, index, seen_ids))
    return tuple(cases)


def _parse_case(raw_case: Any, index: int, seen_ids: set[str]) -> EvaluationCase:
    if not isinstance(raw_case, dict):
        raise ValueError(f"case {index} must be an object")
    missing = _REQUIRED_FIELDS - raw_case.keys()
    if missing:
        raise ValueError(f"case {index} missing required fields: {', '.join(sorted(missing))}")

    case_id = _nonblank_string(raw_case["id"], f"case {index}.id")
    if case_id in seen_ids:
        raise ValueError(f"duplicate case id: {case_id}")
    seen_ids.add(case_id)
    question = _nonblank_string(raw_case["question"], f"case {index}.question")
    category = _nonblank_string(raw_case["category"], f"case {index}.category")
    if category not in _CATEGORIES:
        raise ValueError(f"case {index}.category is unknown: {category}")

    expected_sources = _string_list(raw_case["expected_sources"], f"case {index}.expected_sources")
    required_facts = _string_list(raw_case["required_facts"], f"case {index}.required_facts")
    should_answer = _boolean(raw_case["should_answer"], f"case {index}.should_answer")
    expected_model_call = _boolean(
        raw_case["expected_model_call"], f"case {index}.expected_model_call"
    )
    if category == "out_of_scope" and (
        expected_sources or required_facts or should_answer or expected_model_call
    ):
        raise ValueError("out_of_scope cases must have no sources, facts, answer, or model call")

    return EvaluationCase(
        id=case_id,
        question=question,
        category=category,
        expected_sources=tuple(expected_sources),
        required_facts=tuple(required_facts),
        should_answer=should_answer,
        expected_model_call=expected_model_call,
    )


def _nonblank_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-blank string")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field} must be a list")
    return [_nonblank_string(item, f"{field}[{index}]") for index, item in enumerate(value)]


def _boolean(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be a boolean")
    return value
