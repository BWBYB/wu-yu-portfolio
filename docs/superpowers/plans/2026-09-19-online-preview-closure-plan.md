# Online Preview Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 0 托管成本约束下，把现有 Astro + FastAPI Version 0 Agent 部署为同一 Vercel 项目的可验证 Preview，并在满足时长、限流、密钥和回滚门槛后再决定是否提升 Production。

**Architecture:** Astro 继续静态构建，Vercel Python Function 通过一个薄入口导出已有 `backend/app/main.py` 的 FastAPI `app`。浏览器在 Preview/Production 通过相对地址 `/api/chat` 同域访问 Function；模型 Key 只存在服务端环境变量，资料文件通过 Function 文件打包配置显式包含。

**Tech Stack:** Astro 7, React 19, TypeScript, Vitest, FastAPI, Python 3.11+, OpenAI Python SDK Responses API, Vercel Python Runtime, Vercel CLI/Git Preview。

**Spec:** `docs/superpowers/specs/2026-09-19-online-preview-closure-design.md`

## Global Constraints

- 保持 Astro 静态页面与现有 `askKnowledgeBase()` 适配器，不复制业务逻辑。
- 线上公开路由为 `GET /api/health` 和 `POST /api/chat`；本地 `GET /health` 兼容行为不得被破坏。
- `OPENAI_API_KEY` 只存在 Vercel 服务端敏感变量，任何 `PUBLIC_` 变量都不得包含 Key。
- Preview 验收通过前不配置真实 Production 模型 Key，不提升 Production。
- 上游模型超时 < Vercel Function 最大时长 < 浏览器 75 秒请求上限；采用 Preview 实测值确认。
- 未知问题必须基于固定资料回答，不得推测；远程失败不得静默回退为演示回答。
- 不引入 LangChain、ChromaDB、embedding、登录、持久化会话、数据库或付费托管服务。
- 每完成一个阶段，都更新 `src/content/posts/online-preview-deployment.md`，只记录脱敏配置和验证证据。
- 不提交 `.env`、Vercel 拉取的本地环境文件、真实响应正文、完整供应商错误或任何 API Key。

---

### Task 1: 建立隔离分支并记录线上基线

**Files:**
- Create: `docs/superpowers/plans/2026-09-19-online-preview-closure-plan.md` (this plan)
- Modify: `src/content/posts/online-preview-deployment.md`
- Test: existing `npm test`, `npm run check`, `npm run build`, `backend/.venv/bin/python -m pytest`

**Interfaces:**
- Consumes: approved spec and current PR #2 commit containing Responses API support and 75-second browser timeout.
- Produces: clean implementation branch, recorded baseline test counts, and a blog section stating that deployment code has not yet changed.

- [ ] **Step 1: Create the implementation branch from the approved PR commit.**

  Run from the repository root after the current Git worktree approval is available:

  ```bash
  git fetch origin
  git switch -c codex/online-preview-closure origin/codex/heiyucode-responses-api
  ```

  If the branch already exists locally, switch to it and confirm it points to the PR #2 head. Do not create the branch from an older `main` commit.

- [ ] **Step 2: Confirm the baseline before touching deployment files.**

  ```bash
  npm test
  npm run check
  npm run build
  cd backend && .venv/bin/python -m pytest
  ```

  Expected: frontend `16/16` tests, backend `27/27` tests, Astro check with zero diagnostics, and a successful static build. Record the exact counts in the blog draft.

- [ ] **Step 3: Commit the documentation baseline.**

  ```bash
  git add docs/superpowers/plans/2026-09-19-online-preview-closure-plan.md src/content/posts/online-preview-deployment.md
  git commit -m "docs: plan online preview closure"
  ```

---

### Task 2: Verify Vercel Hobby capabilities before implementation

**Files:**
- Modify: `src/content/posts/online-preview-deployment.md`
- Test: Vercel project and deployment read-only commands

**Interfaces:**
- Consumes: linked Vercel project, current team plan, and official Vercel Function/Firewall documentation.
- Produces: a recorded go/no-go decision for Preview based on actual Function duration and free rate-limit availability.

