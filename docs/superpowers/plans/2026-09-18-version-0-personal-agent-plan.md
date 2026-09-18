# Version 0 Personal Knowledge Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a minimal, grounded personal Q&A Agent that serves verified personal资料 as fixed context through a FastAPI `/api/chat` endpoint and can be selected by the existing Astro chat UI.

**Architecture:** Keep the Astro site static and add a `backend/` FastAPI service in the same repository. The service loads two small Markdown knowledge files, builds one system prompt, sends the question plus limited conversation history to an OpenAI-compatible endpoint, and returns a stable response contract. The frontend keeps demo mode when `PUBLIC_AGENT_API_URL` is absent and uses the remote service when it is configured.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic Settings, OpenAI-compatible Python SDK, pytest, HTTPX, Astro, React, TypeScript.

**Spec:** `docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md` (Version 0 narrows that design to fixed-context remote Q&A; it does not implement RAG, LangChain, ChromaDB, embeddings, tools, memory storage, or streaming).

## Global Constraints

- The public website remains a static Astro build; the FastAPI service is deployed separately.
- Version 0 uses only verified `profile.md` and `spmtrack.md` content; unknown facts must be answered as unknown.
- No LangChain, ChromaDB, embeddings, vector search, tool calling, persistent conversation storage, or background jobs.
- The browser never receives `OPENAI_API_KEY`; the key is read only by the backend process.
- `POST /api/chat` accepts at most 8 history messages and a 2,000-character user message.
- The backend returns a stable JSON response and never exposes raw upstream exception text.
- Missing `PUBLIC_AGENT_API_URL` keeps the existing local demo mode; a configured remote URL does not silently fall back to fake answers.
- Secrets and real `.env` files are ignored; only `.env.example` files are committed.
- Every task ends with focused tests before its commit; the full suite, Astro check, and production build run before integration.

## File Map

- Create `backend/requirements.txt`: runtime and test dependencies.
- Create `backend/.env.example`: documented backend settings with non-secret placeholders.
- Create `backend/app/config.py`: typed environment settings and defaults.
- Create `backend/app/models.py`: request and response schemas.
- Create `backend/app/knowledge.py`: deterministic loading of the fixed Markdown corpus.
- Create `backend/app/prompts.py`: grounding system prompt and message construction.
- Create `backend/app/llm.py`: one OpenAI-compatible completion adapter with timeout handling.
- Create `backend/app/main.py`: FastAPI app, CORS, health endpoint, chat endpoint, and public error mapping.
- Create `backend/tests/test_knowledge.py`, `backend/tests/test_llm.py`, and `backend/tests/test_api.py`: isolated and API-level tests.
- Create `knowledge/profile.md` and `knowledge/spmtrack.md`: verified Version 0 corpus with source labels.
- Create `.env.example`: frontend setting `PUBLIC_AGENT_API_URL=http://localhost:8000`.
- Modify `src/lib/agent/types.ts`: allow assistant source labels and remote/demo mode metadata.
- Modify `src/lib/agent/client.ts`: select demo or remote transport based on `PUBLIC_AGENT_API_URL`.
- Modify `src/components/ChatPanel.tsx`: retain error behavior and show returned source labels/mode.
- Modify `tests/agent/demo.test.ts` and create `tests/agent/client.test.ts`: preserve demo behavior and test remote request parsing.
- Modify `README.md`: add Version 0 local startup, environment, API contract, and security notes.

## API Contract

`POST /api/chat`

Request:

```json
{
  "message": "SPMTrack 使用了哪些服务？",
  "history": [
    {"role": "user", "content": "你是谁？"},
    {"role": "assistant", "content": "我是吴禹……"}
  ]
}
```

Response `200`:

```json
{
  "answer": "SPMTrack 将 React 工作台、Spring Boot 网关、FastAPI 推理服务和跟踪引擎分层组合。",
  "sources": ["个人资料", "SPMTrack 项目资料"],
  "mode": "remote"
}
```

Public error behavior:

- `422`: FastAPI validation response for empty or oversized input.
- `503`: missing backend API key or unavailable model configuration.
- `502`: upstream model request failed or timed out; body contains only a stable Chinese error message.
- `GET /health`: `{"status":"ok"}` without testing the model or revealing configuration values.

## Tasks

