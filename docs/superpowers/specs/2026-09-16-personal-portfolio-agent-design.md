# Personal Portfolio and Knowledge Agent Design

Date: 2026-09-16  
Status: Design approved in conversation; awaiting written-spec review

## 1. Context and Goal

Build a one-week MVP personal portfolio site for Wu Yu, a 2026 Computer Science undergraduate at Huaqiao University who is targeting Shenzhen frontend, full-stack, and AI Agent development roles.

The site must present a credible transition from full-stack engineering to AI Agent development. Its primary proof point is the SPMTrack graduation project: a research tracking implementation extended into a usable system with a React workbench, Spring Boot gateway, FastAPI inference service, task lifecycle management, monitoring, Docker deployment, and smoke checks.

The site will eventually include a personal knowledge-base Q&A Agent. Version one will ship the complete interaction surface with local demonstration answers. The Agent implementation must be replaceable without changing the surrounding pages or visual design, because the Agent technology stack has not yet been selected.

## 2. Product Decisions

### Positioning

The primary positioning is:

> A full-stack developer moving toward AI Agent development.

The copy should show existing engineering ability without presenting Wu Yu as an already-established Agent specialist. The website itself is part of the transition story.

### Homepage direction

Use the personal-introduction layout selected during visual exploration. The first viewport should explain who Wu Yu is and then offer a clear path into the personal knowledge-base conversation.

### Conversation direction

Use recommended questions as the primary entry point while allowing free-form questions. The initial recommended topics are project experience, technical choices, learning direction, and campus experience.

### Content scope

SPMTrack is the only complete project case study in the first version. The medical reimbursement mini-program and the Cangqiong takeaway project will appear as concise cards marked as content being organized. No invented project details or blog articles should be presented as facts.

## 3. Audience and Success Criteria

### Primary audience

- Shenzhen campus-recruiting interviewers and engineers.
- Recruiters who need a fast, credible summary of skills and project scope.
- Technical readers who want to inspect the SPMTrack engineering workflow.

### Version-one success criteria

- A visitor can understand Wu Yu's target direction, current technical foundation, and strongest project within one minute.
- A visitor can reach the SPMTrack case study and understand the system architecture, task workflow, and Wu Yu's responsibilities without opening the original repository.
- A visitor can click a recommended question and receive a useful local demonstration answer.
- The site works on desktop and mobile widths without horizontal overflow or overlapping content.
- The site can be statically deployed without a backend or secret key.
- The content files can later be reused as source documents for a RAG or other knowledge-base implementation.

## 4. Scope

### In scope

- Astro site shell and routing.
- React islands for Agent preview, chat state, mobile navigation, and other stateful interactions.
- Tailwind CSS styling with the approved warm editorial visual direction.
- Homepage, projects index, SPMTrack detail page, lightweight blog page, and about page.
- Markdown or MDX content for profile, projects, experiences, and future posts.
- Resume download link using the supplied resume after it is copied into the site assets.
- Local Agent demo with recommended questions, free-form input, loading state, error state, clear conversation action, and an explicit demo-mode indicator.
- A typed Agent adapter interface that can later call a server endpoint.
- Responsive and keyboard-accessible interaction states.
- Static build and browser-based verification.

### Out of scope for version one

- FastAPI backend implementation.
- LangChain, ChromaDB, vector embeddings, document chunking, or retrieval ranking.
- OpenAI API calls from the browser.
- Authentication, user accounts, persistent conversations, analytics, or multi-user data storage.
- A complete blog archive.
- Detailed content for projects other than SPMTrack.
- A production video inference demo embedded in the portfolio.

## 5. Information Architecture

```text
/
├── /projects
├── /projects/spmtrack
├── /blog
└── /about
```

### Homepage

1. Header with navigation and a persistent Agent entry point.
2. Hero containing the `2026 届 · 深圳` context, the headline `从全栈工程，走向 AI Agent。`, a short capability summary, and actions for SPMTrack and the Agent.
3. Agent preview with welcome message and four recommended questions.
4. Featured work with SPMTrack as the full card and two concise organizing-soon cards.
5. Technical path showing existing engineering experience moving toward Agent learning.
6. Footer with email, GitHub, Shenzhen, and resume download.

### Projects index

Use a readable list or small grid. SPMTrack receives the main visual weight. Other projects remain clearly labeled as incomplete content rather than appearing equally documented.

### SPMTrack detail page

Show the project as a handoff from research code to an interactive software system:

- Project context, dates, and technology list.
- Four-layer architecture: frontend, gateway, inference, and tracking engine.
- Browser flow from video and ROI selection through task creation, queue execution, result rendering, and playback.
- Task state and stage model, including `PENDING`, `RUNNING`, `SUCCESS`, `FAILED`, and `CANCELED`.
- Concrete responsibilities from the resume: React and TypeScript workbench, Canvas ROI selection, Spring Boot API boundary, FastAPI task lifecycle, tracking mode integration, Recharts monitoring, Docker delivery, and smoke checks.
- Engineering reflection on reproducibility, stable boundaries, and user-facing workflow design.
- Link to the original GitHub repository.

