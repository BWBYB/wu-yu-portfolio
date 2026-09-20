# Version 0 个人知识库 Agent 离线评测设计

## 1. 背景与目标

Version 0 已经具备固定 Markdown 资料、轻量关键词检索、命中后调用模型和无命中确定性短路。当前缺少可重复的能力基线，因此无法用证据判断资料覆盖、来源选择和后续 RAG 升级是否真正改善了系统。

本阶段建立一个不消耗模型额度的离线评测：复用真实 FastAPI `/api/chat` 请求路径和真实检索逻辑，使用只存在于评测代码中的 Fake Model Provider 替代真实模型。评测输出机器可读结果和人工可读报告，为后续 Embedding、工具调用或 Agentic RAG 提供版本对照。

## 2. 范围与约束

### 2.1 包含

- 固定、版本化的评测案例集，覆盖事实、项目、同义改写、资料外和对抗问题。
- 一条命令可重复运行的 Python 评测入口。
- 真实 API 校验、资料加载、片段切分、检索和无命中短路的离线验证。
- Fake Provider 调用计数和稳定回答，以验证模型调用边界。
- 每题结果 JSON、指标摘要 Markdown 和网站博客草稿。

### 2.2 不包含

- 不调用真实 OpenAI-compatible Provider、中转站或 Vercel Preview。
- 不接入 LangChain、LangGraph、MCP、ChromaDB、Milvus、Embedding 或多 Agent。
- 不扩充 `knowledge/` 个人资料，不改变 `/api/chat` 请求或响应契约。
- 不修改 Vercel Firewall、环境变量、Production 或前端页面。
- 不把关键词命中或 `required_facts` 命中描述成完整的语义正确率。

## 3. 当前系统边界

离线评测必须通过现有 FastAPI 应用的 `/api/chat` 路径，而不是复制一套检索逻辑。请求仍遵守现有校验：消息长度、历史条数和 Pydantic schema 均由 API 处理。

对于命中资料的案例，测试注入 `backend.app.main.generate_answer`，Fake Provider 记录一次调用并从传入的上下文生成稳定文本。对于资料外案例，真实 `retrieve_chunks` 返回空元组，API 应在调用模型前返回固定未知回答；Fake Provider 若被调用则该案例失败。

评测注入只发生在评测进程中，不新增线上依赖，也不改变 `backend/app/llm.py` 的生产行为。

## 4. 评测案例模型

案例文件：`backend/evals/cases.json`。

第一版至少 24 条，目标约 28 条，使用以下类别：

- `profile_fact`：个人信息、教育背景、技术栈和求职方向。
- `project_fact`：SPMTrack 架构、工作流、技术组成和个人职责。
- `paraphrase`：不改变事实的同义或改写问法。
- `out_of_scope`：当前两份资料没有覆盖的问题。
- `adversarial`：要求编造、忽略资料边界、提示词注入或越权读取文件的请求。

每个案例使用以下字段：

```json
{
  "id": "spmtrack-001",
  "question": "SPMTrack 主要解决什么问题？",
  "category": "project_fact",
  "expected_sources": ["SPMTrack 项目资料"],
  "required_facts": ["视觉跟踪", "视频"],
  "should_answer": true,
  "expected_model_call": true
}
```

资料外或无命中案例示例：

```json
{
  "id": "boundary-001",
  "question": "吴禹最喜欢什么颜色？",
  "category": "out_of_scope",
  "expected_sources": [],
  "required_facts": [],
  "should_answer": false,
  "expected_model_call": false
}
```

字段约定：

- `id` 在文件内唯一，只用于结果关联和报告定位。
- `expected_sources` 是检索来源期望，不代表回答一定正确。
- `required_facts` 是可解释的字符串代理检查，允许为空。
- `should_answer` 表示资料是否足以支持回答；它不自动判断模型语言质量。
- `expected_model_call` 表示 API 是否应进入模型适配器。

案例不得包含真实 API Key、访问者信息、完整供应商错误或需要写入文件的动作。

## 5. 运行器与结果

运行器文件：`backend/evals/runner.py`；测试文件：`backend/evals/test_runner.py`；包标记：`backend/evals/__init__.py`。

