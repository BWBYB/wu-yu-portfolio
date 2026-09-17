# Personal Portfolio and Knowledge Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a statically deployable Astro portfolio for Wu Yu with a warm editorial visual system, a complete SPMTrack case study, honest placeholder entries for unfinished content, and a replaceable local-demo Agent chat interface.

**Architecture:** Astro owns routes, Markdown content, layout, metadata, and static output. React islands own only stateful interactions: the Agent preview/chat and mobile navigation. All Agent calls go through a typed `askKnowledgeBase()` adapter so a later FastAPI/RAG service can replace the local answer map without changing pages or components.

**Tech Stack:** Astro, React, TypeScript, Tailwind CSS, Lucide React icons, Markdown/MDX content collections, Vitest + Testing Library for adapter/component behavior, and Playwright/browser screenshots for responsive verification.

**Spec:** `docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md`

## Global Constraints

- Position the author as `A full-stack developer moving toward AI Agent development.`
- Use the personal-introduction homepage and warm editorial visual direction selected during brainstorming.
- Complete only the SPMTrack case study in version one; mark the medical reimbursement mini-program and Cangqiong takeaway project as `资料整理中`.
- Do not invent blog articles or project facts; use the supplied resume and SPMTrack repository documentation as the factual sources.
- Keep FastAPI, LangChain, ChromaDB, embeddings, retrieval ranking, and real LLM calls out of version one.
- Never put an OpenAI-compatible API key in browser code.
- Keep the Agent contract exactly typed as `AgentMessage`, `AgentResponse`, and `askKnowledgeBase(question, history)`.
- Use the suggested palette: paper `#F7F4EE`, ink `#18212B`, muted `#6B6259`, terracotta `#B45C38`, line `#C9C1B5`, surface `#FFFDF9`.
- Meet desktop and mobile no-overflow, keyboard-accessible, explicit loading/error/clear states, and reduced-motion requirements.
- Validate with a production build, type/content checks, focused tests, and browser screenshots before claiming completion.
- The current workspace rejects creation of `.git`; run commit checkpoints only if a repository is initialized by the environment or user.

---

## File Map

The implementation will create these focused units:

```text
package.json                         dependency scripts and project metadata
astro.config.mjs                     Astro + React + Tailwind integration
tsconfig.json                        strict TypeScript configuration
vitest.config.ts                     jsdom test configuration
src/content.config.ts                content collection schemas
src/styles/global.css                design tokens, typography, responsive primitives
src/layouts/BaseLayout.astro         document shell, metadata, header/footer slots
src/components/SiteHeader.astro      navigation and Agent CTA
src/components/SiteFooter.astro      contact and resume links
src/components/MobileMenu.tsx        mobile menu state
src/components/AgentPreview.tsx      homepage Agent island and recommended prompts
src/components/ChatPanel.tsx         reusable conversation UI and states
src/lib/agent/types.ts               AgentMessage and AgentResponse types
src/lib/agent/demo.ts                factual local answer map and fallback
src/lib/agent/client.ts              typed askKnowledgeBase adapter
src/lib/content.ts                   content loading and status helpers
src/pages/index.astro                homepage composition
src/pages/projects/index.astro      project index
src/pages/projects/spmtrack.astro   complete SPMTrack case study
src/pages/blog/index.astro           blog index with honest placeholders
src/pages/about.astro                profile, education, campus experience, skills
src/content/profile.md               profile and homepage copy
src/content/projects/*.md            project metadata and SPMTrack details
src/content/experiences/*.md         student union and debate team facts
src/content/posts/*.md               explicitly unpublished blog placeholders
public/resume/wu-yu-resume.pdf       supplied resume copy
tests/agent/demo.test.ts             adapter behavior tests
tests/components/ChatPanel.test.tsx  chat interaction/state tests
```

## Task 1: Scaffold the Astro Application

**Files:**
- Create: `package.json`
- Create: `astro.config.mjs`
- Create: `tsconfig.json`
- Create: `vitest.config.ts`
- Create: `src/pages/index.astro`
- Create: `src/styles/global.css`

**Interfaces:**
- Produces an Astro application that can run with `npm run dev`, validate with `npm run check`, test with `npm run test`, and build with `npm run build`.
- Provides the `@/*` alias to `src/*` and React client hydration support for later tasks.

- [ ] **Step 1: Initialize the minimal Astro project**

Run from `/Users/Admin/Documents/ChatGPT/个人网站`:

