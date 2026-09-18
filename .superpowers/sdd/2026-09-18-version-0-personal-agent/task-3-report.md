# Task 3 implementation report

## Outcome

Implemented the backend model boundary in `backend/app/llm.py` using one OpenAI-compatible `AsyncOpenAI` client. The adapter accepts the fixed prompt-builder message shape, applies the configured model and timeout, supports an optional base URL, returns stripped text, and exposes typed failures for the later FastAPI boundary.

## TDD evidence

1. Wrote `backend/tests/test_llm.py` first with a fake async client covering:
   - successful response extraction and whitespace stripping;
   - configured model, optional base URL, API key, and timeout propagation;
   - missing API key as `ConfigurationError`;
   - `None`, empty, and whitespace-only model output as `ModelUnavailableError`;
   - provider exception mapping without leaking the provider's raw message.
2. Ran the requested initial command, `cd backend && pytest -q tests/test_llm.py`. The checkout shell did not have `pytest` installed, so it failed at command lookup (`pytest: command not found`) before collection. The available system Python was also 3.9, while the existing backend uses Python 3.10+ union type syntax.
3. Created a temporary Python 3.11 environment with the declared backend dependencies and ran the focused suite: `6 passed`.
4. Ran the complete backend suite in that environment: `16 passed`, with two existing dependency deprecation warnings from FastAPI/Starlette/httpx.

## Files

- Created `backend/app/llm.py`.
  - `ConfigurationError` is raised when `settings.openai_api_key` is absent.
  - `ModelUnavailableError` is raised for empty output and all client/provider/transport exceptions.
  - Raw provider exception text is kept only as an exception cause and is not exposed in the public error message.
  - Provider details stay behind `generate_answer`; no browser-side secret, LangChain, RAG, persistence, or streaming behavior was added.
- Created `backend/tests/test_llm.py` with the focused fake-client tests.
- `backend/app/config.py` was inspected and required no changes: it already contains the agreed optional base URL, configured model, and positive timeout setting.

## Concerns / follow-up

- The adapter currently creates an `AsyncOpenAI` client per call. This keeps lifecycle ownership local to the model boundary and is sufficient for Version 0; reuse can be considered later if profiling shows a need.
- The current test environment emits existing FastAPI/Starlette/httpx deprecation warnings; they are unrelated to this task.

## Review fix

The review identified that the per-call `AsyncOpenAI` client was not closed. Updated `generate_answer` to await `client.close()` in a `finally` block on both successful and failing provider calls, and extended the fake-client success test to assert closure. The existing public behavior and exception mapping are unchanged.

Focused verification after the fix: `6 passed`.

The focused tests also explicitly exercise closure after empty-output and provider-exception paths.
