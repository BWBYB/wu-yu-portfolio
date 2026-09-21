# RAG V2 Local Vector Retrieval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本地完成 E5 Embedding + ChromaDB 知识库检索，并在向量组件不可用时回退到现有词法 RAG。

**Architecture:** 复用 `build_chunks()` 生成稳定的 `KnowledgeChunk`，通过懒加载的本地 E5 provider 生成归一化向量，使用 cosine distance 的 ChromaDB PersistentClient 保存和查询。`retrieve_relevant_chunks()` 负责选择 vector/lexical 模式，向量异常时回退词法检索，资料外无命中时沿用 `/api/chat` 短路。

**Tech Stack:** FastAPI, Pydantic Settings, sentence-transformers, ChromaDB, pytest, Astro, Vitest。

**Spec:** `docs/superpowers/specs/2026-09-21-rag-v2-local-design.md`

## Global Constraints

- 本阶段只验证本地前后端，不修改 Vercel Preview、Production、Firewall 或线上环境变量。
- 默认模型为 `intfloat/multilingual-e5-small`；文档使用 `passage: `，查询使用 `query: `，并启用归一化向量。
- ChromaDB 使用 cosine distance，默认 collection 为 `wu_yu_knowledge_v2`，路径为 `backend/data/chroma`。
- ChromaDB 目录、模型缓存和真实 `.env` 不提交到公开仓库。
- `POST /api/chat` 请求和响应字段保持不变，`ChatResponse.mode` 继续为 `remote`。
- 现有词法检索是安全边界和 fallback；向量相似度不能绕过资料外拒答。
- 测试只保留个人项目所需的最小证据集。

---

### Task 1: Add vector settings and dependency boundary

**Files:** Modify `backend/requirements.txt`, `backend/app/config.py`, `backend/.env.example`, `.gitignore`; create `backend/tests/test_config.py`.

**Interfaces:** Consume existing `Settings`; produce validated `rag_retrieval`, `embedding_model`, `chroma_path`, `vector_collection`, `vector_top_k`, `vector_max_distance` and `embedding_timeout_seconds` fields.

- [ ] **Step 1: Write failing tests.** Assert `Settings(_env_file=None)` defaults to `vector`, `intfloat/multilingual-e5-small`, `data/chroma`, `wu_yu_knowledge_v2`, `4` and `0.096`. Assert `Settings(_env_file=None, rag_retrieval="bm25")` raises `ValidationError`.
- [ ] **Step 2: Run `cd backend && .venv/bin/python -m pytest tests/test_config.py -q`; confirm failure because the fields do not exist.**
- [ ] **Step 3: Add `chromadb>=1.5,<2` and `sentence-transformers>=6.1,<7`. Add `rag_retrieval: Literal["vector", "lexical", "hybrid"] = "vector"`, `embedding_model: str = "intfloat/multilingual-e5-small"`, `chroma_path: str = "data/chroma"`, `vector_collection: str = "wu_yu_knowledge_v2"`, `vector_top_k: int = Field(default=4, ge=1, le=8)`, `vector_max_distance: float = Field(default=0.096, gt=0)`, and `embedding_timeout_seconds: float = Field(default=30.0, gt=0)`. Document them in `.env.example` and ignore `backend/data/chroma/` and `backend/.model-cache/`.
- [ ] **Step 4: Run `cd backend && .venv/bin/python -m pytest tests/test_config.py -q`; confirm green. Commit with `git add backend/requirements.txt backend/app/config.py backend/.env.example backend/tests/test_config.py .gitignore && git commit -m "feat: configure local vector retrieval"`.**

### Task 2: Implement the local E5 provider

**Files:** Create `backend/app/embeddings.py` and `backend/tests/test_embeddings.py`.

**Interfaces:** Consume `Settings.embedding_model`; produce `LocalEmbeddingProvider.embed_documents(texts) -> list[list[float]]`, `embed_query(text) -> list[float]`, and `EmbeddingError`.

- [ ] **Step 1: Write failing tests.** Patch `app.embeddings.SentenceTransformer` with a fake model that records calls. Assert documents use `passage: `, queries use `query: `, and both calls pass `normalize_embeddings=True`. Assert model/encoding failures become `EmbeddingError("local embedding unavailable")` without raw provider text.
- [ ] **Step 2: Run `cd backend && .venv/bin/python -m pytest tests/test_embeddings.py -q`; confirm failure because `app.embeddings` does not exist.**
- [ ] **Step 3: Implement lazy `SentenceTransformer(model_name)` loading, per-provider model caching, `encode(..., normalize_embeddings=True)`, NumPy-like `.tolist()` conversion and stable exception mapping.**
- [ ] **Step 4: Run `cd backend && .venv/bin/python -m pytest tests/test_embeddings.py -q`; confirm green. Commit with `git add backend/app/embeddings.py backend/tests/test_embeddings.py && git commit -m "feat: add local e5 embedding provider"`.**

### Task 3: Add persistent ChromaDB and index command

**Files:** Create `backend/app/vector_store.py`, `backend/app/index_knowledge.py`, `backend/tests/test_vector_store.py` and `backend/tests/test_index_knowledge.py`.

**Interfaces:** Consume `KnowledgeChunk`, Task 2 embeddings and Task 1 settings; produce `ChromaVectorStore.rebuild(chunks, embeddings) -> int`, `ChromaVectorStore.query(query_embedding, chunks_by_id, top_k, max_distance) -> tuple[KnowledgeChunk, ...]`, and `build_index(settings) -> int`.