```bash
npm create astro@latest . -- --template minimal --typescript strict --install --no-git
```

Expected: Astro starter files exist and dependencies install without creating a nested directory.

- [ ] **Step 2: Install the required runtime and test dependencies**

```bash
npm install @astrojs/react @astrojs/mdx @tailwindcss/vite react react-dom lucide-react
npm install -D @testing-library/jest-dom @testing-library/react @testing-library/user-event jsdom vitest
```

Expected: `package.json` contains Astro, React, Tailwind, Lucide, Vitest, and Testing Library dependencies.

- [ ] **Step 3: Configure Astro, React, Tailwind, and TypeScript aliases**

Set `astro.config.mjs` to integrate React and Tailwind's Vite plugin:

```js
import { defineConfig } from "astro/config";
import react from "@astrojs/react";
import mdx from "@astrojs/mdx";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  integrations: [react(), mdx()],
  vite: { plugins: [tailwindcss()] },
});
```

Set `tsconfig.json` to extend Astro's strict config and expose:

```json
{
  "extends": "astro/tsconfigs/strict",
  "compilerOptions": {
    "baseUrl": ".",
    "paths": { "@/*": ["src/*"] }
  }
}
```

Set `vitest.config.ts` to use jsdom, the `src` alias, and `setupFiles: ["./tests/setup.ts"]`; create `tests/setup.ts` importing `@testing-library/jest-dom/vitest`.

- [ ] **Step 4: Add project scripts and a smoke page**

Ensure `package.json` scripts include:

```json
{
  "dev": "astro dev",
  "build": "astro build",
  "preview": "astro preview",
  "check": "astro check",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

Use `src/pages/index.astro` to render an `h1` with `Wu Yu` and import `src/styles/global.css`.

- [ ] **Step 5: Verify the scaffold**

Run:

```bash
npm run check
npm run test
npm run build
```

Expected: all three commands exit successfully; the build produces `dist/`.

- [ ] **Step 6: Commit the scaffold checkpoint when Git is available**

```bash
git add package.json package-lock.json astro.config.mjs tsconfig.json vitest.config.ts tests/setup.ts src/pages/index.astro src/styles/global.css
git commit -m "chore: scaffold astro portfolio"
```

## Task 2: Establish Content Collections and Source Material

**Files:**
- Create: `src/content.config.ts`
- Create: `src/content/profile.md`
- Create: `src/content/projects/spmtrack.md`
- Create: `src/content/projects/medical-reimbursement.md`
- Create: `src/content/projects/takeout-platform.md`
- Create: `src/content/experiences/student-union.md`
- Create: `src/content/experiences/debate-team.md`
- Create: `src/content/posts/learning-rag.md`
- Create: `src/content/posts/project-review.md`
- Create: `src/lib/content.ts`
- Copy: `public/resume/wu-yu-resume.pdf`

**Interfaces:**
- Produces typed `profile`, `projects`, `experiences`, and `posts` collections.
- Each project exposes `title`, `slug`, `summary`, `status`, `date`, `category`, `tags`, `featured`, and optional `externalUrl`.
- `status` is exactly `published | organizing` so pages can render honest incomplete-content labels.

- [ ] **Step 1: Define collection schemas**

Create `src/content.config.ts` with `defineCollection` and Zod schemas. The project schema must require `status`, `title`, `slug`, `summary`, and `tags`, while allowing `date`, `category`, `featured`, and `externalUrl`. Post and experience schemas must carry the same explicit status field.

- [ ] **Step 2: Write the factual profile content**

Create `profile.md` with frontmatter and body based on the supplied resume:

```yaml
title: Wu Yu
location: 深圳
graduation: 2026
school: 华侨大学
major: 计算机科学与技术
target: 正在从全栈开发走向 AI Agent 的开发者
```

Include the resume's React, Vue3, TypeScript, FastAPI, Spring Boot, Node.js, WebSocket, MySQL, SQLite, Neo4j, Docker, Git/GitHub, and AI-assisted development tools, without adding unsupported claims.

- [ ] **Step 3: Write the SPMTrack source document**

Create `spmtrack.md` with published frontmatter and sections for context, delivered product, responsibilities, architecture, task lifecycle, monitoring, deployment, and reflection. Use the resume and repository docs to state:

```text
React + TypeScript + Vite + Recharts
Spring Boot gateway
FastAPI inference service
SQLite task persistence
Docker delivery
SPMTrack, SPMTrack MOT, and CSRT modes
PENDING/RUNNING/SUCCESS/FAILED/CANCELED task status
preparing/evaluating/rendering/transcoding stages
Canvas ROI selection and result playback
```

Clearly label the upstream CVPR research implementation as the foundation and describe Wu Yu's work as the application-layer integration and delivery work supported by the resume.

- [ ] **Step 4: Write honest organizing-soon content files**

Set `status: organizing` for the medical reimbursement and Cangqiong projects. Include only the resume-provided title, date, team type, technologies, and a short sentence saying the detailed case study is being organized. Set both blog files to `status: organizing` with titles such as `RAG 学习记录` and `SPMTrack 项目复盘`, but do not add fabricated article bodies.

- [ ] **Step 5: Add campus experience source files**

Write the student union and debate team files with the resume's dates, responsibilities, and outcomes: process coordination, meeting execution, activity support, five-person core team management, four cross-school friendly matches, and the 新生杯 top-eight result.

- [ ] **Step 6: Copy the supplied resume into public assets**

```bash
mkdir -p public/resume
cp '/Users/Admin/Downloads/吴禹简历7.16(1).pdf' public/resume/wu-yu-resume.pdf
```

Expected: `public/resume/wu-yu-resume.pdf` exists and is linked only as a download asset.

- [ ] **Step 7: Add content loading helpers**

Create `src/lib/content.ts` with typed helpers:

```ts
export const projects = await getCollection("projects");
export const publishedProjects = projects.filter(({ data }) => data.status === "published");
export const organizingProjects = projects.filter(({ data }) => data.status === "organizing");
```

Export a `statusLabel(status: "published" | "organizing")` helper returning `已发布` or `资料整理中`.

- [ ] **Step 8: Verify content validation**

Run:

```bash
npm run check
```

Expected: Astro reports valid frontmatter and no missing required fields.

- [ ] **Step 9: Commit the content checkpoint when Git is available**

```bash
git add src/content.config.ts src/content src/lib/content.ts public/resume/wu-yu-resume.pdf
git commit -m "feat: add portfolio content collections"
```

## Task 3: Build the Warm Editorial Design System and Site Shell

**Files:**
- Modify: `src/styles/global.css`
- Create: `src/layouts/BaseLayout.astro`
- Create: `src/components/SiteHeader.astro`
- Create: `src/components/SiteFooter.astro`
- Create: `src/components/MobileMenu.tsx`
- Modify: `src/pages/index.astro`

**Interfaces:**
- `BaseLayout.astro` accepts `title`, `description`, and optional `activePath` props and renders the document shell.
- `SiteHeader.astro` renders links for `/`, `/projects`, `/blog`, `/about`, plus a link or button targeting `#agent`.
- `MobileMenu.tsx` exposes the same navigation in a keyboard-accessible disclosure island.

