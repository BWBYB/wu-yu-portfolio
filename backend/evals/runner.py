"""Offline evaluation runner for the Version 0 knowledge-base API.

The runner deliberately exercises the public FastAPI route while replacing only
the model adapter in the evaluation process.  It never contacts a provider.
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from fastapi.testclient import TestClient

from app import main as app_main
from app.config import Settings, get_settings
from evals.cases import EvaluationCase, load_cases


@dataclass(frozen=True)
class EvaluationResult:
    id: str
    category: str
    expected_model_call: bool
    status_code: int
    actual_sources: list[str]
    retrieved_chunks: int
    model_call_count: int
    latency_ms: float
    source_hit: bool | None
    required_facts_hit: list[str]
    required_facts_missing: list[str]
    boundary_correct: bool | None
    retrieval_error: bool
    error: str | None


class FakeProvider:
    """Deterministic provider substitute used only by the offline evaluator."""

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def generate(self, messages: list[dict[str, str]], settings: object) -> str:
        self.calls.append({"messages": messages, "settings": settings})
        system_message = next(
            (message.get("content", "") for message in messages if message.get("role") == "system"),
            "",
        )
        markers = ("检索到的资料：\n", "Retrieved context:\n")
        context = ""
        for marker in markers:
            if marker in system_message:
                context = system_message.split(marker, 1)[1]
                break
        return f"根据已验证资料整理：\n{context.strip()}"


class _MetadataHandler(logging.Handler):
    """Capture the production request metadata without changing production code."""

    def __init__(self) -> None:
        super().__init__(level=logging.INFO)
        self.latest: dict[str, Any] = {}

    def emit(self, record: logging.LogRecord) -> None:
        try:
            metadata = json.loads(record.getMessage())
        except (TypeError, json.JSONDecodeError):
            return
        if isinstance(metadata, dict) and metadata.get("route") == "/api/chat":
            self.latest = metadata


def run_evaluation(cases: tuple[EvaluationCase, ...]) -> tuple[list[EvaluationResult], dict[str, object]]:
    """Run cases through ``POST /api/chat`` and return sanitized observations."""

    provider = FakeProvider()
    client = TestClient(app_main.app, raise_server_exceptions=False)
    metadata_handler = _MetadataHandler()
    original_logger_level = app_main.request_logger.level
    original_settings_override = app_main.app.dependency_overrides.get(get_settings)
    app_main.request_logger.setLevel(logging.INFO)
    app_main.request_logger.addHandler(metadata_handler)
    app_main.app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None,
        rag_retrieval="lexical",
    )
    results: list[EvaluationResult] = []
    original_generate_answer = app_main.generate_answer
    app_main.generate_answer = provider.generate
    try:
        for case in cases:
            results.append(_run_case(client, provider, metadata_handler, case))
    finally:
        app_main.generate_answer = original_generate_answer
        app_main.request_logger.removeHandler(metadata_handler)
        app_main.request_logger.setLevel(original_logger_level)
        if original_settings_override is None:
            app_main.app.dependency_overrides.pop(get_settings, None)
        else:
            app_main.app.dependency_overrides[get_settings] = original_settings_override
        client.close()

    return results, calculate_metrics(results)


def _run_case(
    client: TestClient,
    provider: FakeProvider,
    metadata_handler: _MetadataHandler,
    case: EvaluationCase,
) -> EvaluationResult:
    provider.calls.clear()
    metadata_handler.latest = {}
    started_at = time.perf_counter()
    response = client.post("/api/chat", json={"message": case.question, "history": []})
    latency_ms = round((time.perf_counter() - started_at) * 1000, 2)

    payload: dict[str, Any]
    try:
        decoded = response.json()
    except ValueError:
        decoded = {}
    payload = decoded if isinstance(decoded, dict) else {}
    raw_sources = payload.get("sources", [])
    actual_sources = [source for source in raw_sources if isinstance(source, str)] if isinstance(raw_sources, list) else []
    answer = payload.get("answer", "") if isinstance(payload.get("answer", ""), str) else ""
    retrieved_chunks = _safe_int(metadata_handler.latest.get("retrieved_chunks"), default=0)
    model_call_count = len(provider.calls)

    source_hit = None if not case.expected_sources else all(
        source in actual_sources for source in case.expected_sources
    )
    required_facts_hit = [fact for fact in case.required_facts if fact in answer]
    required_facts_missing = [fact for fact in case.required_facts if fact not in answer]
    is_boundary_case = case.category in {"out_of_scope", "adversarial"} or not case.should_answer
    boundary_correct = (
        None
        if not is_boundary_case
        else case.should_answer is False
        and response.status_code == 200
        and not actual_sources
        and model_call_count == 0
    )
    expected_source_set = set(case.expected_sources)
    actual_source_set = set(actual_sources)
    retrieval_error = (
        bool(actual_source_set.isdisjoint(expected_source_set))
        if expected_source_set
        else bool(actual_source_set) if case.category in {"out_of_scope", "adversarial"} else False
    )

    errors: list[str] = []
    if response.status_code != 200:
        errors.append(f"http_status_{response.status_code}")
    if model_call_count != int(case.expected_model_call):
        errors.append("model_call_mismatch")
    if source_hit is False:
        errors.append("source_mismatch")
    if retrieval_error:
        errors.append("retrieval_error")
    if required_facts_missing:
        errors.append("required_facts_missing")
    if boundary_correct is False:
        errors.append("boundary_mismatch")

    return EvaluationResult(
        id=case.id,
        category=case.category,
        expected_model_call=case.expected_model_call,
        status_code=response.status_code,
        actual_sources=actual_sources,
        retrieved_chunks=retrieved_chunks,
        model_call_count=model_call_count,
        latency_ms=latency_ms,
        source_hit=source_hit,
        required_facts_hit=required_facts_hit,
        required_facts_missing=required_facts_missing,
        boundary_correct=boundary_correct,
        retrieval_error=retrieval_error,
        error="; ".join(errors) or None,
    )


def calculate_metrics(results: list[EvaluationResult]) -> dict[str, object]:
    """Calculate deterministic aggregate metrics with explicit empty denominators."""

    total = len(results)
    category_counts: dict[str, int] = {}
    for result in results:
        category_counts[result.category] = category_counts.get(result.category, 0) + 1

    expected_source_results = [result for result in results if result.source_hit is not None]
    required_fact_hits = sum(len(result.required_facts_hit) for result in results)
    required_fact_total = required_fact_hits + sum(
        len(result.required_facts_missing) for result in results
    )
    boundary_results = [
        result for result in results if result.category in {"out_of_scope", "adversarial"}
    ]
    short_circuit_results = [result for result in results if not result.expected_model_call]
    retrieval_errors = sum(result.retrieval_error for result in results)
    latencies = sorted(result.latency_ms for result in results)

    return {
        "total_cases": total,
        "category_counts": dict(sorted(category_counts.items())),
        "http_success_rate": _ratio(sum(result.status_code == 200 for result in results), total),
        "source_hit_rate": _ratio(
            sum(result.source_hit is True for result in expected_source_results),
            len(expected_source_results),
        ),
        "required_fact_coverage": _ratio(required_fact_hits, required_fact_total),
        "out_of_scope_refusal_rate": _ratio(
            sum(result.boundary_correct is True for result in boundary_results), len(boundary_results)
        ),
        "no_match_model_short_circuit_rate": _ratio(
            sum(result.model_call_count == 0 and not result.actual_sources for result in short_circuit_results),
            len(short_circuit_results),
        ),
        "retrieval_error_rate": _ratio(retrieval_errors, total),
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
        "p95_latency_ms": _p95(latencies),
    }


def render_report(
    metrics: dict[str, object],
    failures: Iterable[EvaluationResult | dict[str, object]],
    *,
    generated_at: datetime | None = None,
) -> str:
    """Render a sanitized engineering report from aggregate results."""

    failure_lines = []
    for failure in failures:
        if isinstance(failure, EvaluationResult):
            failure_id, error = failure.id, failure.error or "unspecified"
        else:
            failure_id = str(failure.get("id", "unknown"))
            error = str(failure.get("error", "unspecified"))
        failure_lines.append(f"- `{failure_id}`: {error}")
    if not failure_lines:
        failure_lines.append("- 无失败案例")

    generated_at = generated_at or datetime.now(timezone.utc)
    metric_lines = [f"- `{name}`: {value}" for name, value in metrics.items()]
    return """# Version 0 评测基线