- [ ] **Step 1: Inspect the linked project without changing it.**

  ```bash
  vercel project ls
  vercel project inspect wu-yu-portfolio --format json
  vercel env ls preview
  vercel env ls production
  ```

  Use the returned project rather than guessing an ID. Do not print environment values; only record variable names and whether the required environment is configured.

- [ ] **Step 2: Verify the current Function duration limit.**

  Read the current project plan and Vercel Function duration documentation, then record the maximum allowed duration. The implementation target is `maxDuration: 60` seconds only if the current Hobby project accepts that value; otherwise use the documented Hobby maximum and stop the Production path if it cannot safely contain a real request around 52 seconds.

- [ ] **Step 3: Verify free rate limiting.**

  ```bash
  vercel firewall rules list
  vercel firewall overview
  ```

  Confirm whether a free IP-based rule can protect `/api/chat` with a fixed window of 5 requests per 60 seconds. If the rule requires a paid plan, record `Preview-only` as the Production decision and do not add an in-process Python counter.

- [ ] **Step 4: Update the blog outline with the capability decision.**

  Record the actual duration limit, whether free rate limiting is available, and the resulting decision. Do not record account IDs, tokens, or environment values.

- [ ] **Step 5: Commit the capability decision.**

  ```bash
  git add src/content/posts/online-preview-deployment.md
  git commit -m "docs: record preview platform capability decision"
  ```

---

### Task 3: Add the thin Vercel FastAPI entrypoint

**Files:**
- Create: `api/index.py`
- Create: `vercel.json`
- Create: `tests/test_deploy_entrypoint.py`
- Modify: `backend/app/knowledge.py` only if the packaging test proves its repository-root lookup is not valid in the Vercel bundle

**Interfaces:**
- Consumes: existing `backend/app/main.py:app`, existing `knowledge/profile.md`, and existing `knowledge/spmtrack.md`.
- Produces: an importable `api.index.app` that is the exact existing FastAPI application; no duplicate routes or prompt logic.

- [ ] **Step 1: Write the failing entrypoint test.**

  Create a test that imports the deployment entrypoint and asserts that it exports the existing FastAPI title and both expected routes:

  ```python
  from fastapi.routing import APIRoute

  from api.index import app


  def test_vercel_entrypoint_exports_existing_fastapi_routes() -> None:
      paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
      assert app.title == "Wu Yu Personal Knowledge Agent"
      assert "/health" in paths
      assert "/api/chat" in paths
  ```

  The test must fail before `api/index.py` exists.

- [ ] **Step 2: Run the focused test and confirm the expected failure.**

  ```bash
  pytest tests/test_deploy_entrypoint.py -q
  ```

  Expected: import failure for the missing deployment entrypoint, not a dependency or syntax error.

- [ ] **Step 3: Implement the minimal entrypoint.**

  `api/index.py` must add the repository `backend` directory to `sys.path` using an absolute path derived from `__file__`, then import and re-export `app` from `app.main`. It must not instantiate a second FastAPI app.

- [ ] **Step 4: Add the Vercel function configuration.**

  `vercel.json` must configure the Python entrypoint with the verified duration and explicitly include `backend/**` and `knowledge/**` in the deployment bundle. Use the exact accepted Vercel property names from the current documentation; do not silently rely on local filesystem behavior.

- [ ] **Step 5: Run the focused test and packaging checks.**

  ```bash
  pytest tests/test_deploy_entrypoint.py -q
  npm run check
  npm run build
  ```

  Expected: entrypoint test passes, Astro diagnostics remain zero, and the static build succeeds.

- [ ] **Step 6: Commit the deployment adapter.**

  ```bash
  git add api/index.py vercel.json tests/test_deploy_entrypoint.py
  git commit -m "feat: expose fastapi app to vercel"
  ```

---

### Task 4: Switch the production browser contract to same-origin Preview requests

**Files:**
- Modify: `src/lib/agent/client.ts`
- Modify: `tests/agent/client.test.ts`
- Modify: `.env.example`
- Modify: `README.md`

**Interfaces:**
- Consumes: `PUBLIC_AGENT_API_URL` and existing `askKnowledgeBase(question, history)`.
- Produces: `/api/chat` when `PUBLIC_AGENT_API_URL=/`, demo mode when the variable is absent, and the existing remote response schema.