### Blog and about pages

Use honest placeholders for missing source material. The pages should make it easy to add Markdown later without changing the route or component architecture.

## 6. Content Model

Use local content files that are independent from page components:

```text
src/content/
├── profile.md
├── projects/
│   ├── spmtrack.md
│   ├── medical-reimbursement.md
│   └── takeout-platform.md
├── experiences/
│   ├── student-union.md
│   └── debate-team.md
└── posts/
    ├── learning-rag.md
    └── project-review.md
```

The exact Astro content-collection schema may use frontmatter fields such as `title`, `slug`, `summary`, `status`, `date`, `tags`, `featured`, and `externalUrl`. The schema must allow an explicit organizing-soon status so incomplete entries are not mistaken for published work.

SPMTrack content should be based on the supplied resume and the repository documentation. The repository confirms the four runtime layers, browser-facing API flow, task state machine, monitoring path, Docker deployment, and reproducible smoke checks. Claims should distinguish Wu Yu's responsibilities from the upstream research implementation.

## 7. Visual and Interaction Design

### Visual direction

Use the selected warm editorial direction:

- Warm paper background rather than a dark dashboard shell.
- Ink-colored text with terracotta as the main emphasis color.
- Serif or editorial display treatment for the main heading, paired with a readable sans-serif body face.
- Thin rules, small metadata labels, and restrained cards.
- No gradients, decorative blobs, oversized marketing hero, or dense nested cards.

Suggested initial tokens:

```text
paper:       #F7F4EE
ink:         #18212B
muted:       #6B6259
terracotta:  #B45C38
line:        #C9C1B5
surface:     #FFFDF9
```

The final implementation may tune these values after browser verification, but the palette should retain contrast and should not become a one-hue interface.

### Agent behavior

- The Agent preview is visible near the top of the homepage.
- Recommended questions are real buttons with stable dimensions and readable text.
- A selected question inserts a user message and then an assistant answer.
- Free-form input is supported in the same component.
- The UI labels local responses as demonstration data.
- Empty, loading, failure, retry, and clear-conversation states are explicit.
- On mobile, recommended questions can scroll horizontally while messages remain in a single column.

## 8. Agent Adapter and Data Flow

The UI must call one module rather than hard-code a provider or framework:

```ts
type AgentMessage = {
  role: "user" | "assistant";
  content: string;
};

type AgentResponse = {
  answer: string;
  sources?: string[];
  mode: "demo" | "remote";
};

async function askKnowledgeBase(
  question: string,
  history: AgentMessage[]
): Promise<AgentResponse>;
```

Version-one flow:

```text
Question button or text input
        -> React chat state
        -> askKnowledgeBase()
        -> local answer map / fallback response
        -> assistant message with demo label
```

Future flow:

```text
Question button or text input
        -> React chat state
        -> askKnowledgeBase()
        -> POST /api/chat
        -> separately deployed FastAPI service
        -> selected retrieval and LLM implementation
        -> answer and optional source labels
```

The browser must never contain an OpenAI-compatible API key. The future remote adapter must handle non-2xx responses, timeouts, and malformed payloads by returning a user-safe error state.

## 9. Error Handling and Accessibility

- Disable send while input is empty or a request is pending.
- Preserve the submitted question if an answer fails so it can be retried.
- Keep the last successful conversation visible after a failed subsequent request.
- Use semantic headings, landmarks, buttons, labels, and keyboard-focusable controls.
- Ensure color is not the only signal for demo mode, status, or errors.
- Respect reduced-motion preferences and keep motion subtle.
- Check text wrapping and minimum control sizes at mobile widths.

## 10. Verification and Delivery

The implementation should include the following checks:

1. Production build completes successfully.
2. TypeScript and Astro content types pass.
3. Every navigation link and the SPMTrack external link resolve.
4. Recommended questions append the expected local answer.
5. Empty, loading, error, retry, and clear states render correctly.
6. Desktop and mobile screenshots show no clipped text, horizontal overflow, or overlapping controls.
7. The site can be served as a static build without environment secrets.

The recommended first deployment is a static host such as Vercel, Netlify, or GitHub Pages. A later Agent backend can be deployed separately while keeping the same frontend contract.

## 11. Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Agent technology decision expands the one-week scope | Ship the UI and typed local adapter first; keep backend out of version one |
| Incomplete project/blog material leads to invented claims | Mark missing entries as organizing soon and use only resume/repository facts |
| A visually attractive page becomes hard for interviewers to scan | Keep metadata labels, short sections, clear project hierarchy, and restrained decoration |
| Future backend changes force a frontend rewrite | Isolate all Agent calls behind `askKnowledgeBase` and typed response data |
| SPMTrack research details overwhelm the portfolio | Present the research context briefly and focus on the delivered workflow and responsibilities |