### Task 1: Add the backend skeleton and typed configuration

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/models.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_api.py`

**Interfaces:**
- `Settings`: `openai_api_key: str | None`, `openai_base_url: str | None`, `openai_model: str`, `allowed_origins: list[str]`, `max_history: int`, `max_message_chars: int`, `llm_timeout_seconds: float`.
- `ChatMessage`: `role` is `user | assistant`; `content` is a non-empty string.
- `ChatRequest`: `message` plus `history`, with the limits in the API contract.
- `ChatResponse`: `answer`, `sources`, and `mode` where mode is `remote`.

- [ ] **Step 1: Write failing tests** for `GET /health`, empty message rejection, oversized message rejection, and response schema import.
- [ ] **Step 2: Run `cd backend && pytest -q tests/test_api.py`** and confirm collection fails because the app and models do not exist.
- [ ] **Step 3: Add the dependency file, settings model, request/response models, and a minimal FastAPI app with `/health` and a placeholder `/api/chat`.
- [ ] **Step 4: Run the focused tests** and confirm health and validation pass.
- [ ] **Step 5: Commit with `git add backend && git commit -m "feat: add version zero agent backend skeleton"`.

### Task 2: Add the verified fixed-context corpus and prompt builder

**Files:**
- Create: `knowledge/profile.md`
- Create: `knowledge/spmtrack.md`
- Create: `backend/app/knowledge.py`
- Create: `backend/app/prompts.py`
- Create: `backend/tests/test_knowledge.py`

**Interfaces:**
- `load_knowledge() -> list[KnowledgeDocument]` returns exactly two documents with stable source labels and non-empty content.
- `build_messages(question: str, history: list[ChatMessage], documents: list[KnowledgeDocument]) -> list[dict[str, str]]` returns one grounding system message, bounded history, and the current user message.

- [ ] **Step 1: Write tests** asserting both source labels load, the prompt contains the verified corpus, history is capped at `settings.max_history`, and the prompt instructs the model to say when information is unavailable.
- [ ] **Step 2: Run `cd backend && pytest -q tests/test_knowledge.py`** and confirm failure because corpus loading and prompt functions do not exist.
- [ ] **Step 3: Copy only confirmed facts from the existing profile and SPMTrack pages into the two Markdown files; include a short `Source` line in each file. Implement deterministic UTF-8 loading relative to the repository root.
- [ ] **Step 4: Run the focused tests** and confirm the context and grounding rules are present.
- [ ] **Step 5: Commit with `git add knowledge backend/app backend/tests/test_knowledge.py && git commit -m "feat: add grounded version zero knowledge corpus"`.

### Task 3: Implement the model adapter with safe failure mapping

**Files:**
- Create: `backend/app/llm.py`
- Create: `backend/tests/test_llm.py`
- Modify: `backend/app/config.py`

**Interfaces:**
- `async generate_answer(messages: list[dict[str, str]], settings: Settings) -> str` returns stripped model text.
- Raises `ConfigurationError` when `openai_api_key` is absent.
- Raises `ModelUnavailableError` for timeout, connection, empty, or provider errors; raw provider text never reaches the API response.

- [ ] **Step 1: Write tests** with a fake client for successful text extraction, missing key, empty model output, and provider exception mapping.
- [ ] **Step 2: Run `cd backend && pytest -q tests/test_llm.py`** and confirm failure because the adapter and exceptions do not exist.
- [ ] **Step 3: Implement one OpenAI-compatible client using `openai.AsyncOpenAI` with optional `base_url`, the configured model, and a timeout. Keep the client behind the adapter so API tests do not call the network.
- [ ] **Step 4: Run the focused tests** and confirm all adapter cases pass.
- [ ] **Step 5: Commit with `git add backend/app backend/tests/test_llm.py && git commit -m "feat: add openai compatible model adapter"`.

### Task 4: Connect FastAPI chat, CORS, and stable public errors

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- `POST /api/chat` loads the corpus, builds grounded messages, calls `generate_answer`, and returns `ChatResponse(answer, sources, mode="remote")`.
- `ALLOWED_ORIGINS` is parsed as a comma-separated list and applied through `CORSMiddleware`.

- [ ] **Step 1: Extend API tests** by monkeypatching `generate_answer` to assert request history reaches the prompt builder, sources are returned, missing configuration maps to `503`, model failures map to `502`, and CORS exposes the configured frontend origin.
- [ ] **Step 2: Run `cd backend && pytest -q tests/test_api.py`** and confirm the new behavior fails before implementation.
- [ ] **Step 3: Wire the endpoint with dependency-injected settings and adapter calls. Return stable Chinese messages for configuration and upstream failures; never serialize exception details.
- [ ] **Step 4: Run the API tests** and confirm all success, validation, CORS, and error cases pass.
- [ ] **Step 5: Commit with `git add backend/app/main.py backend/tests/test_api.py && git commit -m "feat: expose grounded chat api"`.

### Task 5: Switch the existing frontend between demo and remote modes

**Files:**
- Create: `.env.example`
- Modify: `src/lib/agent/types.ts`
- Modify: `src/lib/agent/client.ts`
- Modify: `src/components/ChatPanel.tsx`
- Modify: `tests/agent/demo.test.ts`
- Create: `tests/agent/client.test.ts`

**Interfaces:**
- `askKnowledgeBase(question: string, history: AgentMessage[]): Promise<AgentResponse>` remains the only chat entry point used by the component.
- Remote requests post to `${PUBLIC_AGENT_API_URL.replace(/\/$/, '')}/api/chat` with `{ message: question, history }` and parse `{ answer, sources, mode }`.
- Absent URL uses `getDemoResponse`; configured URL plus a non-2xx response throws an error so the UI displays its existing retry state.

- [ ] **Step 1: Write tests** for demo-mode preservation, exact remote request body, response validation, and non-2xx failure propagation.
- [ ] **Step 2: Run `npm run test -- tests/agent/client.test.ts tests/agent/demo.test.ts`** and confirm remote tests fail before the transport exists.
- [ ] **Step 3: Implement the environment switch with `import.meta.env.PUBLIC_AGENT_API_URL`, a bounded fetch timeout using `AbortController`, and source/mode preservation in assistant messages. Display returned source labels and distinguish `演示模式` from `远程模式`.
- [ ] **Step 4: Run the focused frontend tests** and confirm existing ChatPanel behavior remains green.
- [ ] **Step 5: Commit with `git add .env.example src tests/agent && git commit -m "feat: connect chat ui to version zero api"`.

### Task 6: Add local startup documentation and manual acceptance checks

**Files:**
- Modify: `README.md`
- Modify: `.gitignore` only if needed to cover `backend/.venv/` and `backend/.env`.

- [ ] **Step 1: Add exact setup commands:** `python3 -m venv backend/.venv`, `backend/.venv/bin/pip install -r backend/requirements.txt`, copy `backend/.env.example` to `backend/.env`, and start `backend/.venv/bin/uvicorn app.main:app --reload --port 8000` from `backend/`.
- [ ] **Step 2: Document frontend startup with `PUBLIC_AGENT_API_URL=http://localhost:8000 npm run dev` and explain that the empty variable intentionally keeps demo mode.
- [ ] **Step 3: Document the API contract, required environment variables, no-key behavior, and the rule that real `.env` files must never be committed.
- [ ] **Step 4: Run `git diff --check` and verify `git check-ignore backend/.env backend/.venv` returns ignored paths.
- [ ] **Step 5: Commit with `git add README.md .gitignore && git commit -m "docs: document version zero agent setup"`.

