# ai-agent-book 本地 RAG（Dense + BM25）

这是一个独立于个人网站的、可解释的本地 RAG 检索器。它使用固定 commit 的 `ai-agent-book` 五份正文资料，按 Qwen tokenizer 的 token 窗口切分，同时提供 Dense 向量检索和 BM25 关键词检索。

## 当前范围

- 资料快照：`data/source/`
- 主索引：`introduction.md`、`chapter1.md`、`chapter2.md`、`chapter3.md`、`afterword.md`
- 排除：`reference-answers.md`（留作后续评估，避免答案泄漏）
- 分块：512 tokens，64 tokens overlap；每个 chunk 保留文件和完整 Markdown 标题路径
- 嵌入：`Qwen/Qwen3-Embedding-0.6B`，MPS 优先，CPU 回退，float32
- 检索：NumPy 暴力余弦相似度，默认 Top 5
- 稀疏检索：`rank_bm25`，英文术语按词、中文按字切分

当前已完成 Dense-only、BM25-only、两路并行召回、RRF 融合、Cross-Encoder 重排序和本地 Hybrid 问答；正式评估集、FastAPI 和网站接入仍后置。

已增加受控多查询检索原语，并完成最小 Agentic RAG 循环：首轮证据不足时最多触发一次查询改写，再次执行 Dense/BM25、RRF 和重排序后强制停止。E4 对照结果和循环限制记录在 [`RAG_EVALUATION.md`](RAG_EVALUATION.md)。

评估方法与运行结果单独记录在 [`RAG_EVALUATION.md`](RAG_EVALUATION.md)；v1 已完成用户确认、冻结拆分和 E0-E3 正式 benchmark。单题失败归因见 [`evaluation/FAILURE_ANALYSIS.v1.md`](evaluation/FAILURE_ANALYSIS.v1.md)。

## 环境

复用项目已有 Python 3.11 环境：

```bash
cd "/Users/Admin/Documents/ChatGPT/个人网站/agentbook-rag"
../backend/.venv/bin/pip install -r requirements.txt
```

第一次运行会从 Hugging Face 下载 Qwen tokenizer 和模型并缓存到本机，不会写入本目录或 Git。

## 构建索引

```bash
../backend/.venv/bin/python -m agentbook_rag.ingest
```

默认输出到 `artifacts/qwen-dense-v1/`：

- `chunks.jsonl`：原始 chunk 和来源元数据
- `embeddings.npy`：float32 归一化向量
- `manifest.json`：来源 commit、模型、设备和切分参数

当前快照构建结果为 181 个 chunks、1024 维向量。`artifacts/` 已被 Git 忽略，索引需要时可从源码重新构建。

建立 BM25 索引（复用已经切好的 chunks，不重复下载 Embedding 模型）：

```bash
../backend/.venv/bin/python -m agentbook_rag.bm25_ingest
```

默认输出到 `artifacts/bm25-v1/`，包含 `chunks.jsonl`、`tokens.jsonl` 和 `manifest.json`。

## 查询

```bash
../backend/.venv/bin/python -m agentbook_rag.search "什么是 Agentic RAG？" --top-k 5
```

脚本会只返回检索到的原始片段，不替模型生成答案；这样可以直接检查召回是否来自正确章节。需要机器可读结果时加 `--json`：

```bash
../backend/.venv/bin/python -m agentbook_rag.search "什么是上下文工程？" --top-k 3 --json
```

查询 BM25 索引：

```bash
../backend/.venv/bin/python -m agentbook_rag.bm25_search "RRF" --top-k 5
```

BM25 没有命中查询词时返回空结果，不会随机返回零分片段；这便于后续并行召回判断某一路是否真正命中。

同时查询 Dense 和 BM25（结果暂不融合）：

```bash
../backend/.venv/bin/python -m agentbook_rag.parallel_search \
  "什么是 Agentic RAG？" --top-k 5
```

加 `--json` 时会返回同一个 JSON 对象中的 `dense` 和 `bm25` 两个数组，方便下一步 RRF 读取两路排名。

融合两路排名（RRF 默认 `k=60`）：

```bash
../backend/.venv/bin/python -m agentbook_rag.rrf_search \
  "什么是混合检索？" --top-k 5
```

加 `--json` 时返回 `rrf` 数组。每个候选包含融合分数、最终排名，以及它在 Dense/BM25 分支中的原始排名；RRF 不直接比较两路原始分数。

对 RRF 候选进行神经重排序：

```bash
../backend/.venv/bin/python -m agentbook_rag.rerank_search \
  "什么是混合检索和神经重排序？" \
  --candidate-k 10 --top-k 5
```

