# Agent V1 轻量检索 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变线上 `/api/chat` 契约的前提下，把完整语料 Prompt 升级为可解释的轻量片段检索问答。

**Architecture:** 保留 `KnowledgeDocument` 作为文件读取层，新增不可变 `KnowledgeChunk` 作为检索边界。`knowledge.py` 负责稳定切片，`retrieval.py` 负责无依赖词法评分，`prompts.py` 只接收命中的片段，FastAPI 根据命中片段返回去重来源并记录脱敏统计。

**Tech Stack:** Python 3.11/3.12+, FastAPI, pytest, 现有 OpenAI-compatible client；不增加运行时依赖。

**Spec:** `docs/superpowers/specs/2026-09-19-agent-v1-retrieval-design.md`

## Global Constraints

- 保持 `POST /api/chat` 的请求字段 `message`、`history` 不变。
- 保持 `ChatResponse` 的 `answer`、`sources`、`mode` 字段不变。
- `mode` 继续为 `remote`；`sources` 改为本次实际命中的去重来源。
- 不引入 LangChain、ChromaDB、Embedding API 或其他新的运行时依赖。
- 无匹配问题返回 HTTP 200 和 `sources: []`，不得把无关片段注入 Prompt。
- 现有 2000 字消息限制、8 条历史限制、502/503 错误和日志脱敏行为保持不变。
- 不记录原始问题、完整 Prompt、API Key 或模型回答。
- 每个任务遵循 RED -> GREEN -> REFACTOR，并在任务结束运行对应测试。

### Task 1: Define and test stable knowledge chunks

**Files:**
- Modify: `backend/app/knowledge.py`
- Create: `backend/app/retrieval.py`
- Create: `backend/tests/test_retrieval.py`

**Interfaces:**
- `backend/app/knowledge.py` exports `KnowledgeDocument`, `KnowledgeChunk`, and `build_chunks(documents: tuple[KnowledgeDocument, ...]) -> tuple[KnowledgeChunk, ...]`.
- `backend/app/retrieval.py` exports `retrieve_chunks(question: str, chunks: tuple[KnowledgeChunk, ...], top_k: int = 4, min_score: int = 3) -> tuple[KnowledgeChunk, ...]`.
- `build_chunks` keeps document source, heading, original content, and deterministic `source:index` chunk IDs.

- [ ] **Step 1: Write failing chunk and retrieval tests**

Add tests with small in-memory documents:

```python
def test_build_chunks_preserves_heading_source_and_stable_ids():
    documents = (
        KnowledgeDocument(source="个人资料", content="# 技术栈\n\nReact、FastAPI"),
    )

    chunks = build_chunks(documents)

    assert chunks == (
        KnowledgeChunk(
            chunk_id="个人资料:0",
            source="个人资料",
            heading="技术栈",
            content="React、FastAPI",
        ),
    )


def test_retrieve_chunks_prefers_matching_project_content():
    chunks = build_chunks(
        (
            KnowledgeDocument(source="个人资料", content="# 技术\n\nReact、FastAPI"),
            KnowledgeDocument(source="SPMTrack 项目资料", content="# 流程\n\nROI、任务队列和跟踪引擎"),
        )
    )

    result = retrieve_chunks("SPMTrack 的 ROI 和任务队列", chunks)

    assert result[0].source == "SPMTrack 项目资料"


def test_retrieve_chunks_returns_empty_for_unknown_question():
    chunks = build_chunks((KnowledgeDocument(source="个人资料", content="# 技术\n\nReact、FastAPI"),))

    assert retrieve_chunks("喜欢什么颜色", chunks) == ()


def test_retrieve_chunks_is_bounded_and_deterministic():
    chunks = tuple(
        KnowledgeChunk(str(index), "资料", "标题", "FastAPI")
        for index in range(6)
    )

    result = retrieve_chunks("FastAPI", chunks)

    assert len(result) == 4
    assert [chunk.chunk_id for chunk in result] == ["0", "1", "2", "3"]
```

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_retrieval.py -q
```

Expected: collection or assertion failures because `KnowledgeChunk`, `build_chunks`, `retrieve_chunks`, and the retrieval behavior do not exist yet.

- [ ] **Step 3: Implement the minimum chunk builder**

In `backend/app/knowledge.py`, add the frozen dataclass and parse Markdown line-by-line:

```python
@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    heading: str
    content: str
```

Track the latest `#`-through-`######` heading, collect non-empty lines into paragraphs, and split content over 900 Unicode characters at `。`, `；`, `;`, or fixed 900-character boundaries. Preserve paragraph order and assign IDs using the source and zero-based output index.

- [ ] **Step 4: Implement the minimum dependency-free retriever**

In `backend/app/retrieval.py`:

