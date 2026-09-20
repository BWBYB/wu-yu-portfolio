# Version 0 Evaluation Baseline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a repeatable offline evaluation baseline for the Version 0 personal knowledge agent without calling a real model or changing the public API.

**Architecture:** Store versioned evaluation cases in JSON and run them through the existing FastAPI `TestClient` using the real loading, chunking, retrieval, validation, and no-match short-circuit path. Monkeypatch `app.main.generate_answer` only inside the evaluation runner with a deterministic Fake Provider that records calls and returns context-derived text; write sanitized JSON results and Markdown summaries as local/report artifacts.

**Tech Stack:** Python 3.11+, FastAPI `TestClient`, pytest, standard library `json`, `math`, `statistics`, `time`, Markdown, existing Astro content collection.

**Spec:** `docs/superpowers/specs/2026-09-20-version-0-evaluation-design.md`

## Global Constraints

- Do not call a real OpenAI-compatible provider, Vercel Preview, or any network service.
- Do not add LangChain, LangGraph, MCP, ChromaDB, Milvus, Embedding, or multi-agent dependencies.
- Do not change `POST /api/chat` request or response schemas.
- Do not change `knowledge/`, Vercel Firewall, environment variables, Production, or frontend behavior.
- Keep Fake Provider code inside `backend/evals/`; it must never be imported by production app modules.
- Do not record API keys, request headers, IP addresses, full questions, full answers, or raw provider exceptions in committed reports.
- Use `apply_patch` for manual edits and run the focused test after each implementation step.
- Machine-generated `artifacts/` output is local-only and must remain ignored.

---

### Task 1: Add the versioned evaluation case set and schema tests

**Files:**
- Create: `backend/evals/__init__.py`
- Create: `backend/evals/cases.json`
- Create: `backend/evals/cases.py`
- Create: `backend/evals/test_cases.py`
- Modify: `.gitignore` only if `artifacts/evals/` is not already ignored

**Interfaces:**
- Produces `EvaluationCase` as a typed immutable data object with `id`, `question`, `category`, `expected_sources`, `required_facts`, `should_answer`, and `expected_model_call`.
- Produces `load_cases(path: Path | None = None) -> tuple[EvaluationCase, ...]`.
- The default path is `backend/evals/cases.json` resolved relative to `cases.py`.

- [ ] **Step 1: Write failing case-loader tests**

```python
from evals.cases import EvaluationCase, load_cases


def test_case_file_has_at_least_24_unique_cases_in_all_categories():
    cases = load_cases()

    assert len(cases) >= 24
    assert len({case.id for case in cases}) == len(cases)
    assert {case.category for case in cases} == {
        "profile_fact",
        "project_fact",
        "paraphrase",
        "out_of_scope",
        "adversarial",
    }


def test_out_of_scope_case_requires_no_source_and_no_model_call():
    case = next(case for case in load_cases() if case.category == "out_of_scope")

    assert case.expected_sources == ()
    assert case.should_answer is False
    assert case.expected_model_call is False


def test_loader_rejects_missing_required_fields(tmp_path):
    invalid = tmp_path / "cases.json"
    invalid.write_text('[{"id": "bad"}]', encoding="utf-8")

    try:
        load_cases(invalid)
    except ValueError as error:
        assert "category" in str(error)
    else:
        raise AssertionError("invalid cases must be rejected")
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/evals/test_cases.py -q
```

Expected: collection fails because `backend/evals/cases.py` does not exist.

- [ ] **Step 3: Implement the loader and create the 28-case JSON file**

