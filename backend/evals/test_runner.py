from evals.cases import EvaluationCase
from datetime import datetime, timezone

from evals.runner import EvaluationResult, calculate_metrics, render_report, run_evaluation


def test_out_of_scope_case_short_circuits_without_fake_provider_call():
    cases = (
        EvaluationCase(
            id="boundary-1",
            question="量子泡沫的月相编码是什么？",
            category="out_of_scope",
            expected_sources=(),
            required_facts=(),
            should_answer=False,
            expected_model_call=False,
        ),
    )

    results, metrics = run_evaluation(cases)

    assert results[0].status_code == 200
    assert results[0].actual_sources == []
    assert results[0].retrieved_chunks == 0
    assert results[0].model_call_count == 0
    assert results[0].boundary_correct is True
    assert metrics["no_match_model_short_circuit_rate"] == 1.0


def test_matched_case_calls_fake_provider_and_calculates_source_hit():
    cases = (
        EvaluationCase(
            id="profile-1",
            question="吴禹使用哪些技术？",
            category="profile_fact",
            expected_sources=("个人资料",),
            required_facts=("React",),
            should_answer=True,
            expected_model_call=True,
        ),
    )

    results, _ = run_evaluation(cases)

    assert results[0].status_code == 200
    assert results[0].retrieved_chunks > 0
    assert results[0].model_call_count == 1
    assert results[0].source_hit is True
    assert results[0].required_facts_missing == []


def test_metrics_calculate_p95_for_a_small_sample():
    results = [
        _make_result("a", 1.0),
        _make_result("b", 2.0),
        _make_result("c", 10.0),
    ]

    metrics = calculate_metrics(results)

    assert metrics["total_cases"] == 3
    assert metrics["p95_latency_ms"] == 10.0


def test_report_contains_only_aggregates_and_case_ids():
    report = render_report(
        {"total_cases": 1, "http_success_rate": 1.0},
        [{"id": "boundary-1", "error": "boundary_mismatch"}],
        generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    assert "boundary-1" in report
    assert "完整问题" not in report
    assert "完整回答" not in report
    assert "api_key" not in report.lower()
    assert "2026-09-20T00:00:00+00:00" in report


def test_report_does_not_render_question_or_answer_fields():
    report = render_report(
        {"total_cases": 40},
        [
            {
                "id": "boundary-006",
                "error": "boundary_mismatch",
                "question": "must-not-appear-question",
                "answer": "must-not-appear-answer",
            }
        ],
        generated_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    assert "boundary-006" in report
    assert "must-not-appear-question" not in report
    assert "must-not-appear-answer" not in report


def test_metrics_count_boundary_false_positives_in_short_circuit_rate():
    results = [
        _make_result("boundary-ok", 1.0, category="out_of_scope", sources=[], calls=0),
        _make_result(
            "boundary-hit",
            2.0,
            category="out_of_scope",
            sources=["个人资料"],
            calls=1,
            expected_model_call=False,
        ),
    ]

    metrics = calculate_metrics(results)

    assert metrics["no_match_model_short_circuit_rate"] == 0.5


def test_retrieval_error_requires_disjoint_sources_not_partial_overlap():
    results = [
        _make_result("partial", 1.0, sources=["个人资料"], expected_sources=("个人资料", "SPMTrack 项目资料")),
        _make_result("disjoint", 2.0, sources=["其他资料"], expected_sources=("个人资料",)),
    ]

    metrics = calculate_metrics(results)

    assert metrics["retrieval_error_rate"] == 0.5


def _make_result(
    case_id: str,
    latency_ms: float,
    *,
    category: str = "profile_fact",
    sources: list[str] | None = None,
    calls: int = 1,
    expected_sources: tuple[str, ...] = ("个人资料",),
    expected_model_call: bool | None = None,
) -> EvaluationResult:
    actual_sources = sources if sources is not None else ["个人资料"]
    return EvaluationResult(
        id=case_id,
        category=category,
        expected_model_call=calls > 0 if expected_model_call is None else expected_model_call,
        status_code=200,
        actual_sources=actual_sources,
        retrieved_chunks=1,
        model_call_count=calls,
        latency_ms=latency_ms,
        source_hit=all(source in actual_sources for source in expected_sources),
        required_facts_hit=["React"],
        required_facts_missing=[],
        boundary_correct=None,
        retrieval_error=bool(set(actual_sources).isdisjoint(set(expected_sources))),
        error=None,
    )