1. Normalize query text to lowercase.
2. Extract alphanumeric/technical tokens with a regular expression and Chinese bigram/trigram sequences.
3. Remove a small in-module stopword set and one-character tokens.
4. Score each chunk once per distinct token: `+3` for a content match and `+2` for a heading match.
5. Sort by descending score and original chunk order, filter scores below `min_score`, and return at most `top_k` chunks.

- [ ] **Step 5: Run focused tests and confirm GREEN**

Run the same pytest command. Expected: all retrieval tests pass.

- [ ] **Step 6: Refactor only after green**

Keep token extraction and scoring as small pure helpers. Re-run `backend/tests/test_retrieval.py -q` after any cleanup.

- [ ] **Step 7: Commit the retrieval unit**

```bash
git add backend/app/knowledge.py backend/app/retrieval.py backend/tests/test_retrieval.py
git commit -m "feat: add lightweight knowledge retrieval"
```

### Task 2: Restrict Prompt context to retrieved chunks

**Files:**
- Modify: `backend/app/prompts.py`
- Modify: `backend/tests/test_knowledge.py`

**Interfaces:**
- `build_messages(question: str, history: list[ChatMessage], chunks: tuple[KnowledgeChunk, ...], max_history: int) -> list[dict[str, str]]`.
- The system message formats each selected chunk as `[Source: ...][Section: ...]` and contains no unselected document text.

- [ ] **Step 1: Replace existing full-corpus assertions with failing chunk-context tests**

Add a test that passes one selected chunk and asserts its content and source appear, while an unselected chunk does not:

```python
def test_build_messages_contains_only_selected_chunks():
    selected = (
        KnowledgeChunk("profile:0", "个人资料", "技术栈", "React、FastAPI"),
    )
    unselected = KnowledgeChunk("spmtrack:0", "SPMTrack 项目资料", "流程", "ROI 和任务队列")

    system = build_messages("技术栈", [], selected, max_history=8)[0]["content"]

    assert "React、FastAPI" in system
    assert "ROI 和任务队列" not in system
    assert "information is unavailable" in system.lower()
```

Also add a no-match test using `chunks=()` that confirms the system message still contains the grounding rule and no project content.

- [ ] **Step 2: Run the focused Prompt tests and confirm RED**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_knowledge.py -q
```

Expected: failures because the current function accepts `documents` and always builds the full corpus.

- [ ] **Step 3: Implement the new Prompt input**

Change `build_messages` to format only the provided chunks, include the heading, retain the no-speculation rule, preserve bounded history, and append the current user question last.

- [ ] **Step 4: Run Prompt tests and confirm GREEN**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_knowledge.py -q
```

- [ ] **Step 5: Commit the Prompt boundary**

```bash
git add backend/app/prompts.py backend/tests/test_knowledge.py
git commit -m "feat: ground prompts with retrieved chunks"
```

### Task 3: Integrate retrieval into `/api/chat` and structured logs

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/tests/test_api.py`

**Interfaces:**
- The route remains `POST /api/chat` and returns the existing `ChatResponse` model.
- `main.py` continues importing `load_knowledge` so existing dependency-overrides tests can substitute fixture documents.
- New internal flow: `documents = load_knowledge()` -> `chunks = build_chunks(tuple(documents))` -> `selected = retrieve_chunks(request.message, chunks)` -> `build_messages(..., selected, ...)`.

- [ ] **Step 1: Add failing API tests for selected and empty sources**

Extend the existing API test with monkeypatched fixture chunks and retriever behavior:

```python
async def fake_generate_answer(messages, settings):
    return "测试回答"


def test_chat_returns_only_retrieved_sources(monkeypatch):
    selected = (KnowledgeChunk("spmtrack:0", "SPMTrack 项目资料", "流程", "ROI"),)
    monkeypatch.setattr(main, "load_knowledge", lambda: [
        KnowledgeDocument(source="个人资料", content="profile"),
        KnowledgeDocument(source="SPMTrack 项目资料", content="project"),
    ])
    monkeypatch.setattr(main, "build_chunks", lambda documents: (selected,))
    monkeypatch.setattr(main, "retrieve_chunks", lambda question, chunks: selected)
    monkeypatch.setattr(main, "build_messages", lambda **kwargs: [{"role": "user", "content": kwargs["question"]}])
    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)

    response = client.post("/api/chat", json={"message": "ROI"})

    assert response.json()["sources"] == ["SPMTrack 项目资料"]


def test_chat_returns_empty_sources_when_retrieval_finds_nothing(monkeypatch):
    monkeypatch.setattr(main, "retrieve_chunks", lambda question, chunks: ())
    monkeypatch.setattr(main, "generate_answer", fake_generate_answer)

    response = client.post("/api/chat", json={"message": "未收录的问题"})

    assert response.status_code == 200
    assert response.json()["sources"] == []
