# Agent Book 前三章 RAG 稳定版实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 导入 Agent Book 第三章，验证前三章本地 RAG，并生成可继续扩写的中文博客草稿。

**Architecture:** Dify 继续作为本地验证编排器，三章 Markdown 共用一个向量知识库；博客只记录可复现的资料版本、切分参数、召回证据和平台方向，不把 Dify 验证包装成自研生产系统。

**Tech Stack:** Dify（本地）、本地 multilingual-e5-small Embedding 适配服务、Astro Content Collections、Markdown。

**Spec:** `docs/superpowers/specs/2026-10-07-agent-book-rag-stable-design.md`

## Global Constraints

- 只使用 Agent Book 固定 `main` 提交 `dbc046eb896ac4e39aa19c7774c8bf49583b89a6` 的前三章。
- Dify 切分配置保持最大长度 1024、重叠 50、连续空白清洗和高质量向量索引。
- 本阶段不统计 token 成本，不发布 Dify，不部署网站，不修改 Vercel/OpenShip。
- 不修改既有网站页面组件和既有个人 RAG V2。

### Task 1: 导入并验证第三章

**Files:**
- External input: `/Users/Admin/Documents/ChatGPT/agent-book/book/chapter3.md`
- External system: local Dify dataset `8201e1f0-65a0-4232-8c5e-e70c19607d0b`

**Interfaces:**
- Consumes: Dify knowledge base containing `chapter1.md` and `chapter2.md`.
- Produces: usable `chapter3.md` document and recall evidence for chapters 1-3.

- [ ] **Step 1: Verify source identity**

Run:

```bash
git -C /Users/Admin/Documents/ChatGPT/agent-book rev-parse HEAD
shasum -a 256 /Users/Admin/Documents/ChatGPT/agent-book/book/chapter3.md
```

Expected: commit `dbc046eb896ac4e39aa19c7774c8bf49583b89a6` and SHA-256 `aef4bd529d906b7cd1fa32ab25e55ef88254a9220d769bebead423b1c754d6bc`.

- [ ] **Step 2: Upload and process the document in Dify**

Upload `chapter3.md` to dataset `8201e1f0-65a0-4232-8c5e-e70c19607d0b`, keep the existing chunking and vector settings, and wait for the UI status `可用`.

- [ ] **Step 3: Run six chapter-scoped recall checks**

Use two questions per chapter and record the visible result:

```text
第1章：什么是 Agent？Agent 和 Chatbot 有什么区别？
第2章：上下文工程为什么重要？模型 API 的消息有哪些角色？
第3章：用户记忆和知识库有什么区别？RAG 是如何增强知识库问答的？
```

For each query record the expected chapter, returned source document, number of returned chunks, and highest visible score. Do not call the score an accuracy percentage.

- [ ] **Step 4: Run one cross-chapter and one out-of-scope check**

Use `Agent 如何同时利用上下文和长期知识？` as a cross-chapter question and `吴禹在 SPMTrack 项目中负责什么？` as an out-of-scope question. Record whether the answer cites the correct chapter scope or refuses.

### Task 2: Write the blog draft

**Files:**
- Create: `src/content/posts/agent-book-rag-validation.md`

**Interfaces:**
- Consumes: Task 1 source hashes, Dify settings, recall evidence, and Preview responses.
- Produces: Astro-valid Markdown post with `status: organizing`.

- [ ] **Step 1: Add frontmatter matching the existing post schema**

Use `title`, `slug`, `date`, `status`, `summary`, and `tags`; set `status: organizing` and a stable slug `agent-book-rag-validation`.

- [ ] **Step 2: Write evidence-first sections**

Include: goal and scope, source version, local architecture, chunking configuration, retrieval table, Preview examples, failure boundaries, token-cost placeholder, and the learning-material platform evaluation.

- [ ] **Step 3: Keep claims bounded**

State that Dify is a local validation tool, that the current flow is RAG rather than a self-built LangGraph Agent, and that platform comparisons are recommendations rather than completed deployments.

### Task 3: Validate the blog artifact

**Files:**
- Test: `src/content/posts/agent-book-rag-validation.md`
- Inspect: `src/content.config.ts`

**Interfaces:**
- Consumes: Task 2 Markdown file.
- Produces: passing Astro content/build validation without changing application code.

- [ ] **Step 1: Run the repository checks relevant to content**

Run:

```bash
npm run check
```

Expected: Astro content collection validation passes and the new post frontmatter is accepted.

- [ ] **Step 2: Inspect the final diff**

Run:

```bash
git diff -- src/content/posts/agent-book-rag-validation.md
git status --short
```

Expected: only the new blog file is part of this task; pre-existing untracked files remain untouched.