Use a frozen dataclass and validate each JSON object before constructing it. The loader must reject duplicate IDs, unknown categories, non-list fields, blank IDs/questions, and inconsistent out-of-scope cases. Create approximately 28 cases using only facts already present in `knowledge/profile.md` and `knowledge/spmtrack.md`; adversarial cases must be safe text inputs and must not ask the runner to perform filesystem writes.

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/evals/test_cases.py -q
```

Expected: all case-loader tests pass and every category is represented.

- [ ] **Step 5: Verify artifact ignore behavior**

Run:

```bash
mkdir -p artifacts/evals
touch artifacts/evals/.keep
git check-ignore -v artifacts/evals/.keep
rm artifacts/evals/.keep
```

Expected: the path is ignored. Do not commit generated output.

- [ ] **Step 6: Commit the case set**

```bash
git add backend/evals .gitignore
git commit -m "test: add version zero evaluation cases"
```

---

### Task 2: Implement the offline runner and deterministic metrics

**Files:**
- Create: `backend/evals/runner.py`
- Create: `backend/evals/test_runner.py`

**Interfaces:**
- Produces `FakeProvider` with `calls: list[dict[str, object]]` and an async `generate(messages, settings) -> str` method.
- Produces `EvaluationResult` with the fields defined in the spec: `id`, `category`, `status_code`, `actual_sources`, `retrieved_chunks`, `model_call_count`, `latency_ms`, `source_hit`, `required_facts_hit`, `required_facts_missing`, `boundary_correct`, and `error`.
- Produces `run_evaluation(cases: tuple[EvaluationCase, ...]) -> tuple[list[EvaluationResult], dict[str, object]]`.
- Produces `calculate_metrics(results: list[EvaluationResult]) -> dict[str, object]`.
- Produces a CLI `main(argv: list[str] | None = None) -> int` that writes `artifacts/evals/version-0-results.json` and `docs/evals/version-0-baseline.md`.

- [ ] **Step 1: Write failing runner tests**

```python
from app.evals.cases import EvaluationCase
from app.evals.runner import calculate_metrics, run_evaluation


