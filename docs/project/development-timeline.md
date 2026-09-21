# 个人网站与知识库 Agent 开发时间线

> 时间线只记录能由 Git 提交、合并 PR、评估报告或部署记录支撑的事实。
> Graphify 用于发现跨文档关系；标记为“推断”的关系不会直接写入公开事实。
> 截至：2026-09-21。

## 总览

| 日期 | 阶段 | 当前结果 |
| --- | --- | --- |
| 2026-09-16 | 产品定位与网站设计 | 确定以 SPMTrack 为主案例，网站作为从全栈走向 AI Agent 的求职展示。 |
| 2026-09-17 | 个人网站 MVP | Astro + React + Tailwind 页面和内容集合建立，先使用本地演示回答。 |
| 2026-09-18 | Version 0 Agent | FastAPI、固定 Markdown 资料、OpenAI 兼容模型适配器和 `/api/chat` 完成。 |
| 2026-09-19 | 上游 API 与 Preview | 接入 HeiyuCode Responses API，完成同域 Vercel Preview 适配和线上验收。 |
| 2026-09-19 | RAG V1 | 将固定上下文升级为按标题和段落切片的轻量词法检索。 |
| 2026-09-20 | RAG V1.1 与离线评估 | 用 40 条固定案例建立检索和边界指标，加入证据门和可审计别名。 |
| 2026-09-21 | 本地 RAG V2 | 接入 E5 + ChromaDB，保留词法 fallback；修复短问句召回和 Agent 身份 grounding。 |
| 2026-09-21 | 资料整理 | 使用受控语料运行 Graphify，新增本索引和本时间线；未改变生产逻辑。 |

## 详细记录

### 2026-09-16：确定产品定位和资料边界

- **阶段目标**：在一周内做出能服务求职展示的个人网站，并为后续知识库 Agent 留出替换接口。
- **实现 / 决策**：选择 Astro、React、Tailwind；首版只完整展示 SPMTrack，其他项目标为资料整理中；Agent 先使用本地演示数据，不提前绑定 LangChain、向量库或具体模型供应商。
- **事实依据**：`docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md`；提交 `dfe4967` 的网站实现前置设计。
- **当前状态**：网站定位仍有效；Agent 技术栈已经在后续阶段变为 FastAPI + 轻量 RAG + 本地 RAG V2 实验，原规格中的“尚未选择”属于历史状态。

### 2026-09-17：完成网站 MVP

- **阶段目标**：先把个人介绍、项目、博客、关于页和 Agent 入口做出来，确保内容与交互可独立替换。
- **实现内容**：Astro 页面、React Agent 预览、内容集合、响应式布局、简历下载和本地演示回答。
- **验证证据**：提交 `dfe4967`；后续 README 仍将 Astro 7、React 19、Tailwind 4、Vitest 列为前端基线。
- **当前状态**：网站框架已稳定，后续主要工作集中在 Agent 后端、资料质量和博客整理。

### 2026-09-18：完成 Version 0 固定资料问答

- **阶段目标**：建立可运行的最小后端，不把 Agent、RAG 和模型供应商细节耦合到前端。
- **实现内容**：FastAPI `/api/chat`、Pydantic 请求校验、两份 Markdown 知识资料、OpenAI 兼容模型适配器、历史消息边界、超时和稳定错误映射。
- **调试记录**：Python 3.9 不支持 `str | None` 语法，配置模块启动失败；修正为兼容当前运行时的类型写法后才能启动。之后模型配置错误表现为 502/503，需要区分缺少配置、上游失败和超时。
- **验证证据**：提交序列 `e571332`、`93a7338`、`e8302f5`、`3a268bd`、`45ab094`、`8da2e19`；合并提交 `fdc0b70`。
- **当前状态**：Version 0 的固定上下文路线已被 RAG V1 替代，但其 API 契约、错误边界和历史限制仍是基础。

### 2026-09-19：适配 HeiyuCode Responses API

- **阶段目标**：让中转站的 Codex 分组能够通过 Responses API 工作，同时保持模型 Key 只在后端。
- **实现内容**：切换到支持 Responses API 的 SDK / 调用协议，增加模型客户端清理，放宽能覆盖约 52 秒真实响应的请求链路，并保留 502/503 稳定公共错误。
- **遇到的问题与根因**：原先按 Chat Completions 的调用方式不能直接兼容中转站的 Responses API；过短的上游或浏览器超时也会把慢响应误判为失败。
- **验证证据**：提交 `df291ed`、`c0e6ff7`、`d47f853`；合并提交 `7be23a7`；博客草稿记录了约 52.57 秒的真实耗时观察。
- **当前状态**：Responses API 配置已成为线上 Preview 的历史兼容方案，密钥仍不进入前端或仓库。

