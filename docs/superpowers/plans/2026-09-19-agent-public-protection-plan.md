# Agent Public Protection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为个人知识库 Agent 增加可辨识的 429 前端状态，并通过分阶段 Vercel Firewall 规则验证 Preview 的基础 IP 限流。

**Architecture:** 浏览器保留远程响应的 HTTP status，ChatPanel 将 429 映射为专用提示；Vercel Firewall 在 `POST /api/chat` 进入 FastAPI 前按 IP 固定窗口计数。规则先以超限 `log` 发布，再增加 `environment=preview` 并执行 429；每次发布都由用户亲自在终端确认。

**Tech Stack:** Astro 7、React 19、TypeScript 6、Vitest、Testing Library、FastAPI、pytest、Vercel CLI 59、Vercel Firewall。

**Spec:** `docs/superpowers/specs/2026-09-19-agent-public-protection-design.md`

## Global Constraints

- 不扩充 `knowledge/` 中的简历、项目或博客资料。
- 不引入 Redis、Upstash、LangChain、ChromaDB、Embedding 或新的运行时依赖。
- Firewall 规则只匹配 `POST /api/chat`；不得影响 `/api/health`、静态页面或其他方法。
- 计数使用 `fixed_window`、60 秒、10 次、key 为 IP。
- 阶段 1 的超限动作必须是 `log`；阶段 2 必须增加 `environment=preview` 后才能改为 429。
- 任何 Firewall 草稿在发布前都必须执行 `rules inspect` 和 `firewall diff`。
- `vercel firewall publish` 必须由用户亲自在终端运行；执行者不得代替用户发布。
- 突发验收只能使用检索为空的问题，确保 FastAPI 不调用模型。
- 不启用 Attack Mode、Bot Protection、OWASP、IP Bypass、IP Block 或宽泛 User-Agent 规则。
- 不配置 Production 模型 Key，不提升 Production，不移除 Preview 环境条件。
- 如果 Hobby 套餐拒绝创建或发布频率规则，停止 Firewall 实施并记录为 Preview-only；不得自动接入共享存储。

---

### Task 1: Preserve remote HTTP status in the Agent client

**Files:**
- Modify: `src/lib/agent/client.ts`
- Test: `tests/agent/client.test.ts`

**Interfaces:**
- Produces: `AgentRequestError extends Error` with `readonly status: number`.
- Preserves: `askKnowledgeBase(question: string, history: AgentMessage[]): Promise<AgentResponse>`.
- The error message keeps the numeric HTTP status, for example `Remote agent request failed with status 503`, so existing status assertions continue to work.

- [ ] **Step 1: Add a failing 429 status test**

Change the import in `tests/agent/client.test.ts` to:

```ts
import { AgentRequestError, askKnowledgeBase } from '@/lib/agent/client';
```

Add this test immediately after `rejects non-2xx responses`:

```ts
it('preserves the status of a rate-limited response', async () => {
	vi.mocked(fetch).mockResolvedValue(new Response('rate limited', { status: 429 }));

	try {
		await askKnowledgeBase('问题', []);
		expect.fail('expected the request to reject');
	} catch (error) {
		expect(error).toBeInstanceOf(AgentRequestError);
		expect(error).toMatchObject({ status: 429 });
	}
});
```

- [ ] **Step 2: Run the focused test and confirm RED**

Run:

```bash
npm test -- --run tests/agent/client.test.ts
```

Expected: TypeScript/module failure because `AgentRequestError` is not exported.

- [ ] **Step 3: Implement the minimum typed remote error**

In `src/lib/agent/client.ts`, add above `isValidRemoteResponse`:

```ts
export class AgentRequestError extends Error {
	constructor(readonly status: number) {
		super(`Remote agent request failed with status ${status}`);
		this.name = 'AgentRequestError';
	}
}
```

Replace the existing non-2xx throw with:

```ts
if (!response.ok) {
	throw new AgentRequestError(response.status);
}
```

Do not parse or expose the non-2xx response body.

- [ ] **Step 4: Run the focused client tests and confirm GREEN**

Run:

```bash
npm test -- --run tests/agent/client.test.ts
```

Expected: all client tests pass, including the existing 503 assertion and the new 429 status assertion.