- [ ] **Step 1: Define design tokens and typography**

In `global.css`, import Tailwind and define `:root` tokens for the six approved colors. Add a serif display stack (`Georgia`, `Times New Roman`, serif) and a sans body stack (`Inter`, `ui-sans-serif`, system fallback). Add base rules for body background, ink text, focus-visible outlines, selection color, link transitions, and `prefers-reduced-motion`.

- [ ] **Step 2: Add reusable layout primitives**

Define classes or component styles for:

```text
.page-shell     centered max-width container with responsive gutters
.eyebrow        uppercase/small metadata label
.section-rule   thin horizontal divider
.button-primary terracotta or ink filled action
.button-quiet   outlined action
.status-label   non-color-only project status label
.surface        paper/surface panel with <= 8px radius
```

Keep the page as full-width bands with constrained inner content; use cards only for repeated project entries or the framed Agent tool.

- [ ] **Step 3: Build `BaseLayout.astro`**

Render `<!doctype html>`, language metadata, title, description, canonical-safe viewport settings, global CSS, `SiteHeader`, a `<main id="main-content">` slot, and `SiteFooter`. Add skip-to-content link and ensure the page title is route-specific.

- [ ] **Step 4: Build desktop and mobile navigation**

Use `SiteHeader.astro` for desktop and hydrate `MobileMenu.tsx` with `client:load` or `client:visible`. The menu must close on link activation, expose `aria-expanded`, use a familiar menu/close Lucide icon, and never create horizontal overflow.

- [ ] **Step 5: Build the footer and resume link**

Show `814153912@qq.com`, `深圳`, a GitHub link to `https://github.com/BWBYB/SPMTrack`, and `/resume/wu-yu-resume.pdf` with download semantics. Use icon+text links and tooltips only where an icon is used without visible text.

