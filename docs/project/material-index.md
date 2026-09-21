# 项目资料索引

> 整理范围：个人网站、个人知识库 Agent、RAG 评估与部署记录。
> 更新日期：2026-09-21
> 维护原则：先保留历史资料，再用状态标记可信度和用途；不删除旧规格，不把推断写成事实。

## 1. 状态定义

| 状态 | 含义 |
| --- | --- |
| 权威资料 | 已由简历、项目仓库、已合并代码或可复现结果支撑，可作为网站和 Agent 知识库来源。 |
| 历史设计 | 某个阶段的设计决策，保留用于解释为什么这样做，不代表当前运行状态。 |
| 实施计划 | 当时准备执行的步骤，完成情况以提交、评估或后续记录为准。 |
| 验证报告 | 记录实际运行、测试或线上检查结果；需要同时阅读范围和限制。 |
| 博客草稿 | 面向访客的叙述材料，必须在发布前回查原始证据。 |
| 待审核 | 内容存在，但尚未由本人确认、补充或脱敏；暂不作为公开回答的唯一依据。 |
| 已过期 | 被后续实现替代，只保留历史追溯价值，不应指导当前开发。 |

## 2. 资料总览

### 2.1 产品与个人定位

| 文件 | 类型 | 状态 | 用途与备注 |
| --- | --- | --- | --- |
| `README.md` | 项目说明 | 权威资料 | 当前技术栈、本地启动方式、线上 Preview 与本地 RAG V2 的边界。 |
| `docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md` | 产品规格 | 历史设计 | 定义“全栈开发走向 AI Agent”、SPMTrack 主证明项目和网站信息架构。 |
| `docs/superpowers/plans/2026-09-16-personal-portfolio-agent-plan.md` | 实施计划 | 实施计划 | 记录 Astro、React、Tailwind 网站的分阶段实现任务。 |
| `src/content/profile.md` | 个人资料 | 权威资料 | 学校、毕业年份、目标方向和技术基础；扩充前需本人复核。 |
| `public/resume/wu-yu-resume.pdf` | 简历 | 权威资料 | 求职事实的首要来源；网站文案不得超出简历和项目证据。 |

### 2.2 项目与经历内容

| 文件 | 类型 | 状态 | 用途与备注 |
| --- | --- | --- | --- |
| `src/content/projects/spmtrack.md` | 项目案例 | 权威资料 | 当前最完整案例；描述 React 工作台、Spring Boot 网关、FastAPI 任务服务和跟踪引擎。 |
| `knowledge/spmtrack.md` | Agent 知识资料 | 权威资料 | 面向问答的压缩版 SPMTrack 事实，需与项目案例同步审核。 |
| `src/content/projects/medical-reimbursement.md` | 项目卡片 | 待审核 | 仅有已确认的前端参与范围，细节不足时不扩写。 |
| `src/content/projects/takeout-platform.md` | 项目卡片 | 待审核 | 仅保留已确认的 Vue3、Spring Boot、MySQL 等范围。 |
| `src/content/experiences/debate-team.md` | 校园经历 | 权威资料 | 辩论队职务、训练和名次，发布前核对时间与表述。 |
| `src/content/experiences/student-union.md` | 校园经历 | 权威资料 | 学生会工作范围和活动支持，避免夸大职责。 |
| `docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md` | 内容约束 | 历史设计 | 明确除 SPMTrack 外其他项目首版只能标记为资料整理中。 |

### 2.3 Agent 与 RAG 规格、计划

| 文件 | 类型 | 状态 | 用途与备注 |
| --- | --- | --- | --- |
| `docs/superpowers/plans/2026-09-18-version-0-personal-agent-plan.md` | Version 0 计划 | 已过期 | 固定上下文问答的原始实施路线；仍用于解释最小可用版本。 |
| `docs/superpowers/specs/2026-09-19-agent-v1-retrieval-design.md` | RAG V1 规格 | 历史设计 | 从固定上下文升级到 Markdown 片段和轻量词法检索。 |
| `docs/superpowers/plans/2026-09-19-agent-v1-retrieval-plan.md` | RAG V1 计划 | 实施计划 | 对应 V1 检索实现和 API 接入。 |
| `docs/superpowers/specs/2026-09-20-agent-v1-1-retrieval-hardening-design.md` | RAG V1.1 规格 | 历史设计 | 双层门控、可审计别名和证据门，解决误命中边界。 |
| `docs/superpowers/plans/2026-09-20-agent-v1-1-retrieval-hardening-plan.md` | RAG V1.1 计划 | 实施计划 | 对应固定评测集上的检索边界加固。 |
| `docs/superpowers/specs/2026-09-21-rag-v2-local-design.md` | RAG V2 规格 | 历史设计 | 本地 E5、ChromaDB、混合回退和索引命令的设计依据。 |
| `docs/superpowers/plans/2026-09-21-rag-v2-local-plan.md` | RAG V2 计划 | 实施计划 | 本地向量检索的五个实施任务；不代表线上已部署。 |

### 2.4 评估与实验记录