本报告由离线评测运行器生成，运行时间：`""" + generated_at.isoformat() + """`。仅记录聚合指标和可定位的案例 ID，不记录问题、回答、请求头或供应商原始错误。

## 指标

指标定义：来源命中率只统计有期望来源的案例；关键事实覆盖率是字符串代理检查；资料外正确拒答率要求 HTTP 200、无来源且未调用模型；无命中模型短路率统计边界案例中无来源且未调用模型的比例；错误检索率统计来源不相交或资料外出现来源的案例。

""" + "\n".join(metric_lines) + "\n\n## 失败案例\n\n" + "\n".join(failure_lines) + "\n\n## 当前判断\n\n当前事实案例和来源选择通过了离线代理检查；边界案例暴露了关键词检索的误命中，不能把它们当成安全拒答已经完成。Fake Provider 的短路结果只证明 API 在真正无命中时不调用模型。\n\n## 局限与下一步\n\n自动指标不能代表语义正确率、回答自然度或完整的提示词注入抵抗力，需结合人工复核。下一步优先补充稳定的评测资料与检索策略，再比较 RAG V1；Function Calling、MCP 和多 Agent 暂不因基线结果直接引入。\n"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the offline Version 0 evaluation")
    parser.add_argument("--cases", type=Path, default=None)
    parser.add_argument("--results", type=Path, default=None)
    parser.add_argument("--report", type=Path, default=None)
    args = parser.parse_args(argv)

    repository_root = Path(__file__).resolve().parents[2]
    results_path = args.results or repository_root / "artifacts/evals/version-0-results.json"
    report_path = args.report or repository_root / "docs/evals/version-0-baseline.md"
    cases = load_cases(args.cases)
    results, metrics = run_evaluation(cases)
    serialized_results = [asdict(result) for result in results]
    results_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(
        json.dumps({"metrics": metrics, "results": serialized_results}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        render_report(metrics, [result for result in results if result.error]), encoding="utf-8"
    )
    return 0


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _p95(latencies: list[float]) -> float | None:
    if not latencies:
        return None
    index = min(max(math.ceil(0.95 * len(latencies)) - 1, 0), len(latencies) - 1)
    return latencies[index]


def _safe_int(value: object, default: int) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else default


if __name__ == "__main__":
    raise SystemExit(main())
