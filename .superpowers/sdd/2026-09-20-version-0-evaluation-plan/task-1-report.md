# Task 1 Report: Version Zero Evaluation Cases

## Status

Complete. Commit: `9127aa6a27dfee7190429a419ea42dc080d0a898`

## Changed files

- `backend/app/evals/__init__.py`
- `backend/app/evals/cases.py`
- `backend/evals/__init__.py`
- `backend/evals/cases.json`
- `backend/evals/test_cases.py`
- `.gitignore`

The loader is exposed from `app.evals.cases`, matching the import contract in the plan. The JSON data and evaluation tests remain under `backend/evals/` as specified.

## Implementation

- Added an immutable `EvaluationCase` dataclass.
- Added `load_cases(path=None)` with a default path resolved relative to the loader module.
- Validates required fields, blank strings, list and boolean types, known categories, duplicate IDs, and out-of-scope boundary consistency.
- Added 28 safe cases across `profile_fact`, `project_fact`, `paraphrase`, `out_of_scope`, and `adversarial`.
- Added `artifacts/evals/` to `.gitignore`.

## Verification

TDD red phase:

```text
PYTHONPATH=backend /Users/Admin/Documents/ChatGPT/个人网站/backend/.venv/bin/python -m pytest backend/evals/test_cases.py -q
```

Initially failed during collection with `ModuleNotFoundError: No module named 'app.evals'`, confirming the missing loader contract.

Fresh green results:

```text
5 passed in 0.02s
```

Case inventory check:

```text
28 ['adversarial', 'out_of_scope', 'paraphrase', 'profile_fact', 'project_fact']
```

Existing backend regression suite:

```text
37 passed, 2 warnings in 0.54s
```

Artifact ignore check:

```text
.gitignore:7:artifacts/evals/ artifacts/evals/.keep
```

`git diff --check` passed.

## Concerns

- The worktree has no own `backend/.venv`; verification used the existing project environment at `/Users/Admin/Documents/ChatGPT/个人网站/backend/.venv/bin/python`. No dependencies or environment files were changed.
- The brief lists `backend/evals/cases.py` but its required import is `app.evals.cases`; the implementation follows the import contract by placing the loader at `backend/app/evals/cases.py` and keeps the case asset at `backend/evals/cases.json`.