| 文件 | 类型 | 状态 | 用途与备注 |
| --- | --- | --- | --- |
| `docs/superpowers/specs/2026-09-20-version-0-evaluation-design.md` | 评估规格 | 历史设计 | 定义 Fake Provider、40 条案例和脱敏指标。 |
| `docs/superpowers/plans/2026-09-20-version-0-evaluation-plan.md` | 评估计划 | 实施计划 | 评估案例、运行器和报告生成步骤。 |
| `backend/evals/cases.json` | 评估输入 | 权威资料 | 当前版本的事实、改写、资料外和对抗案例；新增资料后需要扩充。 |
| `docs/evals/version-0-baseline.md` | 评估报告 | 验证报告 | Version 0 和 V1.1 的固定数据集对比，包含指标口径与限制。 |
| `docs/evals/version-1-1-retrieval-hardening.md` | 评估报告 | 验证报告 | 记录 V1.1 的来源命中、边界拒答和错误率结果。 |
| `docs/evals/embedding-chroma-spike.md` | 离线实验 | 验证报告 | 比较词法、MiniLM 和 E5；结论是不替换线上 V1.1。 |
| `docs/evals/rag-v2-local.md` | 本地验证 | 验证报告 | 记录 E5 + ChromaDB 本地 8 条人工验收、fallback 和限制。 |

### 2.5 Preview 部署与安全

| 文件 | 类型 | 状态 | 用途与备注 |
| --- | --- | --- | --- |
| `docs/superpowers/specs/2026-09-19-online-preview-closure-design.md` | 部署规格 | 历史设计 | 同项目同域 Preview、FastAPI Function、HeiyuCode Responses API。 |
| `docs/superpowers/plans/2026-09-19-online-preview-closure-plan.md` | 部署计划 | 实施计划 | 线上 Preview 适配、环境变量、日志和验收步骤。 |
| `docs/superpowers/specs/2026-09-19-agent-public-protection-design.md` | 防护规格 | 历史设计 | Preview-only Firewall 限流和中转站额度边界。 |
| `docs/superpowers/plans/2026-09-19-agent-public-protection-plan.md` | 防护计划 | 实施计划 | 应用与 Vercel 防护的分阶段实施。 |
| `src/content/posts/online-preview-deployment.md` | 博客草稿 | 博客草稿 | 已记录部署失败、Preview 验收、限流和本地 RAG V2；上线前需补浏览器证据。 |
| `api/index.py`, `api/[...path].py`, `vercel.json` | 部署入口 | 权威资料 | 当前 Preview 适配实现；生产环境仍保持未提升。 |

### 2.6 博客与公开内容

| 文件 | 类型 | 状态 | 用途与备注 |
| --- | --- | --- | --- |
| `src/content/posts/version-0-evaluation-baseline.md` | 技术文章 | 权威资料 | 已发布，叙述 Version 0 到 RAG V1.1 的检索边界和评估。 |
| `src/content/posts/learning-rag.md` | 博客草稿 | 博客草稿 | 只有学习方向和主题，尚未补充过程事实。 |
| `src/content/posts/project-review.md` | 博客草稿 | 博客草稿 | SPMTrack 复盘占位稿，不与 Agent 开发时间线混写。 |

### 2.7 主工作区待纳入资料

以下文件当前仍是主工作区的未跟踪变更，已被 Graphify 复制到受控语料，但本分支没有擅自吸收。它们需要单独确认后再提交：

| 文件 | 当前状态 | 后续动作 |
| --- | --- | --- |
| `docs/superpowers/plans/2026-09-19-online-preview-closure-plan.md` | 待审核 | 与已跟踪版本比对，确认是否为最新草稿。 |
| `docs/superpowers/plans/2026-09-21-preview-content-evaluation-plan.md` | 待审核 | 确认 Preview 内容评估是否已完成，补充结果后再归档。 |
| `docs/superpowers/specs/2026-09-19-online-preview-closure-design.md` | 待审核 | 与分支内同名规格比对，避免两份来源漂移。 |
| `src/content/posts/online-preview-deployment.md` | 待审核 | 与分支内博客草稿比对，保留已验证的脱敏记录。 |

## 3. 资料使用规则

1. Agent 知识库优先使用 `knowledge/`、已审核的 `src/content/` 和评估报告中的聚合事实；计划文件只用于解释过程，不直接作为个人事实来源。
2. `SPMTrack` 的职责描述必须区分本人负责的工程封装与上游研究代码，不能把算法作者身份写成个人经历。
3. `RAG V1.1` 是当前线上 Preview 的能力边界；`E5 + ChromaDB` 目前是本地 RAG V2，不能写成线上向量数据库已部署。
4. Graphify 的 `INFERRED` 和 `AMBIGUOUS` 关系只用于发现待核对主题，公开文案必须回查原始文件或 Git 提交。
5. 任何包含 API Key、请求头、完整模型回答、供应商原始异常、向量值或本地缓存的数据都不得进入网站、博客或公开仓库。

## 4. 下一轮整理顺序

1. 本人审核 `profile.md`、`knowledge/profile.md`、`knowledge/spmtrack.md` 和三份项目资料，补齐可公开的事实边界。
2. 将已验证的调试过程拆成博客草稿：Python 3.9 类型语法、502/Responses API、Preview 打包、RAG V1.1 证据门、RAG V2 阈值与 fallback、Agent 身份 grounding。
3. 扩充 `backend/evals/cases.json`，为每个新增资料主题补充事实、同义改写和资料外问题，再重建本地索引。
4. 资料审核和评测稳定后，再决定是否更新线上 Preview；当前不把本地 RAG V2 直接提升到 Production。