```

- [ ] **Step 2: Run the focused API tests and confirm RED**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_api.py -q
```

Expected: failures because `main.py` currently sends all documents to Prompt construction and returns all document sources.

- [ ] **Step 3: Implement the route integration**

Import the chunk builder and retriever, pass selected chunks into `build_messages`, derive sources with insertion-order deduplication, and set:

```python
request.state.retrieved_chunks = len(selected_chunks)
request.state.retrieved_sources_count = len(selected_sources)
```

Extend the structured metadata dictionary with both fields, defaulting to `None` for non-chat routes. Do not log raw text.

- [ ] **Step 4: Run focused API tests and confirm GREEN**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests/test_api.py -q
```

- [ ] **Step 5: Run the complete backend suite**

```bash
PYTHONPATH=backend backend/.venv/bin/python -m pytest backend/tests tests/test_deploy_entrypoint.py -q
```

Expected: all backend and deployment-entrypoint tests pass, with only the existing dependency deprecation warnings if they remain present.

- [ ] **Step 6: Commit the API integration**

```bash
git add backend/app/main.py backend/tests/test_api.py
git commit -m "feat: integrate retrieval into chat endpoint"
```

### Task 4: Update documentation and verify the local product

**Files:**
- Modify: `src/content/posts/online-preview-deployment.md`
- Modify: `README.md`

- [ ] **Step 1: Identify the exact outdated claims**

Run:

```bash
rg -n "固定|全部资料|完整资料|完整语料|未来会接入|本地演示" README.md src/content/posts/online-preview-deployment.md src/components
```

Use the current matches in `README.md` to update the API example from fixed sources to actual retrieved sources, and state that Version 0 used full-corpus Prompt injection while Version 1 uses lexical retrieval. Keep the existing deployment post's completed Preview records unchanged except for the new Version 1 stage entry.

- [ ] **Step 2: Update the stage draft**

Record that Version 0 used full-corpus Prompt injection and Version 1 now uses dependency-free lexical retrieval, while marking ChromaDB/Embedding as later replacement work. Do not claim semantic embeddings or complete RAG.

- [ ] **Step 3: Run frontend verification**

```bash
npm test -- --run
npm run check
npm run build
```

Expected: 17 frontend tests pass, Astro reports 0 errors/warnings/hints, and 5 static pages build successfully.

- [ ] **Step 4: Commit documentation**

```bash
git add src/content/posts/online-preview-deployment.md README.md
git commit -m "docs: describe agent v1 retrieval boundary"
```

### Task 5: Preview deployment and end-to-end acceptance

**Files:**
- No source files; use the already linked Vercel project and existing Preview variables.

- [ ] **Step 1: Push the implementation branch**

```bash
git push origin HEAD:codex/online-preview-closure
```

- [ ] **Step 2: Wait for a Ready Preview**

```bash
vercel ls --limit 5
vercel inspect <preview-url> --wait
```

Expected: the deployment is `Ready` and contains `api/index` plus `api/[...path]`.

- [ ] **Step 3: Verify health and a related question**

```bash
vercel curl <preview-url>/api/health
vercel curl <preview-url>/api/chat -- \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{"message":"你在 SPMTrack 中负责什么？","history":[]}'
```

Expected: health returns `{"status":"ok"}`; the chat response has `mode: "remote"`, at least the SPMTrack source, and an answer grounded in the selected project chunk.

- [ ] **Step 4: Verify an unknown question**

```bash
vercel curl <preview-url>/api/chat -- \
  --request POST \
  --header 'Content-Type: application/json' \
  --data '{"message":"你最喜欢的颜色是什么？","history":[]}'
```

Expected: HTTP 200, `sources: []`, and an answer that states the information is unavailable rather than inventing a personal preference.

- [ ] **Step 5: Inspect sanitized Runtime Logs**

```bash
vercel logs <preview-url> --limit 20
```

Expected: logs include `retrieved_chunks`, `retrieved_sources_count`, status, duration, and request ID; logs do not include the raw question, answer, API Key, or full Prompt.

- [ ] **Step 6: Record the Preview result**

Update the deployment post with the final Preview URL, the related/unknown question results, and any latency or Deployment Protection caveat. Do not configure Production variables or promote the deployment in this plan.

## Final Verification Checklist

- [ ] `backend/tests/test_retrieval.py` passes.
- [ ] `backend/tests/test_knowledge.py` passes.
- [ ] `backend/tests/test_api.py` passes.
- [ ] `backend/tests` and `tests/test_deploy_entrypoint.py` pass as one complete backend command.
- [ ] `npm test -- --run` passes.
- [ ] `npm run check` reports 0 errors, warnings, and hints.
- [ ] `npm run build` builds all 5 static pages.
- [ ] `git diff --check` passes.
- [ ] Preview health, related question, unknown question, and sanitized logs are verified.