### Task 7: Run the complete verification and manual smoke test

**Files:**
- No source changes expected; only fix issues discovered by verification.

- [ ] **Step 1: Run backend tests:** `cd backend && pytest -q` and require all tests to pass without a network call.
- [ ] **Step 2: Run frontend tests:** `npm run test` and require all test files to pass.
- [ ] **Step 3: Run static checks:** `npm run check` and require 0 errors, warnings, and hints.
- [ ] **Step 4: Run production build:** `npm run build` and require the five existing static routes to build.
- [ ] **Step 5: With a test API key configured locally, call `curl -sS http://localhost:8000/health` and one `POST /api/chat`; verify the answer is grounded in the two corpus files, sources are returned, and an unknown question receives an explicit unknown response.
- [ ] **Step 6: Verify `git status --short`, `git diff --check`, and `gh repo view BWBYB/wu-yu-portfolio --json isPrivate,defaultBranchRef`; only after the user reviews the changes should the commits be pushed.

## Version 0 Acceptance Checklist

- [ ] `GET /health` returns `{"status":"ok"}` without an API key.
- [ ] A valid chat request returns `answer`, `sources`, and `mode: "remote"`.
- [ ] The model receives the two verified Markdown documents and the recent bounded history.
- [ ] Questions outside the corpus receive a clear unknown answer instead of an invented fact.
- [ ] Empty, oversized, and overlong-history requests are rejected before the model call.
- [ ] Missing credentials return a stable `503`; provider failures return a stable `502`.
- [ ] CORS allows only configured origins.
- [ ] The frontend uses remote mode only when `PUBLIC_AGENT_API_URL` is set and preserves demo mode otherwise.
- [ ] No API key, real `.env`, conversation log, database, or generated build output is committed.
- [ ] Backend tests, frontend tests, Astro check, and production build all pass.
