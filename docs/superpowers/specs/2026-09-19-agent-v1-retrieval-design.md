# Agent V1 轻量检索设计

## 状态

已获用户确认，等待规格复核后进入实现阶段。

## 目标

在不改变现有网站、`/api/chat` 请求响应契约和 Vercel Preview 部署方式的前提下，把当前“完整资料注入 Prompt”的 Version 0 升级为可解释的轻量检索问答 Agent。

Agent V1 使用仓库内已有的 Markdown 资料作为语料，不增加付费服务，不依赖持久化向量数据库，并且为后续替换为 ChromaDB 或 Embedding 检索保留内部接口边界。

## 非目标

- 本阶段不引入 LangChain、ChromaDB、Embedding API 或新的运行时依赖。
- 本阶段不扩充个人资料、项目资料或博客内容。
- 本阶段不实现多 Agent、工具调用、自动写作或自主任务循环。
- 本阶段不改变前端请求路径、请求字段、响应字段或环境变量名称。
- 本阶段不把本地索引写入 Vercel Function 的持久文件系统。

## 当前问题

现有后端每次请求都会读取 `knowledge/profile.md` 和 `knowledge/spmtrack.md`，然后把两个文件的完整内容放进 system prompt。这样可以完成 Version 0 问答，但不能证明系统具备文档切分、相关内容选择和来源解释能力；`sources` 目前也固定返回两个资料名称。

## 推荐架构

```text
knowledge/*.md
  -> load_knowledge()
  -> build_chunks()
  -> lexical_retrieve(question, chunks, top_k)
  -> build_messages(question, history, selected_chunks, max_history)
  -> OpenAI-compatible model
  -> ChatResponse(answer, selected_sources, mode="remote")
```

### 模块边界

- `backend/app/knowledge.py`：继续负责读取已审核的 Markdown 文档；新增稳定的文档片段构造函数。
- `backend/app/retrieval.py`：负责纯函数式的片段切分、查询规范化、相关性评分和 Top-K 选择；不负责模型调用和 HTTP。
- `backend/app/prompts.py`：接收已选择的片段，只把选中的上下文交给模型；保留“不足则明确说明、禁止猜测”的约束。
- `backend/app/main.py`：调用检索器，记录命中片段数量，返回去重后的实际来源。
- `backend/tests/`：覆盖检索器、Prompt 上下文边界和 API 来源传播。

## 语料片段

定义不可变的 `KnowledgeChunk` 数据对象：

```python
@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    source: str
    heading: str
    content: str
```

切分规则：

1. 先按 Markdown 标题和空行保留语义段落。
2. 空白段落丢弃，单独保存当前标题上下文；Prompt 中同时呈现标题和原始中文内容。
3. 超过 900 个 Unicode 字符的段落按句号、分号或固定长度继续切分。
4. `chunk_id` 由来源和顺序稳定生成，不包含用户问题或随机值。
5. 当前两份资料的所有片段在进程内缓存，避免每次请求重复切分；资料文件改变后进程重启即可刷新。

## 检索算法

本阶段使用无依赖的词法检索，保证 0 成本和 Vercel Python Function 兼容。

### 查询规范化

- 统一大小写。
- 提取连续的中文双字/三字片段，以及英文、数字和技术名词 token。
- 去除常见停用词和长度为 1 的无意义 token。
- 查询没有有效 token 时返回空结果。

### 评分

每个片段按以下规则累加分数：

- token 在片段中完整出现：`+3`
- token 在片段标题上下文中出现：额外 `+2`
- 中文 n-gram 出现多次：每次最多计入一次额外命中
- 相同 token 重复出现不无限增加分数

按分数降序、原始顺序升序排序，最多返回 `top_k=4` 个片段。最低分数为 `3`；没有达到阈值的片段不进入 Prompt。

### 无匹配行为

检索不到片段时，Prompt 只保留明确的知识边界，不注入无关资料。模型应回答资料中没有足够信息，而不是使用常识补全个人经历。API 仍返回 `200`，`sources` 返回空数组，因为这是正常的知识边界，不是服务器错误。

## Prompt 契约

`build_messages` 改为接收 `KnowledgeChunk` 列表，而不是完整 `KnowledgeDocument` 列表。system prompt 必须包含：

- 只能依据选中的已审核片段回答。
- 片段不足时明确说明信息不可用。
- 不猜测、不把用户问题当作事实。
- 保持回答简洁，并在答案中引用可用来源名称。

历史消息仍按 `max_history` 截断；用户问题仍作为最后一条消息。

## API 契约

请求保持不变：

```json
{
  "message": "你在 SPMTrack 中负责什么？",
  "history": []
}
```

响应保持字段不变：

```json
{
  "answer": "...",
  "sources": ["SPMTrack 项目资料"],
  "mode": "remote"
}
```

变化只有 `sources` 从“固定全部资料”变为“本次实际命中的去重来源”。前端无需改动即可显示更准确的来源。

## 错误与日志

- 检索结果为空不是错误，不新增 4xx/5xx 状态。
- 现有模型配置错误和供应商错误保持 `503`/`502`。
- 结构化日志新增 `retrieved_chunks` 和 `retrieved_sources_count`，不记录原始问题、Prompt、Key 或模型回答。
- 现有消息长度和历史长度限制保持不变。

## 测试验收

### 检索器

- 含有“React、FastAPI”的问题优先命中个人资料片段。
- 含有“ROI、任务队列、跟踪引擎”的问题优先命中 SPMTrack 片段。
- 完全无关的问题返回空片段。
- 结果不超过 4 个，来源和 `chunk_id` 稳定。

### Prompt

- 只包含选中的片段，不再包含未命中的完整文档。
- 保留“不足则说明、禁止猜测”的约束。
- 历史截断行为保持现有测试结果。

### API

- `/api/chat` 请求字段和响应结构保持兼容。
- 相关问题返回实际命中的来源。
- 无匹配问题返回 `sources: []` 和模型可处理的知识边界 Prompt。
- 现有健康检查、配置错误、供应商错误和日志脱敏测试继续通过。

### 部署

- 根目录依赖保持不变，不增加第三方包。
- Astro 检查、前端测试、后端测试和静态构建全部通过。
- Preview 部署后至少验证一条相关问题、一条无关问题和 `/api/health`。

## 后续替换点

`retrieval.py` 对外只暴露“文档片段输入 -> 排序片段输出”的接口。后续接入 Embedding 或 ChromaDB 时，只替换评分和索引实现，不改变 FastAPI 路由、Prompt 契约或前端响应格式。