- [ ] **Step 1: Write failing fake-client tests.** Assert rebuild deletes/recreates the versioned collection, stores stable IDs, normalized embeddings and `source`/`heading` metadata; query maps IDs to chunks and filters distances above `max_distance`; repeated rebuilds keep one record per ID; `build_index()` loads knowledge, builds chunks, embeds content and returns the chunk count.
- [ ] **Step 2: Run `cd backend && .venv/bin/python -m pytest tests/test_vector_store.py tests/test_index_knowledge.py -q`; confirm failure because the modules do not exist.**
- [ ] **Step 3: Implement `chromadb.PersistentClient(path=resolved_path)` and `get_or_create_collection(name, metadata={"hnsw:space": "cosine"})`. Rebuild by deleting and recreating the versioned collection, then adding IDs, documents, embeddings and metadata. Resolve relative paths against the repository root; keep Chroma response parsing inside this module.**
- [ ] **Step 4: Implement `build_index(settings=None)` and the CLI `cd backend && .venv/bin/python -m app.index_knowledge`. Print only model name, chunk count and resolved path; never print source text, vectors, keys or provider errors.**
- [ ] **Step 5: Run the focused tests and `cd backend && .venv/bin/python -m app.index_knowledge`. Confirm the local directory is created, then commit with `git add backend/app/vector_store.py backend/app/index_knowledge.py backend/tests/test_vector_store.py backend/tests/test_index_knowledge.py && git commit -m "feat: add persistent chroma knowledge index"`. Do not stage `backend/data/chroma/`.**

### Task 4: Integrate vector retrieval and lexical fallback

**Files:** Modify `backend/app/retrieval.py`, `backend/app/main.py`, `backend/tests/test_retrieval.py`, `backend/tests/test_api.py`; create `backend/tests/test_vector_retrieval.py`.

**Interfaces:** Consume the Task 2 provider, Task 3 store, current `retrieve_chunks()` and `Settings`; produce `RetrievalResult(chunks, mode, fallback_used)` and `async retrieve_relevant_chunks(question, chunks, settings)`.

- [ ] **Step 1: Write failing orchestration tests.** Verify vector results return `mode="vector"`; an embedding/store exception returns lexical chunks with `mode="lexical"` and `fallback_used=True`; blocked requests return no chunks without vector calls; successful vector no-match does not call lexical fallback.
- [ ] **Step 2: Run `cd backend && .venv/bin/python -m pytest tests/test_vector_retrieval.py -q`; confirm failure because the result type and function do not exist.**
- [ ] **Step 3: Add `@dataclass(frozen=True) class RetrievalResult` with `chunks: tuple[KnowledgeChunk, ...]`, `mode: Literal["vector", "lexical", "none"]` and `fallback_used: bool`. Check the existing blocked-request predicate first, use lexical mode directly when configured, run local embedding/Chroma work in `asyncio.to_thread()`, and fall back only on vector component exceptions. Cache provider/store by model/path/collection.**
- [ ] **Step 4: Await the new function in `main.py`; preserve the response schema, fixed no-match answer, `mode="remote"`, 502/503 behavior and validation. Add only sanitized `retrieval_mode` and `fallback_used` log fields. Update API tests for vector context, no-match short circuit, fallback and log redaction.**
- [ ] **Step 5: Run `cd backend && .venv/bin/python -m pytest tests/test_config.py tests/test_embeddings.py tests/test_vector_store.py tests/test_index_knowledge.py tests/test_vector_retrieval.py tests/test_retrieval.py tests/test_api.py -q`; confirm green and commit with `git add backend/app/retrieval.py backend/app/main.py backend/tests/test_retrieval.py backend/tests/test_api.py backend/tests/test_vector_retrieval.py && git commit -m "feat: integrate vector retrieval with lexical fallback"`.**

### Task 5: Document and verify the local phase

**Files:** Modify `README.md` and `src/content/posts/online-preview-deployment.md`; create `docs/evals/rag-v2-local.md`.

**Interfaces:** Consume the local index command, settings and retrieval behavior; produce reproducible startup instructions and a sanitized local RAG V2 validation record.

- [ ] **Step 1: Document `cd backend && .venv/bin/pip install -r requirements.txt`, `cd backend && .venv/bin/python -m app.index_knowledge`, and `cd backend && .venv/bin/uvicorn app.main:app --reload --port 8000`. Explain that `backend/data/chroma/` is local-only, Embedding runs locally, and `OPENAI_*` is only for answer generation.**
- [ ] **Step 2: Run the acceptance set: `cd backend && .venv/bin/python -m app.index_knowledge`; `cd backend && .venv/bin/python -m pytest -q`; `npm test`; `npm run check`; `npm run build`; `git diff --check`.**
- [ ] **Step 3: Manually verify 8 local questions: 4 facts, 2 unsupported facts, 1 injection request and 1 vector-failure fallback. Record aggregate counts and retrieval modes only.**
- [ ] **Step 4: Write `docs/evals/rag-v2-local.md` with model, PersistentClient path policy, cosine/top-k/threshold settings, fallback behavior, aggregate results and limitations. Update the blog draft without presenting local-only ChromaDB as online production service.**
- [ ] **Step 5: Confirm Chroma data, model caches, `.env` files and generated artifacts are absent from the diff; commit with `git add README.md src/content/posts/online-preview-deployment.md docs/evals/rag-v2-local.md && git commit -m "docs: record local rag v2 validation"`.**

## Final Verification Checklist

- [ ] Index construction completes and repeated runs are idempotent.
- [ ] Vector retrieval returns verified sources for fact cases.
- [ ] Unsupported and blocked questions do not call the LLM without context.
- [ ] Vector failures fall back to lexical retrieval without raw exceptions.
- [ ] Backend tests, frontend tests, Astro check and static build pass.
- [ ] `git diff --check` passes.
- [ ] Preview, Production, knowledge source and public API contract are unchanged.
