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
    cases = [case for case in load_cases() if case.category == "out_of_scope"]

    assert cases
    assert all(case.expected_sources == () for case in cases)
    assert all(case.required_facts == () for case in cases)
    assert all(case.should_answer is False for case in cases)
    assert all(case.expected_model_call is False for case in cases)


def test_out_of_scope_set_contains_a_real_no_match_case():
    from app.knowledge import build_chunks, load_knowledge
    from app.retrieval import retrieve_chunks

    chunks = build_chunks(tuple(load_knowledge()))
    out_of_scope = [case for case in load_cases() if case.category == "out_of_scope"]

    assert any(not retrieve_chunks(case.question, chunks) for case in out_of_scope)


def test_loader_rejects_missing_required_fields(tmp_path):
    invalid = tmp_path / "cases.json"
    invalid.write_text('[{"id": "bad"}]', encoding="utf-8")

    try:
        load_cases(invalid)
    except ValueError as error:
        assert "category" in str(error)
    else:
        raise AssertionError("invalid cases must be rejected")


def _valid_case(**overrides):
    case = {
        "id": "case-1",
        "question": "一个问题",
        "category": "profile_fact",
        "expected_sources": ["个人资料"],
        "required_facts": ["React"],
        "should_answer": True,
        "expected_model_call": True,
    }
    case.update(overrides)
    return case


def test_loader_rejects_duplicate_ids_and_unknown_categories(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        __import__("json").dumps([_valid_case(), _valid_case()]), encoding="utf-8"
    )
    try:
        load_cases(duplicate)
    except ValueError as error:
        assert "duplicate case id" in str(error)
    else:
        raise AssertionError("duplicate IDs must be rejected")

    unknown = tmp_path / "unknown.json"
    unknown.write_text(__import__("json").dumps([_valid_case(category="unknown")]), encoding="utf-8")
    try:
        load_cases(unknown)
    except ValueError as error:
        assert "unknown" in str(error)
    else:
        raise AssertionError("unknown categories must be rejected")


def test_loader_rejects_invalid_lists_blank_strings_and_inconsistent_boundaries(tmp_path):
    invalid_cases = (
        (_valid_case(expected_sources="个人资料"), "must be a list"),
        (_valid_case(question="   "), "non-blank string"),
        (
            _valid_case(
                category="out_of_scope",
                expected_sources=[],
                required_facts=[],
                should_answer=False,
                expected_model_call=True,
            ),
            "out_of_scope",
        ),
    )
    for index, (case, message) in enumerate(invalid_cases):
        path = tmp_path / f"invalid-{index}.json"
        path.write_text(__import__("json").dumps([case]), encoding="utf-8")
        try:
            load_cases(path)
        except ValueError as error:
            assert message in str(error)
        else:
            raise AssertionError("invalid case must be rejected")
