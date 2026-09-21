# RAG V2 本地向量检索设计

## 状态

方案 A 已获用户批准：先在本地完成真实 Embedding + ChromaDB 链路，稳定后再评估线上适配。本规格只定义本地开发和验证范围，不承诺本阶段部署到 Vercel 或 Production。

## 背景

个人网站当前已经有 RAG V1.1：Markdown 文档分块、可解释的词法检索、来源返回、无命中短路和提示词边界。离线评测证明它适合当前小语料，但用户希望通过一个真实的向量化 RAG 项目展示 Embedding 和向量数据库经验。

本阶段的目标不是证明向量检索一定比词法检索更好，而是在本地完成一条可运行、可解释、可复现的技术链路：资料切分 -> 本地 Embedding -> ChromaDB 持久化 -> 查询向量化 -> Top-K 检索 -> LLM 回答。资料外问题仍必须受到边界控制，向量检索不可用时仍能回退到 V1.1 词法检索。

## 目标

1. 使用 `intfloat/multilingual-e5-small` 在本地生成知识片段和查询向量。
2. 使用本地持久化 ChromaDB 保存当前两份知识文档的向量和元数据。
3. 通过明确的 `top_k` 和相似度阈值选择上下文。
4. 保留 V1.1 词法检索作为 Embedding/ChromaDB 失败时的 fallback。
5. 保持现有 `POST /api/chat` 请求和响应契约，前端不需要知道检索实现细节。
6. 提供可重复的索引构建命令，资料更新后可以安全重建而不产生重复记录。
7. 用精简的本地测试和人工冒烟验证证明链路可用，暂不接入线上环境。

## 非目标

- 不修改 Vercel Preview、Production、Firewall 或线上环境变量。
- 不把本地 ChromaDB 目录、模型缓存或真实 `.env` 提交到公开仓库。
- 不引入 LangChain、LangGraph、MCP、多 Agent 或 Agentic RAG 编排。
- 不修改 `knowledge/profile.md`、`knowledge/spmtrack.md` 的资料正文。
- 不实现用户上传资料、后台管理、在线增量索引或多租户隔离。
- 不把本地持久化 ChromaDB 描述为已经上线的云端向量数据库。
- 不追求大规模压测、100% 测试覆盖率或企业级容灾。

## 方案选择

### 采用：本地 Embedding + 本地持久化 ChromaDB + 远程 LLM

```text
Markdown knowledge files
  -> existing build_chunks()
  -> local E5 embedding model
  -> PersistentClient(path=backend/data/chroma)
  -> query embedding
  -> ChromaDB top-k + distance threshold
  -> build grounded prompt
  -> existing OpenAI-compatible LLM
  -> answer + sources
```

Embedding 模型只在本地运行；回答生成继续使用现有 OpenAI-compatible 中转站。这样可以真实展示向量化 RAG，同时避免当前阶段把本地 PyTorch 模型部署到 Serverless。

### 暂不采用：远程 Embedding

中转站是否支持 `/v1/embeddings` 还没有作为本地实现的前置条件。先使用已验证可下载的本地模型，后续线上适配时再抽象 Embedding Provider。

### 暂不采用：仅预计算向量和手写余弦检索

该方案部署更轻，但运行时没有 ChromaDB，不能完整展示本阶段希望掌握的向量数据库使用方式。

## 组件边界

### `backend/app/embeddings.py`

职责：加载本地 Sentence Transformers 模型，并提供批量文档编码和单条查询编码。

约束：

- 文档文本使用 `passage: ` 前缀。
- 查询文本使用 `query: ` 前缀。
- Embedding 输出使用归一化向量；ChromaDB collection 使用 cosine distance。
- 模型名称由配置读取，默认 `intfloat/multilingual-e5-small`。
- 模型在进程内懒加载并缓存。
- 加载或编码错误转换为稳定的内部异常，不向 API 返回模型堆栈。

### `backend/app/vector_store.py`

职责：管理本地 ChromaDB collection、索引重建和查询结果转换。

约束：

- 使用 `PersistentClient`，目录默认为 `backend/data/chroma`。
- collection 名称固定且版本化，例如 `wu_yu_knowledge_v2`。
- collection 空间固定为 cosine，避免不同默认距离度量造成阈值失效。
- 每条记录使用 `KnowledgeChunk.chunk_id` 作为唯一 ID。
- metadata 至少包含 `source` 和 `heading`。
- 重建索引前删除本版本 collection，再批量写入当前 chunks，保证幂等。
- 查询返回 `KnowledgeChunk`，不得让 `main.py` 依赖 ChromaDB 返回结构。
- 查询只返回 `top_k` 条，距离超过阈值的结果被过滤。

### `backend/app/retrieval.py`

职责：保留现有词法检索，并增加一个统一的检索选择层。

建议接口：

```python
async def retrieve_relevant_chunks(
    question: str,
    chunks: tuple[KnowledgeChunk, ...],
    settings: Settings,
) -> RetrievalResult
```

`RetrievalResult` 至少包含：

- `chunks: tuple[KnowledgeChunk, ...]`
- `mode: Literal["vector", "lexical", "none"]`
- `fallback_used: bool`

选择规则：