def test_out_of_scope_case_short_circuits_without_fake_provider_call():
    cases = (
        EvaluationCase(
            id="boundary-1",
            question="一个资料中没有的问题",
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
    assert results[0].model_call_count == 1
    assert results[0].source_hit is True
    assert results[0].required_facts_missing == []


def test_metrics_calculate_p95_for_a_small_sample():
    results = [
        make_result("a", 1.0),
        make_result("b", 2.0),
        make_result("c", 10.0),
    ]

    metrics = calculate_metrics(results)

    assert metrics["total_cases"] == 3
    assert metrics["p95_latency_ms"] == 10.0
```

`make_result` is a test helper that constructs a valid `EvaluationResult`; tests must not rely on network or environment secrets.

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/evals/test_runner.py -q
```

Expected: collection fails because the runner interfaces do not exist.

- [ ] **Step 3: Implement Fake Provider injection and one-case execution**

Use `TestClient(app)` and monkeypatch `app.main.generate_answer` only around the evaluation call. The Fake Provider should inspect the system/user message text, record a call, and return a deterministic answer containing the selected context so required-fact checks are reproducible. Reset its calls before every case. Do not expose provider internals through `ChatResponse`.

- [ ] **Step 4: Implement result classification**

For every case, collect only sanitized fields. Set `source_hit` to true only when every expected source appears in the response source list; for cases with no expected sources, leave it null. Set `boundary_correct` true only when `should_answer` is false, status is 200, sources are empty, and model call count is zero; otherwise false for an out-of-scope/adversarial case. Match `required_facts` against the deterministic answer text and preserve missing facts explicitly.

- [ ] **Step 5: Implement aggregate metrics**

Group totals by category. Compute HTTP success rate, source hit rate over cases with expected sources, required-fact coverage over all non-empty fact requirements, out-of-scope refusal rate, no-match model short-circuit rate, retrieval error rate, mean latency, and P95 using `ceil(0.95 * n) - 1` with bounds checking. Return `None` for a ratio with no denominator instead of inventing zero.

- [ ] **Step 6: Run focused runner tests and verify GREEN**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/evals/test_cases.py backend/evals/test_runner.py -q
```

Expected: all focused evaluation tests pass with no network call.

- [ ] **Step 7: Commit the runner**

```bash
git add backend/evals
git commit -m "test: add offline agent evaluation runner"
```

---

### Task 3: Add sanitized engineering report and website blog draft

**Files:**
- Create: `docs/evals/version-0-baseline.md`
- Create: `src/content/posts/version-0-evaluation-baseline.md`

**Interfaces:**
- The CLI writes the engineering report after each run using aggregate metrics and failure IDs only.
- The blog draft is a content-collection-compatible Markdown post and does not expose raw questions, answers, secrets, IPs, tokens, or provider errors.

- [ ] **Step 1: Write report-format tests**

```python
from app.evals.runner import render_report


def test_render_report_includes_metric_definitions_and_sanitized_failures():
    report = render_report(
        {"total_cases": 1, "source_hit_rate": 0.5},
        [{"id": "case-1", "error": "source mismatch"}],
    )

    assert "source_hit_rate" in report
    assert "case-1" in report
    assert "source mismatch" in report
    assert "API Key" not in report
```

- [ ] **Step 2: Run the focused report test and confirm RED**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/evals/test_runner.py::test_render_report_includes_metric_definitions_and_sanitized_failures -q
```

Expected: failure because report rendering is not implemented.

- [ ] **Step 3: Implement report rendering and add the blog frontmatter**

The report must include run timestamp, case counts, metric definitions, actual values, category summary, failed case IDs, and automatic-evaluation limitations. The blog must use the existing content schema fields (`title`, `slug`, `date`, `status`, `summary`, `tags`) and clearly label the post as a draft. Do not paste every evaluation question into either document.

- [ ] **Step 4: Run report and Astro content checks**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/evals/test_runner.py -q
npm run check
```

Expected: focused tests pass and Astro reports zero errors, warnings, and hints.

- [ ] **Step 5: Run the offline CLI once and inspect generated output**

```bash
PYTHONPATH=backend backend/.venv/bin/python backend/evals/runner.py
python -m json.tool artifacts/evals/version-0-results.json >/dev/null
sed -n '1,240p' docs/evals/version-0-baseline.md
```

Verify that output contains no secrets or full raw conversations. Leave `artifacts/` untracked.

- [ ] **Step 6: Commit report and blog**

```bash
git add docs/evals/version-0-baseline.md src/content/posts/version-0-evaluation-baseline.md
git commit -m "docs: record version zero evaluation baseline"
```

---

### Task 4: Run full regression and final cleanliness checks

**Files:**
- No source changes expected; only correct failures discovered by verification.

- [ ] **Step 1: Run backend tests including eval tests**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests backend/evals -q
```

Expected: all tests pass without network access.

- [ ] **Step 2: Run frontend tests**

```bash
npm test -- --run
```

Expected: all frontend tests pass.

- [ ] **Step 3: Run Astro check and static build**

```bash
npm run check
npm run build
```

Expected: zero Astro errors, warnings, and hints; all existing static pages build.

- [ ] **Step 4: Check diff and repository boundaries**

```bash
git diff --check
git status --short --branch
git diff --name-only origin/codex/online-preview-closure...HEAD
```

Verify only the planned evaluation files and ignored local artifacts changed. Confirm no `knowledge/`, `backend/app/`, frontend, Vercel, or environment files were modified.

- [ ] **Step 5: Commit any verification-only fix and report the baseline**

If a fix is needed, add a focused test first, run the failing test, apply the smallest fix, and rerun the full suite. Do not push or deploy in this phase unless separately requested. Final report must include actual case count, all metric values, test counts, and the known limitation that semantic answer quality still needs manual or live evaluation.

## Final Verification Checklist

- [ ] At least 24 unique cases cover all five categories.
- [ ] Runner uses real FastAPI validation/retrieval/short-circuit logic and a test-only Fake Provider.
- [ ] No network, API key, Vercel, or Production access occurs during evaluation.
- [ ] Results are machine-readable and reports are sanitized.
- [ ] Source hit, fact proxy coverage, boundary refusal, short-circuit, error rate, mean latency, and P95 definitions match the spec.
- [ ] Backend, frontend, Astro check, Astro build, and `git diff --check` pass.
- [ ] Website blog labels automatic evaluation limitations accurately.