- [ ] **Step 5: Commit the client error boundary**

```bash
git add src/lib/agent/client.ts tests/agent/client.test.ts
git commit -m "feat: preserve agent response status"
```

---

### Task 2: Show a dedicated rate-limit state in ChatPanel

**Files:**
- Modify: `src/components/ChatPanel.tsx`
- Test: `tests/components/ChatPanel.test.tsx`

**Interfaces:**
- Consumes: `AgentRequestError` from `src/lib/agent/client.ts`.
- 429 copy: `请求有点频繁，请稍后再试。`
- Other failure copy remains: `这次回答没有生成成功，请重试。`
- A 429 error does not set `failedQuestion`, so the immediate retry button is absent.

- [ ] **Step 1: Preserve the real error class in the module mock**

Replace the current `vi.mock('@/lib/agent/client', ...)` block in `tests/components/ChatPanel.test.tsx` with:

```ts
vi.mock('@/lib/agent/client', async (importOriginal) => {
	const actual = await importOriginal<typeof import('@/lib/agent/client')>();
	return {
		...actual,
		askKnowledgeBase: vi.fn(),
	};
});
```

Change the import to:

```ts
import { AgentRequestError, askKnowledgeBase } from '@/lib/agent/client';
```

- [ ] **Step 2: Add a failing component test for 429**

Add after `shows a recoverable failure state`:

```ts
it('shows a dedicated rate-limit message without an immediate retry', async () => {
	const user = userEvent.setup();
	mockedAsk.mockRejectedValueOnce(new AgentRequestError(429));
	render(<ChatPanel recommendedPrompts={['你是谁？']} />);

	await user.click(screen.getByRole('button', { name: /你是谁/ }));

	expect(await screen.findByRole('alert')).toHaveTextContent('请求有点频繁，请稍后再试。');
	expect(screen.queryByRole('button', { name: /重试/ })).not.toBeInTheDocument();
	expect(screen.getByRole('textbox', { name: /向我的知识库提问/ })).toBeEnabled();
});
```

- [ ] **Step 3: Run the focused component test and confirm RED**

Run:

```bash
npm test -- --run tests/components/ChatPanel.test.tsx
```

Expected: the component displays the generic message and a retry button.

- [ ] **Step 4: Implement the 429 branch**

Change the production import in `src/components/ChatPanel.tsx` to:

```ts
import { AgentRequestError, askKnowledgeBase } from '@/lib/agent/client';
```

Replace the current `catch` body with:

```ts
} catch (error) {
	if (conversationVersion.current !== requestVersion) return;
	if (error instanceof AgentRequestError && error.status === 429) {
		setError('请求有点频繁，请稍后再试。');
		setFailedQuestion(null);
	} else {
		setError('这次回答没有生成成功，请重试。');
		setFailedQuestion(trimmed);
	}
} finally {
```

Do not add countdown state or inspect a non-JSON Firewall body.

- [ ] **Step 5: Run focused frontend tests and confirm GREEN**

Run:

```bash
npm test -- --run tests/components/ChatPanel.test.tsx tests/agent/client.test.ts
```

Expected: both test files pass; the ordinary failure test still proves retry behavior.

- [ ] **Step 6: Commit the UI behavior**

```bash
git add src/components/ChatPanel.tsx tests/components/ChatPanel.test.tsx
git commit -m "feat: explain agent rate limits"
```

---

### Task 3: Verify locally and deploy the frontend behavior to Preview

**Files:**
- No source changes expected.

**Interfaces:**
- Consumes: the two frontend commits from Tasks 1 and 2.
- Produces: one Ready Vercel Preview URL whose commit SHA matches the branch HEAD.

- [ ] **Step 1: Run the complete local verification suite**

Run from the repository worktree:

```bash
PYTHONPATH=backend /Users/Admin/Documents/ChatGPT/个人网站/backend/.venv/bin/python -m pytest backend/tests tests/test_deploy_entrypoint.py -q
npm test -- --run
npm run check
npm run build
git diff --check
```

Expected:

- Backend and deployment tests have zero failures.
- Frontend tests have zero failures and include the new 429 cases.
- Astro check reports zero errors, warnings, and hints.
- Astro build produces 5 pages.
- `git diff --check` is empty.