- [ ] **Step 1: Write the failing same-origin test.**

  Add a test fixture with `PUBLIC_AGENT_API_URL=/` and assert that the request URL is exactly `/api/chat`, with no duplicated slash and no absolute local host.

- [ ] **Step 2: Run the focused test and confirm it fails for the current implementation.**

  ```bash
  npm test -- tests/agent/client.test.ts
  ```

  Expected: failure showing that the current environment fixture still targets the old absolute URL or does not normalize `/` as the intended production contract.

- [ ] **Step 3: Implement the smallest URL normalization change.**

  Keep the current explicit demo/remote switch. Normalize a root value of `/` to an empty prefix before appending `/api/chat`; preserve absolute local URLs for development and preserve the existing request body, timeout, response validation, and error behavior.

- [ ] **Step 4: Update the public configuration documentation.**

  Change the Preview/Production example to `PUBLIC_AGENT_API_URL=/`. Keep the local example as `PUBLIC_AGENT_API_URL=http://localhost:8000`. Explain that an unset value intentionally stays in demo mode.

- [ ] **Step 5: Run frontend tests and static checks.**

  ```bash
  npm test
  npm run check
  npm run build
  ```

  Expected: `16/16` tests or the updated total pass, zero Astro diagnostics, successful build, and no changed remote response contract.

- [ ] **Step 6: Commit the same-origin contract.**

  ```bash
  git add src/lib/agent/client.ts tests/agent/client.test.ts .env.example README.md
  git commit -m "feat: use same-origin agent api in vercel"
  ```

---

### Task 5: Add safe request metadata logging without recording content

**Files:**
- Create: `backend/app/observability.py`
- Modify: `backend/app/main.py`
- Create or modify: `backend/tests/test_observability.py`
- Modify: `src/content/posts/online-preview-deployment.md`

**Interfaces:**
- Consumes: FastAPI request/response lifecycle and current stable error categories.
- Produces: one structured log record per API request containing request ID, route, status class, duration, message length, history count, source count when available, and sanitized error category; no question or answer body.

- [ ] **Step 1: Write failing log-capture tests.**

  Use `caplog` and the FastAPI test client to assert that a successful health or chat request logs the route and duration, while the captured log text does not contain a known question string or known answer string. Add a second test asserting that a provider failure logs `provider` or `timeout` as a category without the original provider message.

- [ ] **Step 2: Run the focused backend tests and confirm they fail.**

  ```bash
  cd backend
  .venv/bin/python -m pytest tests/test_observability.py -q
  ```

  Expected: the new log assertions fail because the application has no structured request metadata middleware.

- [ ] **Step 3: Implement a narrow middleware and category helper.**

  Generate a request ID per request, measure monotonic elapsed time, log method/path/status/duration, and attach only safe numeric metadata. Catch and classify known public errors; never log exception text from the provider. Keep health and chat behavior unchanged.

- [ ] **Step 4: Run backend tests and inspect a local log line.**

  ```bash
  .venv/bin/python -m pytest
  ```

  Expected: all existing backend tests plus the new tests pass, and a local request prints no secret or message body.

- [ ] **Step 5: Update and commit the observability stage.**

  Add the log fields and redaction result to the blog outline, then run:

  ```bash
  git add backend/app/observability.py backend/app/main.py backend/tests/test_observability.py src/content/posts/online-preview-deployment.md
  git commit -m "feat: add redacted agent request telemetry"
  ```

---

### Task 6: Deploy a private Preview and verify the public API

**Files:**
- Modify: `src/content/posts/online-preview-deployment.md`
- Test: Vercel Preview deployment, public `curl`, and Vercel Runtime Logs

**Interfaces:**
- Consumes: committed deployment adapter, same-origin frontend contract, Preview environment variables, and a private branch deployment.
- Produces: a concrete Preview URL, health/chat evidence, timing measurements, and a go/no-go result for Production.