- [ ] **Step 6: Verify shell behavior**

Run `npm run check`, start `npm run dev -- --host 127.0.0.1`, and verify `/`, `/projects`, `/blog`, and `/about` currently resolve or show the intended scaffold state. Check keyboard focus through header links and mobile menu.

- [ ] **Step 7: Commit the shell checkpoint when Git is available**

```bash
git add src/styles/global.css src/layouts/BaseLayout.astro src/components/SiteHeader.astro src/components/SiteFooter.astro src/components/MobileMenu.tsx src/pages/index.astro
git commit -m "feat: add warm editorial site shell"
```

## Task 4: Implement the Typed Local Agent Adapter

**Files:**
- Create: `src/lib/agent/types.ts`
- Create: `src/lib/agent/demo.ts`
- Create: `src/lib/agent/client.ts`
- Create: `tests/agent/demo.test.ts`

**Interfaces:**
- `AgentMessage = { role: "user" | "assistant"; content: string }`.
- `AgentResponse = { answer: string; sources?: string[]; mode: "demo" | "remote" }`.
- `askKnowledgeBase(question: string, history: AgentMessage[]): Promise<AgentResponse>` returns local demo data today and is the only UI-facing Agent function.

- [ ] **Step 1: Write failing adapter tests**

In `tests/agent/demo.test.ts`, cover exact behaviors:

```ts
it("answers the SPMTrack responsibility prompt with demo mode and a source label", async () => {
  const response = await askKnowledgeBase("你在 SPMTrack 里负责什么？", []);
  expect(response.mode).toBe("demo");
  expect(response.answer).toContain("React");
  expect(response.sources).toContain("SPMTrack 项目资料");
});

it("returns a bounded fallback instead of inventing unknown facts", async () => {
  const response = await askKnowledgeBase("你最喜欢的电影是什么？", []);
  expect(response.mode).toBe("demo");
  expect(response.answer).toContain("资料中没有");
});

it("does not mutate conversation history", async () => {
  const history = [{ role: "user", content: "你是谁？" }] as const;
  await askKnowledgeBase("你在学习什么？", [...history]);
  expect(history).toHaveLength(1);
});
```

- [ ] **Step 2: Run the focused tests and observe failure**

Run `npm run test -- tests/agent/demo.test.ts`. Expected: FAIL because the typed adapter modules do not exist yet.

- [ ] **Step 3: Implement types and factual demo answers**

Create `demo.ts` with normalized keyword matching for these recommended questions: identity, SPMTrack responsibilities, architecture/technology choices, and current AI Agent learning direction. Each answer must be traceable to `profile.md`, `spmtrack.md`, or the resume and include a short source label. Unknown prompts return an answer containing `目前资料中没有` and do not speculate.

- [ ] **Step 4: Implement the adapter boundary**

Create `client.ts`:

```ts
export async function askKnowledgeBase(
  question: string,
  history: AgentMessage[],
): Promise<AgentResponse> {
  return getDemoResponse(question, history);
}
```

Do not add fetch, environment variables, API keys, or provider-specific imports. Add a comment only where it explains the future remote adapter boundary.

- [ ] **Step 5: Run focused tests and full checks**

Run:

```bash
npm run test -- tests/agent/demo.test.ts
npm run check
```

Expected: all focused tests pass and types validate.

- [ ] **Step 6: Commit the Agent boundary checkpoint when Git is available**

```bash
git add src/lib/agent tests/agent
git commit -m "feat: add replaceable local agent adapter"
```

## Task 5: Build the Homepage and Chat Experience

**Files:**
- Create: `src/components/ChatPanel.tsx`
- Create: `src/components/AgentPreview.tsx`
- Create: `tests/components/ChatPanel.test.tsx`
- Modify: `src/pages/index.astro`
- Modify: `src/styles/global.css`

**Interfaces:**
- `AgentPreview` accepts optional `compact?: boolean` and renders the four recommended prompts.
- `ChatPanel` accepts `recommendedPrompts?: readonly string[]`, owns `messages`, `input`, `isLoading`, `error`, and retry/clear handlers; it calls `askKnowledgeBase` and does not know how demo/remote mode is implemented.
- `ChatPanel` displays `AgentResponse.sources` and `AgentResponse.mode` without requiring them to exist.

- [ ] **Step 1: Write failing chat tests**

Use Testing Library and User Event to test:

```tsx
it("appends a recommended question and demo answer", async () => {
  render(<ChatPanel recommendedPrompts={["你在 SPMTrack 里负责什么？"]} />);
  await user.click(screen.getByRole("button", { name: /你在 SPMTrack 里负责什么/ }));
  expect(await screen.findByText(/React/)).toBeVisible();
  expect(screen.getByText(/演示模式/)).toBeVisible();
});

it("does not submit empty input and can clear the conversation", async () => {
  render(<ChatPanel />);
  expect(screen.getByRole("button", { name: /发送/ })).toBeDisabled();
  await user.click(screen.getByRole("button", { name: /清空对话/ }));
  expect(screen.getByText(/还没有问题/)).toBeVisible();
});

it("shows a recoverable failure state", async () => {
  const askKnowledgeBase = vi.mocked(await import("@/lib/agent/client")).askKnowledgeBase;
  askKnowledgeBase.mockRejectedValueOnce(new Error("network unavailable"));
  render(<ChatPanel recommendedPrompts={["你是谁？"]} />);
  await user.click(screen.getByRole("button", { name: /你是谁/ }));
  expect(await screen.findByRole("button", { name: /重试/ })).toBeVisible();
});
```

Add `vi.mock("@/lib/agent/client", () => ({ askKnowledgeBase: vi.fn() }))` at the top of the test file, reset the mock in `beforeEach`, and mock the successful response in the first test. This keeps UI tests independent from the answer map implementation.

- [ ] **Step 2: Run focused tests and observe failure**

Run `npm run test -- tests/components/ChatPanel.test.tsx`. Expected: FAIL because the chat components do not exist.

- [ ] **Step 3: Implement the reusable ChatPanel**

Build semantic markup with a labelled log (`role="log"`, `aria-live="polite"`), message bubbles, status text, a text input, send button with `Send` icon, clear button with `Trash2` icon, and retry button with `RotateCcw` icon. Keep all controls at stable dimensions. Submit on Enter while allowing Shift+Enter for a newline. Preserve the failed prompt for retry.

- [ ] **Step 4: Implement AgentPreview and homepage hero**

Compose `AgentPreview` as a small section wrapper that supplies the four prompts to `ChatPanel`, then compose `index.astro` with `BaseLayout`, the `2026 届 · 深圳` eyebrow, headline `从全栈工程，走向 AI Agent。`, capability summary, two hero actions, an Agent preview section with `id="agent"`, featured project teaser, two organizing-soon teaser cards, technical path, and footer. Hydrate `AgentPreview` with `client:visible`.

Use the selected warm editorial visual hierarchy: display serif headline, terracotta action, ink secondary action, thin rules, small metadata, and no gradient or oversized hero card.

- [ ] **Step 5: Add empty/loading/error/clear visual states**

Render a welcome state before messages, a loading status while awaiting the adapter, an inline error with retry, a visible `演示模式` label on local responses, and a clear button that returns to the welcome state. On mobile, make prompt buttons a horizontal scroll row and keep message content single-column.

- [ ] **Step 6: Run component tests and check the homepage**

Run:

```bash
npm run test -- tests/components/ChatPanel.test.tsx
npm run check
npm run build
```

Expected: tests pass, Astro checks pass, and the homepage appears in `dist/`.

- [ ] **Step 7: Commit the homepage checkpoint when Git is available**

```bash
git add src/components/ChatPanel.tsx src/components/AgentPreview.tsx tests/components/ChatPanel.test.tsx src/pages/index.astro src/styles/global.css
git commit -m "feat: add homepage and local agent chat"
```

## Task 6: Build Project, About, and Blog Routes

**Files:**
- Create: `src/pages/projects/index.astro`
- Create: `src/pages/projects/spmtrack.astro`
- Create: `src/pages/blog/index.astro`
- Create: `src/pages/about.astro`
- Modify: `src/styles/global.css`

**Interfaces:**
- Project pages consume the `projects` collection and render `statusLabel` for organizing entries.
- The SPMTrack page consumes only published SPMTrack content and includes a stable external GitHub link.
- Blog and about pages use the same `BaseLayout` and preserve the same content-loading conventions as the homepage.

- [ ] **Step 1: Write the projects index**

Render SPMTrack as the lead project with title, date, category, summary, tags, and a `查看案例` link. Render the two other projects as compact repeated entries with `资料整理中`, no fake detail links, and the facts from their source files.

- [ ] **Step 2: Write the SPMTrack case study page**

Create a readable long-form layout with:

```text
project header and metadata
why this project matters
four-layer architecture diagram/list
browser request and task workflow
status/stage state machine
your contribution sections
monitoring and deployment
engineering reflection
repository link
```

Use CSS flow diagrams or semantic lists rather than manually drawn SVG. Keep the architecture understandable on mobile by stacking layers and allowing code/status labels to wrap.

- [ ] **Step 3: Write the blog index placeholder**

List the two organizing blog titles with `资料整理中` and a short explanation that the page will hold RAG learning notes and an SPMTrack project review once source material is prepared. Do not render invented article body text.

- [ ] **Step 4: Write the about page**

Show education, target direction, technical skills, student union experience, debate team experience, contact information, and resume download. Use short scannable sections rather than copying the two-page resume verbatim.

- [ ] **Step 5: Verify route output and links**

Run `npm run check && npm run build`. Inspect generated paths for `/projects/`, `/projects/spmtrack/`, `/blog/`, and `/about/`. Confirm `/resume/wu-yu-resume.pdf` exists in the build output and the SPMTrack link is exactly `https://github.com/BWBYB/SPMTrack`.

- [ ] **Step 6: Commit the route checkpoint when Git is available**

```bash
git add src/pages/projects src/pages/blog src/pages/about.astro src/styles/global.css
git commit -m "feat: add project, about, and blog routes"
```

## Task 7: Responsive, Accessibility, and Browser Verification

**Files:**
- Modify: `src/styles/global.css`
- Modify: `src/components/SiteHeader.astro`
- Modify: `src/components/SiteFooter.astro`
- Modify: `src/components/MobileMenu.tsx`
- Modify: `src/components/ChatPanel.tsx`
- Modify: any route file only where browser verification finds a concrete layout defect

**Interfaces:**
- No public data contract changes; this task hardens the approved UI against real viewport and keyboard behavior.

- [ ] **Step 1: Run static validation before browser work**

```bash
npm run test
npm run check
npm run build
```

Expected: all pass before visual inspection.

- [ ] **Step 2: Start the local production preview**

```bash
npm run preview -- --host 127.0.0.1
```

Open the reported URL in a browser and inspect `/`, `/projects/`, `/projects/spmtrack/`, `/blog/`, and `/about/`.

- [ ] **Step 3: Verify desktop visual behavior**

At a 1440px-wide viewport, capture or inspect the homepage and SPMTrack page. Confirm:

```text
no overlapping hero copy or actions
Agent panel is visible near the top
SPMTrack receives the strongest project emphasis
metadata and status labels stay aligned
long code/status tokens wrap without resizing controls
```

- [ ] **Step 4: Verify mobile visual behavior**

At 390px x 844px, inspect all routes. Confirm:

```text
header collapses into the accessible menu
headline wraps inside its parent
prompt row scrolls horizontally without page overflow
chat messages and buttons remain single-column
architecture sections stack cleanly
footer links wrap without clipping
```

- [ ] **Step 5: Verify interaction and keyboard behavior**

Use keyboard-only navigation to open the mobile menu, activate a recommended prompt, type and submit a question, clear the conversation, and navigate to the SPMTrack page. Confirm focus-visible styles, `aria-expanded`, `aria-live`, disabled send behavior, and retry behavior.

- [ ] **Step 6: Run a final repository scan**

```bash
rg -n "TBD|TODO|lorem|example\.com|OPENAI_API_KEY|api_key" src public package.json
```

Expected: no placeholder prose, invented email/domain, or browser secret. `资料整理中` is allowed only on the explicitly incomplete project/blog entries.

- [ ] **Step 7: Commit the verification checkpoint when Git is available**

```bash
git add src
git commit -m "test: verify responsive portfolio experience"
```

## Final Acceptance Checklist

- [ ] `npm run test` passes.
- [ ] `npm run check` passes.
- [ ] `npm run build` passes.
- [ ] Homepage communicates the full-stack-to-Agent positioning within the first viewport.
- [ ] Agent recommended questions and free-form input work in demo mode.
- [ ] Agent empty, loading, failure, retry, and clear states are visible and usable.
- [ ] SPMTrack page explains the four-layer system, task lifecycle, responsibilities, monitoring, Docker, and smoke checks.
- [ ] Other projects and blog entries are explicitly marked as organizing, with no invented details.
- [ ] Resume download resolves.
- [ ] Desktop and mobile browser inspection shows no clipping, horizontal overflow, or overlapping content.
- [ ] No secret key or real LLM call is shipped in the browser.