- [ ] **Step 2: Push to the existing Preview branch**

```bash
git push origin HEAD:codex/online-preview-closure
```

This is a non-Production branch push. Do not use `vercel --prod`, `vercel promote`, or the Production alias.

- [ ] **Step 3: Resolve and inspect the new Preview**

Run:

```bash
vercel ls --limit 5
```

Set `AGENT_PREVIEW_URL` to the newest `wu-yu-portfolio` Preview URL created by this push, then run:

```bash
vercel inspect "$AGENT_PREVIEW_URL" --wait
vercel curl "$AGENT_PREVIEW_URL/api/health"
```

Expected: deployment status `Ready`; health returns `{"status":"ok"}`. If the deployment is not Ready, stop and inspect build logs before any Firewall work.

---

### Task 4: Stage and validate the log-only Firewall rule

**Files:**
- No repository files change in this task.

**Interfaces:**
- Produces: Vercel rule `Agent chat per-IP limit` as a reviewed draft, then an active log-only rule after the user's publish command.
- Project: `wu-yu-portfolio`.
- Scope: `bwbybs-projects`.

- [ ] **Step 1: Reconfirm that no unrelated draft exists**

Run:

```bash
vercel firewall rules list --expand --json --project wu-yu-portfolio --scope bwbybs-projects
vercel firewall diff --json --project wu-yu-portfolio --scope bwbybs-projects
```

Expected before staging: no custom rule named `Agent chat per-IP limit` and `changes: []`. If any draft exists, stop and show it to the user; do not mix changes.

- [ ] **Step 2: Stage the log-only rate rule**

Run:

```bash
vercel firewall rules add "Agent chat per-IP limit" \
  --project wu-yu-portfolio \
  --scope bwbybs-projects \
  --description "Observe POST /api/chat bursts before Preview enforcement" \
  --condition '{"type":"path","op":"eq","value":"/api/chat"}' \
  --condition '{"type":"method","op":"eq","value":"POST"}' \
  --action rate_limit \
  --rate-limit-window 60 \
  --rate-limit-requests 10 \
  --rate-limit-keys ip \
  --rate-limit-algo fixed_window \
  --rate-limit-action log \
  --yes
```

Expected: the CLI creates only a draft. If it reports a plan/upgrade error, stop and follow Task 4 Step 6.

- [ ] **Step 3: Inspect the complete rule and draft diff**

Run:

```bash
vercel firewall rules inspect "Agent chat per-IP limit" --json --project wu-yu-portfolio --scope bwbybs-projects
vercel firewall diff --json --project wu-yu-portfolio --scope bwbybs-projects
```

Verify all of the following before asking the user to publish:

- Conditions are exactly `path == /api/chat` AND `method == POST`.
- Window is 60 seconds, request count is 10, key is IP, algorithm is fixed window.
- Exceeded action is `log`.
- The diff contains no other rules, IP blocks, managed rulesets, Attack Mode, or bypass changes.

- [ ] **Step 4: Stop for the user's log-stage publish**

Give the user this exact command and wait for them to run it:

```bash
vercel firewall publish --project wu-yu-portfolio --scope bwbybs-projects --yes
```

Do not execute this command on the user's behalf.

- [ ] **Step 5: Verify the active log rule without model calls**

After the user confirms publication, inspect the active rule, wait for a new 60-second counter window, and send 11 unknown questions:

```bash
vercel firewall rules inspect "Agent chat per-IP limit" --json --project wu-yu-portfolio --scope bwbybs-projects
sleep 60
for AGENT_REQUEST_INDEX in {1..11}; do
  vercel curl "$AGENT_PREVIEW_URL/api/chat" -- \
    --silent \
    --output /dev/null \
    --write-out "request=$AGENT_REQUEST_INDEX status=%{http_code}\n" \
    --request POST \
    --header 'Content-Type: application/json' \
    --data '{"message":"你最喜欢什么颜色？","history":[]}'
done
```

Expected: all requests remain 200 because the exceeded action is log. Then obtain the rule ID from the inspect output, assign it to `AGENT_RULE_ID`, and run:

```bash
vercel firewall traffic list \
  --project wu-yu-portfolio \
  --scope bwbybs-projects \
  --rule "$AGENT_RULE_ID" \
  --path /api/chat \
  --since 15m \
  --json
vercel logs "$AGENT_PREVIEW_URL" --limit 50
```

Expected: Firewall traffic shows rule activity; Runtime Logs for the test questions show `retrieved_chunks: 0` and contain no HeiyuCode request line.

- [ ] **Step 6: Handle a Hobby plan rejection without expanding scope**

Only if Step 2 or the user's Step 4 publish is rejected by the plan:

1. Run `vercel firewall diff --json --project wu-yu-portfolio --scope bwbybs-projects` and record whether a draft remains.
2. Do not publish, discard, or replace it without showing the state to the user.
3. Stop implementation and update the deployment decision to Preview-only.
4. Do not proceed to Task 5 and do not add Redis/Upstash.

---

### Task 5: Change the rule to Preview-only 429 enforcement

**Files:**
- No repository files change in this task.

**Interfaces:**
- Consumes: the active log-only rule and its observed traffic from Task 4.
- Produces: a Preview-only active rule that returns HTTP 429 after 10 requests per IP in 60 seconds.

- [ ] **Step 1: Stage the complete enforcement rule**

Run one edit command that repeats every condition because Vercel replaces the condition list on edit:

```bash
vercel firewall rules edit "Agent chat per-IP limit" \
  --project wu-yu-portfolio \
  --scope bwbybs-projects \
  --description "Rate limit POST /api/chat in Preview only" \
  --condition '{"type":"path","op":"eq","value":"/api/chat"}' \
  --condition '{"type":"method","op":"eq","value":"POST"}' \
  --condition '{"type":"environment","op":"eq","value":"preview"}' \
  --action rate_limit \
  --rate-limit-window 60 \
  --rate-limit-requests 10 \
  --rate-limit-keys ip \
  --rate-limit-algo fixed_window \
  --rate-limit-action rate_limit \
  --yes
```

- [ ] **Step 2: Inspect the rule and diff before publication**

Run:

```bash
vercel firewall rules inspect "Agent chat per-IP limit" --json --project wu-yu-portfolio --scope bwbybs-projects
vercel firewall diff --json --project wu-yu-portfolio --scope bwbybs-projects
```

Verify:

- All three conditions are joined by AND.
- `environment == preview` is present.
- The action is rate limit with a 429-style `rate_limit` exceeded action.
- No Production deployment, model configuration, IP block, or unrelated Firewall rule changes appear.

- [ ] **Step 3: Stop for the user's Preview-enforcement publish**

Give the user this exact command and wait for them to run it:

```bash
vercel firewall publish --project wu-yu-portfolio --scope bwbybs-projects --yes
```

Do not execute this command on the user's behalf.

- [ ] **Step 4: Verify Preview 429 after a fresh window**

After publication, wait for a fresh counter window and issue 11 unknown questions:

```bash
sleep 60
for AGENT_REQUEST_INDEX in {1..11}; do
  vercel curl "$AGENT_PREVIEW_URL/api/chat" -- \
    --silent \
    --output /dev/null \
    --write-out "request=$AGENT_REQUEST_INDEX status=%{http_code}\n" \
    --request POST \
    --header 'Content-Type: application/json' \
    --data '{"message":"你最喜欢什么颜色？","history":[]}'
done
```

Expected in a fresh fixed window: the first 10 requests return 200 and at least the 11th returns 429. If region routing makes the exact order differ, require at least one reproducible 429 and use Firewall Traffic to confirm the same rule caused it.

- [ ] **Step 5: Confirm unrelated routes and model boundaries**

Run:

```bash
vercel curl "$AGENT_PREVIEW_URL/api/health"
vercel firewall traffic list \
  --project wu-yu-portfolio \
  --scope bwbybs-projects \
  --rule "$AGENT_RULE_ID" \
  --path /api/chat \
  --since 15m \
  --json
vercel logs "$AGENT_PREVIEW_URL" --limit 50
```

Expected:

- Health remains 200.
- Firewall traffic records the rate-limit action.
- Only requests admitted to FastAPI appear in Runtime Logs.
- Admitted unknown questions show `retrieved_chunks: 0` and no HeiyuCode request.
- Production remains untouched because the rule includes `environment=preview`.