- [ ] **Step 1: Configure only Preview environment variables.**

  Add the following names to the target Preview environment using the Vercel dashboard or CLI. Enter the real Key interactively; never put it in shell history or a tracked file:

  ```text
  OPENAI_API_KEY
  OPENAI_BASE_URL=https://www.heiyucode.com
  OPENAI_MODEL=gpt-5.5
  OPENAI_API_MODE=responses
  LLM_TIMEOUT_SECONDS=55
  MAX_HISTORY=8
  MAX_MESSAGE_CHARS=2000
  PUBLIC_AGENT_API_URL=/
  ```

  Set `LLM_TIMEOUT_SECONDS=55` only when the verified Function maximum is at least 60 seconds, leaving time for response serialization. If the platform maximum is lower than the required model latency, stop at Preview-only and record the reason.

- [ ] **Step 2: Push the implementation branch and wait for the Vercel Preview.**

  ```bash
  git push -u origin codex/online-preview-closure
  gh pr create --base main --head codex/online-preview-closure --title "feat: deploy agent preview on vercel" --body-file /tmp/online-preview-pr.md
  ```

  The PR body must list the environment names without values, automated test results, and the Preview acceptance checklist. Do not paste a Key or model response into the PR.

- [ ] **Step 3: Check Preview health and timing.**

  Use the actual Preview URL shown by Vercel:

  ```bash
  curl -i --max-time 20 "$PREVIEW_URL/api/health"
  curl -sS -w '\nHTTP_STATUS=%{http_code} TOTAL=%{time_total}s\n' --max-time 75 \
    -X POST "$PREVIEW_URL/api/chat" \
    -H 'Content-Type: application/json' \
    -d '{"message":"请介绍一下吴禹的技术栈，并说明资料来源。","history":[]}'
  ```

  Set `PREVIEW_URL` in the current shell to the actual Vercel URL before running the commands; do not commit it to the repository. Expected health response: HTTP 200 and `{"status":"ok"}`. Expected chat response: HTTP 200, non-empty `answer`, `sources` containing `个人资料` and `SPMTrack 项目资料`, and `mode` equal to `remote`.

- [ ] **Step 4: Run five real questions and record timing only.**

  Use five questions covering identity, SPMTrack responsibilities, technical choices, learning direction, and an unavailable fact. Record request duration and HTTP status in the blog, not the response body. A single request exceeding the Function/browser budget is a Preview failure.

- [ ] **Step 5: Inspect runtime and client errors.**

  ```bash
  vercel logs --environment preview --level error --since 15m
  ```

  Use Playwright against the actual Preview URL to assert remote mode, two sources, loading state completion, retry after a forced failure, and no console errors. Save only redacted screenshots.

- [ ] **Step 6: Run the secret scan.**

  ```bash
  rg -n "OPENAI_API_KEY|sk-[A-Za-z0-9]|heiyucode.*key" dist .vercel 2>/dev/null || true
  ```

  Expected: no API key or secret value in client build output or deployment metadata. A variable name alone is not evidence of a leaked value; inspect any match before proceeding.

- [ ] **Step 7: Update and commit the Preview evidence.**

  Record URL classification (private Preview), timing summary, health/chat results, browser result, log result, and secret-scan result. Commit only the redacted evidence:

  ```bash
  git add src/content/posts/online-preview-deployment.md
  git commit -m "docs: record agent preview verification"
  ```

---

### Task 7: Configure the free abuse boundary and decide Production eligibility

**Files:**
- Modify: `src/content/posts/online-preview-deployment.md`
- Test: Vercel Firewall rule behavior and API response status

**Interfaces:**
- Consumes: verified Preview route `/api/chat` and the capability result from Task 2.
- Produces: either an active free platform-level rate limit or an explicit `Preview-only` decision; never a non-shared Python counter.

- [ ] **Step 1: Create a disabled candidate rule before activation.**

  If Task 2 confirmed free support, create a disabled rule for path prefix `/api/chat` with IP key, fixed window, 5 requests per 60 seconds, and a 429/deny action. Review the generated rule before publishing.

- [ ] **Step 2: Enable the rule and verify the boundary.**

  Publish the rule only to the Preview/target project as supported by the current Vercel plan. Send six lightweight invalid requests and verify that the sixth is rejected before model invocation. Do not use real prompts for this test.

