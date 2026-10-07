# Preview Content and Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在保持 Vercel Preview、零新增托管成本和不调用 Production 的前提下，把 Version 0 固定资料问答整理成可维护、可离线评测的 Agent 基线。

**Architecture:** 保留现有 Astro 前端、FastAPI `/api/chat` 和服务端密钥边界。先把资料源、事实边界和验收问题固定下来，再决定是否引入轻量检索；本阶段不引入 LangChain、ChromaDB、embedding 或持久化会话。

**Tech Stack:** Markdown knowledge corpus, FastAPI, pytest, TypeScript/Astro, Vercel Preview。

**Spec:** `docs/superpowers/specs/2026-09-19-online-preview-closure-design.md`

## Global Constraints

- Preview 保持当前部署，不修改 Production 环境或 Production 密钥。
- 未经用户再次批准，不发起新的远程模型请求。
- 资料只使用简历、SPMTrack 仓库和用户审核后的项目总结；未知事实必须返回未知。
- 不把当前固定上下文问答描述为完整 RAG 或 Agentic RAG。
- 不提交任何 API Key、真实 `.env`、完整模型回答或供应商错误正文。
- 每完成一个阶段，更新 `src/content/posts/online-preview-deployment.md` 的脱敏记录。

---

### Task 1: 固定资料来源与事实边界

**Files:**
- Modify: `knowledge/profile.md`
- Modify: `knowledge/spmtrack.md`
- Create: `docs/agent/source-boundary-v0.md`

**Interfaces:**
- Consumes: 当前已验证的个人资料和 SPMTrack 资料。
- Produces: 两份带来源说明的权威 Markdown，以及一份列明可回答、不可回答和待补充信息的边界文档。

- [ ] **Step 1: 对照现有资料建立事实清单。**

  必须覆盖以下已验证事实：教育背景、目标方向、React/TypeScript/FastAPI/Spring Boot/Docker 技术栈、SPMTrack 的四层架构、浏览器工作流、支持的跟踪模式和吴禹的职责边界。

- [ ] **Step 2: 标记不可回答问题。**

  在 `docs/agent/source-boundary-v0.md` 中明确列出家庭成员、薪资、未提供的实习经历、实时招聘信息、未提供的成绩和隐私信息；这些问题不能通过推测回答。

- [ ] **Step 3: 检查每条资料都有来源标签。**

  `profile.md` 的来源为简历/个人资料，`spmtrack.md` 的来源为 SPMTrack 仓库和已确认项目描述；不把模型生成的未审核文本直接当作事实。

- [ ] **Step 4: 运行现有资料测试。**

  ```bash
  cd backend
  .venv/bin/python -m pytest tests/test_knowledge.py -q
  ```

  Expected: 现有知识加载和 prompt grounding 测试全部通过。

- [ ] **Step 5: Commit。**

  ```bash
  git add knowledge/profile.md knowledge/spmtrack.md docs/agent/source-boundary-v0.md
  git commit -m "docs: define version zero knowledge boundaries"
  ```

### Task 2: 建立不调用模型的离线评测集

**Files:**
- Create: `docs/agent/eval-v0.md`
- Create: `backend/tests/fixtures/eval_v0.json`
- Create: `backend/tests/test_eval_fixture.py`

**Interfaces:**
- Consumes: `knowledge/profile.md`, `knowledge/spmtrack.md` and `source-boundary-v0.md`。
- Produces: 可重复的事实问题、未知问题和提示词注入边界用例；fixture 只描述预期来源和边界类别，不保存真实模型回答。

- [ ] **Step 1: 写入 14 条固定用例。**

  `eval_v0.json` 必须包含 6 条事实题、4 条未知题和 4 条安全边界题。事实题至少覆盖“技术栈”“SPMTrack 是什么”“系统四层架构”“浏览器工作流”“支持的跟踪模式”“吴禹负责什么”；未知题覆盖家庭成员、薪资、实时信息和未提供经历；安全题覆盖索要系统提示词、索要 API Key、要求忽略资料和要求编造事实。