---

### Task 6: Record the phase and run final verification

**Files:**
- Modify: `src/content/posts/online-preview-deployment.md`

**Interfaces:**
- Consumes: verified Task 4 and Task 5 results.
- Produces: a truthful stage draft that records capability, limitations, 429 evidence, and the Production hold.

- [ ] **Step 1: Update the browser acceptance checklist from the user's completed review**

Mark these existing items complete:

```md
- [x] 页面显示远程回答和来源。
- [x] 移动端、错误、重试和清空状态正常。
```

- [ ] **Step 2: Replace the abuse-protection section with verified findings**

Replace the current Section 7 bullets with:

```md
## 7. 免费条件下的滥用防护

- 消息长度和历史条数限制只是输入保护，不是频率限制。
- Vercel 项目自带系统级防护；IP Bypass 和 OWASP 规则不属于当前免费能力，本项目没有启用它们。
- `POST /api/chat` 已配置每 IP 每 60 秒最多 10 次的固定窗口规则，阶段一先记录超限流量，阶段二只在 Preview 执行 429。
- 限流验收使用检索为空的问题，FastAPI 直接返回固定边界回答，因此测试流量没有调用模型。
- IP 计数按区域维护，也可能被多 IP 绕过；正式公开前仍需在中转站账户设置额度或余额上限。
- Production 继续保持未提升状态，限流规则暂不对 Production 执行。
```

Only use the completed wording above after both Firewall stages actually pass. If a Hobby plan rejection stopped Task 4, instead record that the project remains Preview-only because a free cross-instance rule could not be verified.

- [ ] **Step 3: Mark the Preview rate-limit evidence complete**

Change the writing-material checklist entry to:

```md
- [x] 限流 429 验证
```

Update the phase conclusion to state that Preview enforcement is active, Production is still held, and the supplier quota cap remains a Production prerequisite. Do not include IP addresses, OIDC tokens, API keys, raw Firewall payloads, or complete visitor questions.

- [ ] **Step 4: Run documentation and full regression verification**

Run:

```bash
PYTHONPATH=backend /Users/Admin/Documents/ChatGPT/个人网站/backend/.venv/bin/python -m pytest backend/tests tests/test_deploy_entrypoint.py -q
npm test -- --run
npm run check
npm run build
git diff --check
```

Expected: all backend/frontend tests pass; Astro check is clean; 5 pages build; diff check is empty.

- [ ] **Step 5: Commit and push the stage record**

```bash
git add src/content/posts/online-preview-deployment.md
git commit -m "docs: record preview rate-limit validation"
git push origin HEAD:codex/online-preview-closure
```

- [ ] **Step 6: Verify the final docs-only Preview and clean worktree**

Run:

```bash
vercel ls --limit 5
```

Set `AGENT_PREVIEW_URL` to the newest Preview for the final commit, then run:

```bash
vercel inspect "$AGENT_PREVIEW_URL" --wait
vercel curl "$AGENT_PREVIEW_URL/api/health"
git status --short --branch
```

Expected: Preview is Ready, health is 200, the branch tracks `origin/codex/online-preview-closure`, and the worktree has no uncommitted files. Do not promote this deployment.

---

## Final Verification Checklist

- [ ] Client preserves a non-2xx HTTP status in `AgentRequestError` without exposing the response body.
- [ ] ChatPanel shows the dedicated 429 copy and no immediate retry button.
- [ ] Ordinary request failures still show the existing retry path.
- [ ] Backend tests, frontend tests, Astro check, Astro build, and `git diff --check` pass.
- [ ] The active rule matches only `POST /api/chat`, uses 10 requests per 60 seconds per IP, and includes `environment=preview` before enforcement.
- [ ] The user personally publishes both reviewed Firewall stages.
- [ ] A fresh-window Preview burst produces at least one 429.
- [ ] Burst questions have zero retrieval hits and do not call HeiyuCode.
- [ ] `/api/health` remains 200.
- [ ] The deployment blog records the limitation of per-region/IP counting and the need for a supplier quota cap.
- [ ] Production model configuration and deployment remain unchanged.