运行器通过 FastAPI `TestClient` 调用应用。每条案例开始前重置 Fake Provider 的调用记录，并记录：

```json
{
  "id": "spmtrack-001",
  "category": "project_fact",
  "expected_model_call": true,
  "status_code": 200,
  "actual_sources": ["SPMTrack 项目资料"],
  "retrieved_chunks": 2,
  "model_call_count": 1,
  "latency_ms": 1.8,
  "source_hit": true,
  "required_facts_hit": ["视觉跟踪", "视频"],
  "required_facts_missing": [],
  "boundary_correct": null,
  "retrieval_error": false,
  "error": null
}
```

实现可以从 API 响应和 Fake Provider 计数获得公开结果。为获得 `retrieved_chunks`，评测注入应使用最小、可测试的观察边界；优先读取请求状态或增加评测专用的非生产观察回调，不向 API 响应增加字段。如果无需修改生产代码即可通过 Fake Provider 和现有响应完成指标，则不得为了评测而改动 `backend/app/main.py`。

运行命令：

```bash
PYTHONPATH=backend python backend/evals/runner.py
```

默认输出到本地 `artifacts/evals/version-0-results.json` 和 `docs/evals/version-0-baseline.md`。机器生成的 `artifacts/` 不提交；人工整理后的工程报告可以提交。评测运行器不打印问题全文、回答全文、密钥、请求头或供应商原始异常。

## 6. 指标定义

报告至少包含总题数、分类题数、HTTP 成功率、平均响应时间和 P95 响应时间，并计算以下边界清晰的指标：

- **期望来源命中率**：`actual_sources` 包含全部 `expected_sources` 的案例比例，仅适用于有期望来源的案例。
- **关键事实覆盖率**：实际可观察文本中命中的 `required_facts` 数除以非空 required facts 总数；这是字符串代理指标，不是语义评估。
- **资料外正确拒答率**：`should_answer=false` 且没有来源、模型未调用、返回 200 固定边界回答的案例比例。
- **无命中模型短路率**：`expected_model_call=false` 且 Fake Provider 调用次数为 0、没有来源的案例比例。
- **错误检索率**：实际来源与期望来源不相交，或资料外问题出现非空来源的案例比例。

P95 使用排序后的离线耗时列表，索引取 `ceil(0.95 * n) - 1` 并限制在合法范围内。没有足够样本时报告实际样本数，不伪造稳定性结论。

真实模型回答的自然度、事实完整性、提示词注入抵抗力和答案是否真正满足问题，不纳入自动指标；这些内容在报告中列为人工复核项。

## 7. 报告与博客产物

工程报告：`docs/evals/version-0-baseline.md`。

网站博客草稿：`src/content/posts/version-0-evaluation-baseline.md`。

两份文档应记录：

- 为什么先建立基线再选择 Embedding 或 Agent 框架。
- 案例分类和指标定义。
- 当前轻量检索的有效范围、同义改写失败和误命中。
- 无命中不调用模型的成本边界。
- 自动评测与人工复核的区别。
- 下一步选择 RAG V1、Function Calling 或补充资料的判断依据。

文档只能记录聚合指标、案例 ID 和脱敏的技术结论，不记录 API Key、IP、OIDC token、完整问题正文、完整回答或供应商原始响应。

## 8. 验收标准

- 案例不少于 24 条，五类问题均有覆盖且 ID 唯一。
- `PYTHONPATH=backend python backend/evals/runner.py` 可重复运行，不需要网络或真实 API Key。
- 结果 JSON 可被程序读取，Markdown 报告包含定义和实际结果。
- 至少一个有命中案例验证 Fake Provider 被调用，至少一个无命中案例验证 Fake Provider 未被调用。
- 失败案例能通过案例 ID 和明确原因定位。
- 后端完整测试、前端测试、Astro check、Astro build 和 `git diff --check` 不回归。
- 评测和博客明确说明自动指标的局限，不宣称已完成语义质量评估。
- Production、Vercel Firewall、前端聊天契约和知识资料保持不变。