### 2026-09-19：完成同域 Vercel Preview

- **阶段目标**：在 0 成本约束下验证浏览器、Vercel Python Function、FastAPI 和中转站的完整链路，但不提升 Production。
- **实现内容**：复用 FastAPI app，增加 `api/index.py`、`api/[...path].py`、`vercel.json`，让前端请求同域 `/api/chat`；显式打包 `backend/app/**` 和 `knowledge/**`；增加脱敏日志与健康检查。
- **部署问题**：首次 `includeFiles` 类型不符合 Vercel schema；修正后，根目录依赖文件的 `-r` 递归引用又导致构建失败；改为直接依赖列表后构建成功。
- **验证证据**：提交 `d7bf74d`、`6b932d0`、`0b36b31`、`ef3f818`、`dc15f6d`、`9715b33`、`8c2b8f7`；线上 Preview 状态为 Ready，健康检查和 `/api/chat` 已验证。
- **当前状态**：Preview-only；Production 未提升。浏览器视觉验收、Function 时长观察和供应商额度上限仍是正式公开前的门槛。

### 2026-09-19：RAG V1 轻量词法检索

- **阶段目标**：让模型只看到命中的个人资料片段，并返回实际来源，而不是每次把全部固定上下文放入 Prompt。
- **实现内容**：按标题和段落切分 Markdown，增加 `KnowledgeChunk`、来源列表、无命中短路和检索结果注入；未知问题不调用模型。
- **验证证据**：设计与计划文件 `2026-09-19-agent-v1-retrieval-*`；提交 `ea907f3`、`ca2b167`、`7bb7c3a`；Preview 验收记录 `199ca44`、`260340d`。
- **当前状态**：线上 Preview 的基本检索路线，后续由 V1.1 加固边界。

### 2026-09-19：Preview 公开前防护

- **阶段目标**：在不引入付费数据库或常驻服务的情况下，减少重复请求对模型额度的风险。
- **实现内容**：应用层保留消息长度和历史条数限制；Vercel Preview 使用每 IP 每 60 秒 10 次的 Firewall 规则；429 与模型失败分开；未知问题用不调用模型的请求验收限流。
- **验证证据**：提交 `1dea125`、`fdd639c`、`2652785`；设计和计划文件 `2026-09-19-agent-public-protection-*`。
- **当前状态**：规则只作用于 Preview，按区域计数，不被描述为严格的全局费用控制；Production 仍未启用。

### 2026-09-20：Version 0 离线评估与 RAG V1.1

- **阶段目标**：把“回答得像”变成可重复的检索和边界指标，不用真实模型调用阻塞迭代。
- **实现内容**：建立 40 条脱敏评估案例和 Fake Provider，使用真实 FastAPI 请求路径统计来源命中、关键事实覆盖、资料外拒答和模型调用次数；随后增加双层门控、证据门和可审计别名。
- **结果**：Version 0 暴露出“已知实体词出现就误命中”的问题；V1.1 在固定 40 条案例上把资料外 / 对抗正确拒答率提升到 1.0，错误检索率降到 0，同时保留已知事实的来源命中。
- **验证证据**：提交 `4905aec`、`8eab151`、`68fdfd9`、`dbe8ead`；提交 `dc55fd8`、`1d5ac0b`、`6cdabb3`、`0a77c0c`；报告见 `docs/evals/version-0-baseline.md` 与 `docs/evals/version-1-1-retrieval-hardening.md`。
- **当前状态**：V1.1 是线上 Preview 的检索边界；自动字符串指标不等于语义回答质量，资料扩充后需要重跑评估。

### 2026-09-21：Embedding + ChromaDB 离线 Spike

- **阶段目标**：判断向量检索是否值得进入个人项目的本地学习路线，同时不影响线上 V1.1。
- **实现内容**：在临时 Python 3.11 环境比较 MiniLM、E5 和词法基线，记录召回、边界拒答、延迟、模型加载和依赖体积。
- **结果**：零错误阈值下 E5 的来源命中率只有 0.5217；较高阈值虽然提高召回，却出现 0.0250 错误率。结论是暂不把向量检索替换线上方案。
- **验证证据**：`docs/evals/embedding-chroma-spike.md`；合并提交 `9a457ed`。
- **当前状态**：保留为本地对照实验和求职学习材料。

