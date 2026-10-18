# Agent Workspace Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a formal `/agent/` ChatGPT-style workspace to the Astro portfolio while preserving the existing homepage and reusing its two typed Agent adapters.

**Architecture:** A new hydrated React `AgentWorkspace` owns workspace state and calls `askKnowledgeBase` or `askAgentBook` based on the selected assistant. Astro adds a route and navigation entry; global CSS scopes the new layout under `.agent-workspace` so the existing homepage `ChatPanel` remains unchanged. Browser localStorage persists sessions, assistant selection, sidebar state, and theme.

**Tech Stack:** Astro 7, React 19, TypeScript, Lucide React, existing Agent adapter modules, Vitest + Testing Library, and the existing global CSS.

**Spec:** `docs/superpowers/specs/2026-10-08-agent-workspace-design.md`

## Global Constraints

- Keep the existing homepage layout and `ChatPanel` behavior unchanged.
- Add a new route at `/agent/`; do not copy the ignored `.superpowers` prototype into production code.
- Reuse `askKnowledgeBase(question, history)` and `askAgentBook(question, conversationId)`; never expose API keys in browser code.
- Use assistant labels `了解 WU YU` and `AI-Agent-Book`.
- Persist only serializable conversation state under `wuyu-agent-workspace-v1`; malformed storage must fall back safely.
- Keep citations as an absolutely positioned overlay so opening them does not change message layout height.
- Exclude `.worktrees/**`, `.superpowers/**`, `dist/**`, and `node_modules/**` from Vitest discovery so the root test command represents this checkout.
- Follow the repository instruction to use `astro dev --background` if a dev server is needed.

---

### Task 1: Make the test boundary explicit

**Files:**
- Modify: `vitest.config.ts`
- Test: existing root tests under `tests/`

**Interfaces:**
- Produces a Vitest configuration that discovers only the current checkout's tests.

- [ ] **Step 1: Add explicit discovery and exclusion rules**

Update `test` in `vitest.config.ts` with:

```ts
include: ['tests/**/*.{test,spec}.{ts,tsx}'],
exclude: ['**/node_modules/**', '**/dist/**', '**/.worktrees/**', '**/.superpowers/**'],
```

- [ ] **Step 2: Run the root test command**

Run `npm test -- --run`. Expected: only the three root test files execute; existing failures, if any, are now attributable to current code.

- [ ] **Step 3: Commit the test-boundary change**

Run `git add vitest.config.ts && git commit -m "test: scope vitest to current checkout"` when the repository workflow calls for a checkpoint.

### Task 2: Define the workspace state contract and tests

**Files:**
- Create: `tests/components/AgentWorkspace.test.tsx`
- Create: `src/components/AgentWorkspace.tsx`

**Interfaces:**
- Consumes: `AgentMessage`, `AgentResponse`, `AgentBookResponse`, `askKnowledgeBase`, and `askAgentBook`.
- Produces: a default export React component `AgentWorkspace` and the serializable `WorkspaceConversation` state shape from the spec.

- [ ] **Step 1: Write failing interaction tests**

Create tests that cover these behaviors:

```tsx
it('starts with the personal assistant and can switch to Agent Book', async () => {
  render(<AgentWorkspace />);
  expect(screen.getByRole('button', { name: /切换助手，当前为 了解 WU YU/ })).toBeVisible();
  await user.click(screen.getByRole('button', { name: /切换助手/ }));
  await user.click(screen.getByRole('menuitemradio', { name: /AI-Agent-Book/ }));
  expect(screen.getByRole('button', { name: /切换助手，当前为 AI-Agent-Book/ })).toBeVisible();
});

it('sends through the adapter for the selected assistant and renders sources', async () => {
  mockedBook.mockResolvedValue({ answer: 'RAG 回答', conversation_id: 'conv-1', sources: ['第一章'], mode: 'dify' });
  render(<AgentWorkspace />);
  await user.click(screen.getByRole('button', { name: /切换助手/ }));
  await user.click(screen.getByRole('menuitemradio', { name: /AI-Agent-Book/ }));
  await user.click(screen.getByRole('button', { name: /什么是 Agent/ }));
  expect(await screen.findByText('RAG 回答')).toBeVisible();
  expect(mockedBook).toHaveBeenCalledWith('什么是 Agent？', null);
  await user.click(screen.getByRole('button', { name: /显示参考来源/ }));
  expect(screen.getByRole('region', { name: /参考来源/ })).toHaveTextContent('第一章');
});

it('opens a conversation from any point in its row and preserves retry state', async () => {
  mockedPersonal.mockRejectedValueOnce(new Error('network unavailable'));
  render(<AgentWorkspace />);
  await user.click(screen.getByRole('button', { name: '新建对话' }));
  await user.click(screen.getByRole('button', { name: /打开对话 你最近在学什么/ }));
  await user.click(screen.getByRole('button', { name: /你是谁/ }));
  expect(await screen.findByRole('button', { name: /重试/ })).toBeVisible();
  expect(screen.getByText('你是谁？')).toBeVisible();
});
```

The test file must mock both adapter functions with `vi.mock('@/lib/agent/client', ...)`, clear localStorage in `beforeEach`, and use Testing Library role/name assertions rather than CSS selectors.

- [ ] **Step 2: Run only the new test file to verify RED**

