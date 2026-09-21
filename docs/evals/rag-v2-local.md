# RAG V2 本地验证记录

## 范围与结论

本阶段在本地接入 E5 Embedding 与 ChromaDB 持久化向量检索，目标是形成可运行、可解释的 RAG 项目经验。线上 Preview/Production、知识资料正文和公开 `/api/chat` 契约均未修改。

本地索引、向量检索、资料外短路和词法 fallback 已通过。当前结果只证明两份固定 Markdown 资料上的本地主链路，不代表通用语义正确率，也不代表向量数据库已上线。

## 配置

| 项目 | 值 |
| --- | --- |
| Embedding 模型 | `intfloat/multilingual-e5-small` |
| 文档前缀 | `passage: ` |
| 查询前缀 | `query: ` |
| 向量归一化 | 开启 |
| 向量库 | ChromaDB `PersistentClient` |
| 距离 | cosine |
| collection | `wu_yu_knowledge_v2` |
| `top_k` | 4 |
| `max_distance` | 0.096 |
| 本地路径 | `backend/data/chroma/`，被 Git 忽略 |

相对路径由后端目录解析，索引不提交到公开仓库。知识资料变化后需要重新构建索引。`OPENAI_*` 只用于检索后的答案生成，本地 Embedding 不读取 OpenAI Key。

## 可复现命令

```bash
cd backend
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.index_knowledge
.venv/bin/uvicorn app.main:app --reload --port 8000
```

本轮索引输出为 8 个 chunk。重复执行索引命令会删除并重建同名 collection，不累积重复记录。

## 检索与 fallback

1. 明确的提示词泄露、编造事实或服务器文件请求先经过现有安全门控，不访问向量组件。
2. `RAG_RETRIEVAL=vector` 时，本地 E5 生成查询向量，ChromaDB 按 cosine distance 返回阈值内片段。
3. 向量查询成功但无命中时返回空上下文，`/api/chat` 不调用 LLM。
4. Embedding 或 ChromaDB 异常时回退到词法检索，并在脱敏日志中记录 `retrieval_mode` 与 `fallback_used`。
5. 对外响应仍只有 `answer`、`sources` 和 `mode`；其中 `mode=remote` 表示答案由远程 LLM 生成，不表示检索模式。

## 8 条本地人工验证

验证直接调用真实 `retrieve_relevant_chunks()` 与本地索引；故障案例只注入稳定的 `EmbeddingError`。记录案例类别、检索模式、片段数和来源聚合，不保存问题正文、回答、向量或供应商错误。

| 类别 | 数量 | 结果 |
| --- | ---: | --- |
| 事实问题 | 4 | 4/4 使用 `vector`，均命中期望来源，每题 1 个片段 |
| 资料外问题 | 2 | 2/2 使用 `none`，0 个片段 |
| 提示词注入请求 | 1 | 1/1 使用 `none`，0 个片段，向量查询前阻断 |
| 向量故障 | 1 | 1/1 使用 `lexical`，`fallback_used=true` |

## 自动化证据

- Task 4 检索/API 验收集：52 passed。
- 覆盖 E5 前缀与归一化、Chroma 重建/查询、向量/词法编排、资料外短路、blocked 请求、Embedding/VectorStore 异常 fallback、线程边界、公开响应契约和日志脱敏。
- 现有 Starlette/httpx 与 anyio 各有一条弃用警告，不影响本阶段行为。

## 限制与下一步

- 语料只有 2 份文档、8 个 chunk，不能据此证明大规模知识库效果。
- `max_distance=0.096` 来自当前固定实验；资料扩充后必须重新评估阈值，不能直接沿用。
- 当前只完成本地部署，PyTorch、sentence-transformers、模型权重与 ChromaDB 不适合直接塞入现有零成本 Vercel Function。
- 先补充和审核求职资料，再固定一组更大的评测集，比较召回率、边界正确率、延迟和资源占用。
- 本地稳定后再独立评估线上托管方案；本阶段不引入 LangChain、LangGraph、MCP 或多 Agent。