- [ ] **Step 3: If free support is unavailable, stop the Production path.**

  Record `Preview-only: free cross-instance rate limiting is unavailable` in the blog. Do not substitute an in-memory dictionary, do not expose the Preview URL publicly, and do not configure a Production model Key.

- [ ] **Step 4: Set a provider-side usage ceiling.**

  In the model provider account, configure the smallest available spend/usage ceiling compatible with testing. Record only that the ceiling is enabled, never its credential or private account details.

- [ ] **Step 5: Commit the security decision.**

  ```bash
  git add src/content/posts/online-preview-deployment.md
  git commit -m "docs: record preview abuse protection decision"
  ```

---

### Task 8: Production promotion only after explicit approval

**Files:**
- Modify: `src/content/posts/online-preview-deployment.md`
- Modify: site copy files identified by Preview review, only if they still claim the Agent is local-only
- Test: Production health, chat, browser, logs, and rollback

**Interfaces:**
- Consumes: all Preview evidence and the user's explicit Production approval.
- Produces: either a verified Production deployment or a documented decision to keep the Agent Preview-only.

- [ ] **Step 1: Review the Production gate checklist.**

  Do not proceed unless all are true: Preview API/browser tests pass; Function duration covers real latency; rate limiting is active or the Agent remains Preview-only; Key is server-only; stale local-demo copy is corrected; Version 0 is labeled fixed-corpus Q&A; rollback target is known.

- [ ] **Step 2: Request explicit Production approval.**

  Present the Preview URL, timing summary, cost/rate-limit result, and rollback target. Do not promote based on a general earlier architecture approval.

- [ ] **Step 3: Configure Production variables only after approval.**

  Add the same server-side model variables to Production and set `PUBLIC_AGENT_API_URL=/`. Never copy the Key into Git or a client-visible variable.

- [ ] **Step 4: Promote the verified Preview deployment.**

  Use the exact ready deployment returned by Vercel rather than creating a new unverified build:

  ```bash
  vercel promote "$DEPLOYMENT_URL" --yes
  vercel promote status
  ```

- [ ] **Step 5: Run Production smoke tests and rollback if needed.**

  ```bash
  curl -i --max-time 20 "$PRODUCTION_URL/api/health"
  curl -sS -w '\nHTTP_STATUS=%{http_code} TOTAL=%{time_total}s\n' --max-time 75 \
    -X POST "$PRODUCTION_URL/api/chat" \
    -H 'Content-Type: application/json' \
    -d '{"message":"你在 SPMTrack 项目中负责什么？","history":[]}'
  vercel logs --environment production --level error --since 10m
  ```

  If health, chat, browser, or logs fail, promote the last verified deployment back or use the Vercel rollback control; record the failure before changing code.

- [ ] **Step 6: Complete the Production blog section and commit.**

  Record the final status as `Production` or `Preview-only`, the smoke-test result, observed latency range, rate-limit result, and rollback evidence without response bodies or secrets.

  ```bash
  git add src/content/posts/online-preview-deployment.md
  git commit -m "docs: record agent production decision"
  ```

---

## Final Verification Checklist

- [ ] `npm test` passes with zero failures.
- [ ] `npm run check` reports zero errors, warnings, and hints.
- [ ] `npm run build` succeeds when run alone, not concurrently with Astro content sync.
- [ ] `backend/.venv/bin/python -m pytest` passes with zero failures.
- [ ] `api/index.py` exports the existing FastAPI `app` and does not duplicate business logic.
- [ ] Vercel bundle contains both knowledge Markdown files.
- [ ] Preview `/api/health` returns 200 without a model Key.
- [ ] Preview `/api/chat` returns 200, `mode=remote`, and two sources.
- [ ] Five real Preview questions complete within the measured budget.
- [ ] Browser shows remote response, sources, loading completion, retry behavior, and no console errors.
- [ ] No Key appears in static assets, logs, screenshots, or commits.
- [ ] A free cross-instance rate-limit decision is recorded.
- [ ] Production is promoted only after explicit user approval, or the blog states why the Agent remains Preview-only.