Run `npx vitest run tests/components/AgentWorkspace.test.tsx`. Expected: FAIL because `src/components/AgentWorkspace.tsx` does not exist yet.

- [ ] **Step 3: Implement minimal state and rendering**

Implement the component with:

```ts
type WorkspaceAgentId = 'personal' | 'book';
type WorkspaceConversation = {
  id: string;
  agent: WorkspaceAgentId;
  title: string;
  messages: AgentMessage[];
  providerConversationId?: string;
  updatedAt: number;
};
```

Use one state object for `activeAgent`, `selected`, `conversations`, `collapsed`, `theme`, and `settingsOpen`; initialize through a guarded `readWorkspaceState()` helper. Use `conversationVersion` or a request token to ignore late responses after clearing or switching conversations. The selected agent determines whether `askKnowledgeBase` receives the conversation's message history or `askAgentBook` receives its provider conversation id.

- [ ] **Step 4: Run the focused tests to verify GREEN**

Run `npx vitest run tests/components/AgentWorkspace.test.tsx`. Expected: all new workspace tests pass.

### Task 3: Add the formal route and navigation entry

**Files:**
- Create: `src/pages/agent.astro`
- Modify: `src/components/SiteHeader.astro`
- Modify: `src/components/MobileMenu.tsx`

**Interfaces:**
- Consumes: `AgentWorkspace` from Task 2.
- Produces: `/agent/` route and visible links from desktop and mobile navigation.

- [ ] **Step 1: Add the route shell**

Create `src/pages/agent.astro`:

```astro
---
import BaseLayout from '../layouts/BaseLayout.astro';
import AgentWorkspace from '../components/AgentWorkspace';
---

<BaseLayout title="Agent · Wu Yu" description="WU YU 的个人知识库与 Agent Book 对话工作台。" activePath="/agent/">
  <section class="agent-page page-shell">
    <AgentWorkspace client:load />
  </section>
</BaseLayout>
```

- [ ] **Step 2: Point existing Agent CTAs to `/agent/`**

Change the desktop and mobile Agent links from `/#agent` to `/agent/`, leaving the homepage's internal “点击开始对话” anchor unchanged.

- [ ] **Step 3: Run type checking**

Run `npm run check`. Expected: zero errors, warnings, and hints.

### Task 4: Style the workspace without changing homepage chat styles

**Files:**
- Modify: `src/styles/global.css`

**Interfaces:**
- Consumes: the class names emitted by `AgentWorkspace`.
- Produces: desktop expanded/collapsed layout, mobile drawer behavior, theme menu, message actions, and citation overlay.

- [ ] **Step 1: Add workspace design tokens and layout styles**

Add a scoped `.agent-workspace` block with paper/surface/text/muted/line/accent variables, a 286px sidebar, a 72px collapsed rail, a flexible main column, and an absolute citation panel. Keep all selectors prefixed with `.agent-workspace` or `.agent-page`.

- [ ] **Step 2: Add responsive rules**

At `max-width: 820px`, use a mobile drawer with an overlay, preserve the same assistant and conversation controls, and allow the message column to shrink without horizontal overflow. At `max-width: 480px`, reduce padding and keep send/action controls at a usable touch size.

- [ ] **Step 3: Add theme rules**

Support `system`, `light`, `warm`, and `dark` through `[data-agent-theme]` selectors on the workspace root. Render the theme menu as an absolute floating panel below the settings control so opening it does not change header dimensions.

- [ ] **Step 4: Run focused component tests and build**

Run `npx vitest run tests/components/AgentWorkspace.test.tsx`, `npm run check`, and `npm run build`. Expected: all pass and `/agent/index.html` appears in the static output.

### Task 5: Verify the complete flow and document usage

**Files:**
- Modify: `README.md`
- Test: `tests/components/AgentWorkspace.test.tsx` and all root tests

**Interfaces:**
- Consumes: the completed route, navigation, component, and style contracts.
- Produces: a reproducible local verification path for future content/API changes.

- [ ] **Step 1: Document local startup and API behavior**

Add a concise README section:

```text
npm install
npm run dev
# visit http://localhost:4321/agent/
```

Explain that the personal assistant falls back to demo mode when `PUBLIC_AGENT_API_URL` is unset, while Agent Book requires the existing backend/Dify configuration. Do not include secret values.

- [ ] **Step 2: Run the complete current-checkout verification**

Run `npm test -- --run`, `npm run check`, and `npm run build`. Expected: root tests pass, Astro diagnostics are clean, and static output includes `/agent/index.html`.

- [ ] **Step 3: Perform a manual browser smoke check**

If a server is needed, start it with `astro dev --background`. Check desktop and narrow mobile widths for: navigation to `/agent/`, assistant switching, new conversation, whole-row opening, theme menu overlay, citation overlay, clear, and retry. Stop the server with `astro dev stop` after checking.

- [ ] **Step 4: Commit the completed migration**

Run:

```bash
git add vitest.config.ts src/components/AgentWorkspace.tsx src/pages/agent.astro src/components/SiteHeader.astro src/components/MobileMenu.tsx src/styles/global.css tests/components/AgentWorkspace.test.tsx README.md docs/superpowers/specs/2026-10-08-agent-workspace-design.md docs/superpowers/plans/2026-10-08-agent-workspace-migration-plan.md
git commit -m "feat: add agent workspace page"
```