默认使用 `BAAI/bge-reranker-v2-m3`。它会把问题和每个候选片段一起输入 Cross-Encoder，输出新的相关性排序；结果中的 `dense_rank` 和 `bm25_rank` 仍然是重排前的来源排名。首次运行会从 Hugging Face 下载重排序模型。

预先生成查询改写并运行受控 E4：

```bash
set -a
source ../backend/.env
set +a

../backend/.venv/bin/python -m agentbook_rag.rewrite \
  evaluation/questions.v1.development.jsonl \
  artifacts/evaluation/questions.v1.development.rewrites.jsonl \
  --max-rewrites 2 --timeout 120

../backend/.venv/bin/python -m agentbook_rag.evaluate \
  --questions evaluation/questions.v1.development.jsonl \
  --rewrites artifacts/evaluation/questions.v1.development.rewrites.jsonl \
  --output-dir artifacts/evaluation/e4-development
```

改写文件应保存后再评估，避免同一问题每次得到不同查询；`--rewrites` 会额外启用 E4，并保留 E0-E3 作为同一轮对照。

如果批量生成中途失败，使用相同命令加 `--resume` 继续；改写器会跳过已经写入输出文件的问题，只请求尚未完成的题目。

运行完整 Hybrid RAG 问答：

```bash
set -a
source ../backend/.env
set +a

../backend/.venv/bin/python -m agentbook_rag.hybrid_ask \
  "什么是混合检索和神经重排序？" \
  --candidate-k 10 --top-k 5
```

该命令的链路是 Dense/BM25 并行召回 → RRF → Cross-Encoder 重排序 → OpenAI 兼容 Chat Completions。回答末尾会列出来源编号，终端还会显示每个来源的 Dense/BM25 原始排名。

## 校验评估问题集

在运行检索评估前，先检查 JSONL 字段、题目 ID、问题类型和 `gold_chunk_ids` 是否都能对应当前索引：

```bash
../backend/.venv/bin/python -m agentbook_rag.validate_questions \
  evaluation/questions.v0.jsonl --json
```

校验器只检查数据集结构和来源引用，不判断问题表达是否自然、标注是否完整；这些仍需人工审核。

当前扩充中的候选集为 `evaluation/questions.v1.candidate.jsonl`，包含 69 道题（65 道可用于检索 qrels，4 道不可回答题）。其中包含更接近日常提问的模糊/同义表达，以及故意使用非标准术语的题目；它仍是候选版本，人工审核后才能复制为冻结测试集。

候选题的审核和拆分规则见 [`evaluation/REVIEW_GUIDE.md`](evaluation/REVIEW_GUIDE.md)。

当前已根据审核确认生成正式拆分文件：`evaluation/frozen/questions.v1.development.jsonl`、`evaluation/frozen/questions.v1.test.jsonl` 和 `evaluation/frozen/questions.v1.unanswerable.jsonl`。正式对照只使用 `questions.v1.test.jsonl`，调参只使用 development 文件。

运行首轮检索 smoke benchmark（会加载 Dense Embedding 和 Reranker 模型）：

```bash
../backend/.venv/bin/python -m agentbook_rag.evaluate \
  --questions evaluation/questions.v0.jsonl
```

结果默认写入 `artifacts/evaluation/`，包含每个配置的逐题 JSONL 和一个 `*-summary.json` 汇总。`v0` 结果只用于验证评估程序，不代表正式效果结论。

## 本地问答闭环（V1.1）

如果只想验证 Dense-only 问答，可以把 Top-K 片段交给 OpenAI 兼容的 Chat Completions 接口。API Key 只从环境变量读取；可以复用已有 `backend/.env`，但不要把它提交到 Git：

```bash
cd "/Users/Admin/Documents/ChatGPT/个人网站/agentbook-rag"
set -a
source ../backend/.env
set +a

../backend/.venv/bin/python -m agentbook_rag.ask \
  "什么是 Agentic RAG？它和普通 RAG 有什么区别？" \
  --top-k 5
```

问答层默认读取 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 和 `OPENAI_MODEL`。也可以用 `--base-url` 或 `--model` 临时覆盖后两项。Dense-only 和 Hybrid 都使用 Chat Completions，回答会附带实际检索到的来源；它不会把检索内容当作可执行指令。

## 测试

```bash
../backend/.venv/bin/python -m pytest -q
```

测试覆盖固定窗口和 overlap、fenced code 标题排除、Dense/BM25 索引保存/加载和排序、统一检索结果结构、两路并行召回、RRF 合并、神经重排序、Hybrid 问答和边界行为。它们使用轻量 double，不会下载 Embedding、Reranker 或调用外部 API。

## 来源

语料来源和固定版本见 [`source-manifest.json`](source-manifest.json)。原项目许可证快照保存在 [`data/LICENSE`](data/LICENSE)。