### 2026-09-21：本地 RAG V2

- **阶段目标**：在本地形成可运行、可解释的 E5 + ChromaDB 项目经验，响应求职 JD 对 RAG / 向量数据库的要求。
- **实现内容**：使用 `intfloat/multilingual-e5-small`、`passage:` / `query:` 前缀、归一化向量、ChromaDB PersistentClient、`wu_yu_knowledge_v2` collection、top-k 4、最大距离 0.096；向量异常回退词法检索，正常无命中保持拒答。
- **遇到的问题与根因**：严格阈值会漏掉短问题；盲目放宽阈值会破坏资料外拒答。因此增加 hybrid lexical fallback，而不是直接放宽准入。模型还曾在个人资料问题上回答“我是 Codex”，最后通过 prompt grounding 明确助手身份为吴禹的个人知识库助手。
- **验证证据**：提交 `f73e37c`、`d812e85`、`fe2b1f8`、`d1d7eee`、`b858197`、`ea1d5f4`、`d495866`、`eabbf30`；合并提交 `ede1a0c`；`docs/evals/rag-v2-local.md` 记录 8 条本地人工验收。
- **当前状态**：仅本地运行；索引在被 Git 忽略的 `backend/data/chroma/`，没有部署到线上，也不代表通用语义正确率。

### 2026-09-21：Graphify 资料整理

- **阶段目标**：把规格、计划、评估、博客和知识库放到同一张关系图中，帮助后续写时间线和补资料。
- **处理范围**：受控语料 38 个 Markdown 文件、约 29,701 个词；不包含代码，不包含密钥、`.env`、模型缓存或 ChromaDB 数据。
- **结果**：生成 143 个节点、140 条边、10 个超边、22 个社区；最明显的主题桥接是 SPMTrack 作品集证明、Preview 请求链路、RAG 评估与本地向量检索。
- **可信度边界**：Graphify 的 EXTRACTED 关系可回查原文；INFERRED / AMBIGUOUS 关系只列为待核对线索。输出保存在 `/Users/Admin/.codex/graphify/portfolio-development.jt6bmk/graphify-out/`，不进入仓库。
- **当前状态**：本次只新增整理文档，不改变网站、后端、Vercel 或 GitHub 远程仓库。

## 调试问题清单（待扩写为博客）

| 问题 | 根因 | 已采取的决策 | 证据 |
| --- | --- | --- | --- |
| Python 3.9 启动时报 `unsupported operand type(s) for |` | 使用了 Python 3.10 才支持的联合类型语法 | 改为兼容当前运行时的类型声明，并在 README 标注后端 Python 版本 | 2026-09-18 提交序列、启动日志摘要 |
| `/api/chat` 出现 502 | 中转站调用协议、SDK 能力或超时边界与实际服务不一致 | 切换 Responses API，统一稳定错误，分别处理 503 配置缺失与 502 上游失败 | `df291ed`、`c0e6ff7`、`d47f853` |
| Preview 首次构建失败 | `includeFiles` schema 和根依赖的递归引用不符合 Vercel 构建器 | 改用 brace glob 和直接依赖清单，复用 FastAPI 入口 | `ef3f818`、`dc15f6d`、`9715b33` |
| 短问句向量距离超过 0.096 | 当前阈值优先保证资料外零误命中 | 在 hybrid 模式下对向量异常或短问句回退词法，不直接放宽阈值 | `d495866`、`docs/evals/rag-v2-local.md` |
| Agent 把自己说成 Codex | Prompt 没有明确助手身份，模型受通用系统身份影响 | 在 grounding 中固定“吴禹的个人知识库助手”身份，并保持回答基于资料 | `eabbf30`、`docs/evals/rag-v2-local.md` |

## 当前边界与下一阶段入口

- **当前可公开描述**：个人网站、SPMTrack 工程案例、FastAPI 知识库问答、线上 Preview 的 RAG V1.1、以及本地 E5 + ChromaDB RAG V2 学习验证。
- **当前不可公开描述**：线上已部署 ChromaDB、已使用 LangChain / LangGraph / MCP、多 Agent 协作、通用语义准确率或 Production 已开放。
- **资料整理后的下一步**：先由本人审核和扩充个人资料，再扩充评估案例并重建索引；之后才决定是否继续 Agent 技术开发或线上升级。