- [ ] **Step 2: 写 fixture schema 测试。**

  `test_eval_fixture.py` 验证每条记录有 `id`、`category`、`question` 和 `expected_sources`，类别只允许 `fact`、`unknown`、`boundary`，且 ID 唯一。

- [ ] **Step 3: 运行离线测试。**

  ```bash
  cd backend
  .venv/bin/python -m pytest tests/test_eval_fixture.py tests/test_knowledge.py -q
  ```

  Expected: 测试不读取模型 Key、不发起网络请求，并验证 fixture 与当前资料源存在。

- [ ] **Step 4: Commit。**

  ```bash
  git add docs/agent/eval-v0.md backend/tests/fixtures/eval_v0.json backend/tests/test_eval_fixture.py
  git commit -m "test: add offline agent evaluation fixture"
  ```

### Task 3: 评估当前 Version 0 的可维护性

**Files:**
- Modify: `backend/tests/test_knowledge.py`
- Modify: `backend/tests/test_api.py`
- Modify: `src/content/posts/online-preview-deployment.md`

**Interfaces:**
- Consumes: Task 1 的边界文档和 Task 2 的 fixture。
- Produces: 不调用模型的 grounding、输入限制、稳定错误映射和来源标签回归测试，以及一份当前 Preview 基线记录。

- [ ] **Step 1: 补充无网络 API 回归测试。**

  使用 monkeypatch 替换 `generate_answer`，验证空消息、超长消息、超长 history 在模型调用前被拒绝，异常只返回稳定的 502/503 文案，响应包含 `sources` 和 `mode`。

- [ ] **Step 2: 运行完整本地测试。**

  ```bash
  cd backend
  .venv/bin/python -m pytest -q
  cd ..
  npm test
  npm run check
  npm run build
  ```

- [ ] **Step 3: 更新部署博客草稿。**

  记录 Preview 已通过的 `/api/health`、正常事实问答、未知问题、提示词注入和输入校验；只记录状态码、耗时区间、检索数量和错误分类，不记录完整回答或密钥。

- [ ] **Step 4: Commit。**

  ```bash
  git add backend/tests src/content/posts/online-preview-deployment.md
  git commit -m "test: lock preview agent baseline"
  ```

### Task 4: 评估是否进入轻量检索 V1

**Files:**
- Modify: `docs/agent/eval-v0.md`
- Create only after approval: `backend/app/retrieval.py`, `backend/tests/test_retrieval.py`

**Interfaces:**
- Consumes: 已通过的离线评测集和用户审核后的新增 Markdown 资料。
- Produces: 一个可比较的 go/no-go 决策；只有在固定上下文无法维持可接受的资料规模或来源准确性时，才实现轻量检索。

- [ ] **Step 1: 先用现有 Version 0 记录基线。**

  以 14 条 fixture 为评估范围，记录资料覆盖和边界行为；本步骤不调用远程模型。

- [ ] **Step 2: 设定升级门槛。**

  只有当资料数量增长导致 prompt 过长、来源无法稳定对应，或新增项目文档超过当前固定上下文可维护范围时，才进入 retrieval V1；否则保留简单架构。

- [ ] **Step 3: 在用户批准后选择实现方向。**

  优先考虑可解释的 Markdown 分段和关键词召回，再评估 ChromaDB/embedding；不因为学习路线而提前引入多 Agent 或复杂编排。

## 验收标准

- [ ] Preview 继续保持 `READY`，Production 没有被修改。
- [ ] 资料来源和不可回答边界有明确文档。
- [ ] 离线 fixture 测试无需 API Key 且不产生网络请求。
- [ ] 后端、前端、Astro check 和 build 全部通过。
- [ ] 未完成资料审核前，不把新内容部署为事实或发起额外线上模型请求。