1. 先使用当前词法阻断规则识别明确的编造、提示词泄露和文件越权请求。
2. 向量检索成功且有结果时使用向量结果。
3. 向量模型、ChromaDB 或索引不可用时回退 `retrieve_chunks()`。
4. 向量和词法都没有结果时返回空结果，由现有 API 短路且不调用 LLM。
5. 不因为向量相似度高就绕过现有资料边界。

### `backend/app/index_knowledge.py`

职责：提供可重复运行的索引构建入口。

命令接口：

```bash
cd backend
.venv/bin/python -m app.index_knowledge
```

命令读取当前知识文档、调用本地 Embedding、重建 ChromaDB collection，并输出脱敏的片段数量、模型名和索引路径，不输出原文、向量值或密钥。

### `backend/app/config.py`

新增配置项：

```dotenv
RAG_RETRIEVAL=vector
EMBEDDING_MODEL=intfloat/multilingual-e5-small
CHROMA_PATH=data/chroma
VECTOR_COLLECTION=wu_yu_knowledge_v2
VECTOR_TOP_K=4
VECTOR_MAX_DISTANCE=0.096
EMBEDDING_TIMEOUT_SECONDS=30
```

`RAG_RETRIEVAL` 支持 `vector`、`lexical` 和 `hybrid`。本地默认使用 `vector`，测试可以显式使用 `lexical`。`hybrid` 表示向量优先、失败时词法回退，而不是两个结果无条件合并。

## API 与日志行为

`POST /api/chat` 的请求字段和响应字段保持不变：

```json
{
  "answer": "...",
  "sources": ["个人资料"],
  "mode": "remote"
}
```

`mode` 继续表示回答使用远程 LLM，不新增前端必须处理的模式值。后端脱敏日志新增或复用以下字段：

- `retrieval_mode`
- `retrieved_chunks`
- `retrieved_sources_count`
- `fallback_used`
- `duration_ms`
- `error_category`

日志不得包含完整问题、回答、API Key、原文片段、Embedding 向量或供应商错误正文。

## 错误与降级

| 场景 | 行为 |
| --- | --- |
| ChromaDB 目录不存在 | 自动创建；首次请求或显式索引命令建立索引 |
| 索引为空或版本不匹配 | 尝试本地重建；失败则回退词法检索 |
| Embedding 模型加载失败 | 回退词法检索并记录 `embedding_unavailable` |
| 向量查询失败 | 回退词法检索并记录 `vector_store_unavailable` |
| 两种检索均无结果 | 返回固定知识边界回答，不调用 LLM |
| LLM 配置缺失 | 保持现有 503 |
| LLM 上游失败或超时 | 保持现有 502 |

向量组件的异常不应让已有本地词法问答整体不可用。

## 数据和安全边界

- ChromaDB 目录加入 `.gitignore`，只提交目录说明或空目录占位文件（如确有需要）。
- 本地模型缓存放在仓库外或用户缓存目录。
- 向量是由个人资料派生的数据，不上传到公共仓库或第三方存储。
- 知识源仍然只有已审核的 `profile.md` 和 `spmtrack.md`。
- 资料外问题不通过向量相似度强行生成答案。
- 前端永远不接触 Embedding Key、LLM Key 或 ChromaDB 路径。

## 测试策略

只保留个人项目所需的最小证据集：

### 单元测试

- E5 文档/查询前缀和批量编码调用参数正确。
- ChromaDB 记录包含稳定 ID、source 和 heading。
- 同一份 chunks 重建索引不会产生重复记录。
- 查询结果正确映射回 `KnowledgeChunk`。
- 超过距离阈值的结果被过滤。
- 向量异常触发词法 fallback。

### API 回归测试

- 正常事实问题返回正确来源。
- 资料外问题返回空来源且不调用 LLM。
- 明确对抗问题继续被词法边界拦截。
- Embedding/ChromaDB 故障时仍返回词法结果。
- 日志只保留聚合元数据。
- `/health` 和 `/api/health` 保持 200。

### 本地验收

```bash
cd backend
.venv/bin/python -m app.index_knowledge
.venv/bin/python -m pytest -q
cd ..
npm test
npm run check
npm run build
git diff --check
```

至少人工验证 8 条问题：4 条资料内事实、2 条资料外问题、1 条提示词注入、1 条 Embedding 失败 fallback。记录聚合指标，不把完整回答写入报告。

## 线上适配边界

本阶段不修改 Vercel。未来上线前需要单独评估：

1. 本地模型是否改为远程 Embedding Provider。
2. ChromaDB 是否改用适合部署的平台或预构建索引。
3. Serverless 冷启动和内存是否可接受。
4. 公开接口限流和 Embedding 成本。
5. 是否保留词法 fallback 和本地索引构建流程。

## 验收标准

- 本地索引命令可以从当前两份资料建立 ChromaDB collection。
- 重复运行索引不会产生重复 chunk。
- 正常事实问题能够返回向量检索来源。
- 资料外和明确对抗问题不会因为实体相似度而调用模型。
- Embedding 或 ChromaDB 失败时词法检索仍可用。
- 后端、前端、Astro check、build 和 diff check 通过。
- `.gitignore`、`.env.example` 和 README 清楚说明本地数据目录及启动方式。
- Preview、Production、知识正文和现有 API 契约保持不变。
- 项目文档可以准确描述“本地完成并验证的向量化 RAG”，不把本阶段写成线上持久化向量服务。
