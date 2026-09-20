from evals.cases import EvaluationCase
from evals.runner import EvaluationResult, calculate_metrics, run_evaluation


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


def test_metrics_count_boundary_false_positives_in_short_circuit_rate():
    results = [
        _make_result("boundary-ok", 1.0, category="out_of_scope", sources=[], calls=0),
        _make_result("boundary-hit", 2.0, category="out_of_scope", sources=["个人资料"], calls=1),
    ]

    metrics = calculate_metrics(results)

    assert metrics["no_match_model_short_circuit_rate"] == 0.5


def _make_result(
    case_id: str,
    latency_ms: float,
    *,
    category: str = "profile_fact",
    sources: list[str] | None = None,
    calls: int = 1,
) -> EvaluationResult:
    actual_sources = sources if sources is not None else ["个人资料"]
    return EvaluationResult(
        id=case_id,
        category=category,
        status_code=200,
        actual_sources=actual_sources,
        retrieved_chunks=1,
        model_call_count=calls,
        latency_ms=latency_ms,
        source_hit=True,
        required_facts_hit=["React"],
        required_facts_missing=[],
        boundary_correct=None,
        error=None,
    )
