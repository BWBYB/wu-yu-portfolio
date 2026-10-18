# Agent Book RAG 评估方法与结果

> 本文是评估方法和实验结果的独立记录。每次跑出一组结果后，在这里补充配置、指标、观察和失败案例。
>
> 当前状态：v1 问题集已完成用户确认并冻结拆分；E0-E3 正式检索对照已完成，失败归因见 [`evaluation/FAILURE_ANALYSIS.v1.md`](evaluation/FAILURE_ANALYSIS.v1.md)。

<a id="toc"></a>

## 目录

- [评估目标](#goal)
- [采用的方法](#method)
- [固定条件](#conditions)
- [问题集](#dataset)
- [对照实验](#experiments)
- [指标说明](#metrics)
- [效果记录](#results)
- [失败分析](#failures)
- [执行顺序](#next-steps)

详细单题归因：[FAILURE_ANALYSIS.v1.md](evaluation/FAILURE_ANALYSIS.v1.md)

E4 目标题 pilot：[evaluation/targets.v1.jsonl](evaluation/targets.v1.jsonl)

<a id="goal"></a>

## 评估目标

检索和生成分开评估。第一阶段只评估**检索**，不调用 LLM judge；这样可以回答“正确证据有没有被找回、排在什么位置”，避免把检索错误误判成生成模型错误。

第二阶段再考虑评价最终答案正确性、忠实度、引用和拒答。它需要人工评价或 LLM judge，本轮暂不实施。

主要问题：

- BM25 是否补回 Dense 漏掉的精确术语？
- RRF 是否让相关证据更靠前？
- Reranker 是否把 RRF 候选中的关键证据排进最终 Top 5？
- 效果是否因问题类型而异？

<a id="method"></a>

## 采用的方法

复用现成评估工具，不自行重写标准排序指标：

| 任务 | 采用方案 | 说明 |
| --- | --- | --- |
| 检索排序指标 | `ranx` | 使用 qrels 和各检索配置的 run，计算 Recall、Hit Rate、MRR、nDCG 等 |
| 正确证据标注 | 人工审核的 JSONL 问题集 | 可先从语料片段生成候选问题，但每条问题、答案和来源都要人工核验 |
| 生成质量 | 下一阶段可选 `Ragas` / `DeepEval` | 当前先不混入检索分数，避免无法判断问题出在检索还是生成 |
| 运行记录 | JSONL 结果 + 本文汇总 | 保存 query、配置、排序、耗时和指标，便于复跑和定位 |

评估 runner 已接入 `ranx`，正式运行会把配置、逐题结果、分类型指标和延迟统计写入 `artifacts/evaluation/`。本项目仍不自行重写标准排序指标。

### 工具怎么选（简要）

- `ranx`：已经在项目中使用，负责“正确资料排第几”的检索指标；适合 E0-E5 对照。
- `Ragas`：适合后续自动评价最终答案的忠实度、上下文召回和答案相关性；接入方便，但仍需人工抽查。
- `DeepEval`：适合把生成质量检查写成测试用例；功能更丰富，但当前项目暂时不需要同时引入。
- 人工审核：不可替代，用于确认问题、正确答案和引用是否真的合理。

当前建议：保留 `ranx + 人工审核` 作为检索评估；等 Agentic RAG 闭环跑通后，再只选 `Ragas` 或人工 rubric 做生成层评估，不同时引入多个框架。

评估问题集可先用仓库内置校验器检查，再进入人工审核：

```bash
../backend/.venv/bin/python -m agentbook_rag.validate_questions \
  evaluation/questions.v0.jsonl --json
```

它只验证 JSONL 结构、题目 ID、允许的问题类型和 `gold_chunk_ids` 是否存在于当前索引；它不会替代人工判断问题是否自然、证据是否充分。

评估 runner：

```bash
../backend/.venv/bin/python -m agentbook_rag.evaluate \
  --questions evaluation/questions.v0.jsonl
```

runner 固定比较 E0-E3，默认每组保留 Top 20 候选，并额外记录前 5 个上下文；逐题记录和汇总写入 `artifacts/evaluation/`。`v0` 运行标记为 `smoke_benchmark`，不会自动变成正式结论。

### 对“Hit@5 是答案质量天花板”的说明

Hit@5 可以检查最终 Top 5 是否至少包含一条已标注的相关证据，是回答可获得正确证据的必要诊断之一，但不是答案质量的严格上限：问题可能需要多个证据片段，单一命中不代表证据完整；回答模型也可能不正确使用已经召回的证据。因此多跳题还要看必需证据覆盖率，生成质量留待第二阶段单独评估。

<a id="conditions"></a>

## 固定条件

首轮比较期间固定资料、切分和模型，只替换检索链路的阶段：

| 项目 | 固定值 |
| --- | --- |
| 语料版本 | `bojieli/ai-agent-book`，commit `dbc046eb896ac4e39aa19c7774c8bf49583b89a6` |
| 文档 | introduction、chapter1-3、afterword；不索引 `reference-answers.md` |
| Chunk 数 | 181 |
| 切分 | Qwen tokenizer，512 tokens，64 overlap |
| Dense | `Qwen/Qwen3-Embedding-0.6B`，NumPy cosine |
| BM25 | `rank_bm25`，`k1=1.5`、`b=0.75`，当前中文按字切分 |
| 融合 | RRF，`k=60` |
| Reranker | `BAAI/bge-reranker-v2-m3` |

每个 run 记录语料 commit、问题集版本、top-k、RRF 参数、模型、运行时间和代码版本。参数调优时只使用开发问题；冻结的测试问题不用于反复调参。

<a id="dataset"></a>

## 问题集

### 规模和分层

先用少量问题验证评估程序是否正确；`questions.v0.jsonl` 包含 12 道题，只用于格式和标注流程检查。当前候选集 `questions.v1.candidate.jsonl` 包含 69 道题（65 道可回答、4 道不可回答），正式对照集目标为 **50-80 道经人工审核的问题**。少于 30 道只作为试跑，不据此下强结论。

问题按类型标记，正式汇总时既看总分，也看各类型：

| 类型 | 检查重点 |
| --- | --- |
| 事实型 | 单个片段能否回答直接事实 |
| 多跳/聚合型 | 是否召回所有必需证据，允许跨章节 |
| 术语型 | BM25 是否命中精确术语、模型名或参数 |
| 语义改写型 | Dense 是否理解与原文措辞不同的表达 |
| 中英混合型 | 英文技术词与中文问题混合时的召回表现 |

生成式提问可以作为问题来源：从 chunk 抽样，让模型生成候选问题，再由人逐条检查问题自然度、答案是否确实由标注证据支持、是否存在其他同样可接受的来源。不能直接把“生成问题时的源 chunk”当作唯一正确 chunk。

不可回答问题对检索排序指标没有合适的正向 qrels，第一阶段不计入检索总分；可保留一小组作为后续拒答评估集。

### JSONL 记录格式

`gold_chunk_ids` 表示可接受的证据 chunk 集合；多跳题需包含回答问题所必需的不同证据。每个 chunk id 使用 `文件路径#chunk_index`，例如 `book/chapter3.md#24`。

```json
{"id":"q001","question":"什么是 RRF？","type":"term","gold_chunk_ids":["book/chapter3.md#24"],"note":"核对术语定义和公式"}
```

首轮不要求填写 `gold_answer`；若之后做生成质量评估，可扩展字段。chunk 切分方案变化时，必须重新把标注证据映射到新 chunks，不能沿用旧 chunk id。

当前样例文件：[`evaluation/questions.v0.jsonl`](evaluation/questions.v0.jsonl)。`v0` 表示草稿版本，所有题目仍需人工检查问题是否自然、gold 是否完整，以及是否存在其他同样可接受的 chunk。

候选文件：[`evaluation/questions.v1.candidate.jsonl`](evaluation/questions.v1.candidate.jsonl)。它包含 65 道带 gold chunk 的检索题和 4 道不可回答题，其中包含宽泛、口语化、同义表达和非标准术语测试题。用户已确认完成人工审核；候选文件保留生成阶段的 `待人工审核` note，正式审核状态以 [`evaluation/splits.v1.json`](evaluation/splits.v1.json) 的 `review_status` 和 `evaluation/frozen/` 拆分文件为准。

<a id="experiments"></a>

## 对照实验

首轮使用相同问题集比较四组；每组保留 Top 20 检索结果用于评估，重排序组从 RRF Top 20 候选中选出最终 Top 5。

| 配置 | 检索链路 | 主要观察 |
| --- | --- | --- |
| E0 Dense-only | Dense Top 20 | 语义检索基线 |
| E1 BM25-only | BM25 Top 20 | 关键词检索基线 |
| E2 Hybrid + RRF | Dense/BM25 各召回，RRF Top 20 | 两种召回加融合后的变化 |
| E3 Hybrid + RRF + Reranker | RRF Top 20，再精排取 Top 5 | 重排对最终上下文排名的影响 |

重点比较：

- E0 与 E1：两种检索器各自的强弱。
- E0/E1 与 E2：Hybrid/RRF 是否改善候选覆盖和排名。
- E2 Top 5 与 E3 Top 5：重排序有没有把相关证据提升进最终上下文。
- 分问题类型查看收益和退化，避免总平均数掩盖 BM25 或 Dense 的特长。

<a id="metrics"></a>

## 指标说明

使用 `ranx` 计算标准排序指标。首轮报告以下项目：

| 指标 | 直观含义 | 适用位置 |
| --- | --- | --- |
| Recall@5 / @10 / @20 | 前 K 个结果找回了多少已标注相关证据 | E0-E3 |
| Hit Rate@5 / @10 / @20 | 前 K 个结果至少命中一条相关证据的查询比例 | E0-E3 |
| MRR@10 | 第一条相关证据平均排得有多靠前 | E0-E3 |
| nDCG@10 | 相关证据整体排序质量 | E0-E3 |
| 必需证据覆盖率 | 多跳问题所需证据组是否都出现在候选/上下文中 | E2 候选与 E3 Top 5 |
| 完整覆盖率 | 一题的全部 gold chunk 是否都进入指定 Top-K | 多跳问题诊断，不替代 Recall |
| p50 / p95 延迟 | 检索与重排序耗时分布 | E0-E3，分阶段记录 |

Hit Rate 和 Recall 口径不同：Hit Rate 只问“有没有命中”；Recall 还看全部已标注相关证据中找回了多少。若一个问题只有一个相关 chunk，两者数值可能相同。

当前阶段不测答案正确性、引用忠实度、拒答率，不统计 token 成本；这些不在本轮结论范围内。

<a id="results"></a>

## 效果记录

### 当前状态

| 项目 | 状态 | 结果 |
| --- | --- | --- |
| 评估方法 | 已确定 | `ranx` 排序指标 + 人工审核 qrels |
| 正式问题集 | 已建立并冻结 | 44 道开发题、21 道冻结测试题、4 道不可回答题；拆分清单见 `evaluation/splits.v1.json` |
| v0 样例问题集 | 已建立草稿 | 12 道，已完成 smoke benchmark |
| v1 候选问题集 | 已建立候选 | 69 道（65 道可回答、4 道不可回答），见 `evaluation/questions.v1.candidate.jsonl`；结构校验通过，已按审核结果拆分 |
| E0-E3 量化对照 | 已完成正式 v1 | 运行 ID `20261015-200121`；结果已写入下方表格，单题失败归因见 `evaluation/FAILURE_ANALYSIS.v1.md` |
| 生成层评价 | 暂缓 | 本轮不调用 LLM judge |

### 已有的非基准观察

P5 曾用“什么是混合检索和神经重排序？”做过一次真实 Hybrid 问答，正确相关的 chapter3 `#24` 片段进入了重排序 Top 1。它只证明调用链能运行，是单条 smoke check，不是 benchmark，不作为效果提升结论。

### 实验结果表

每次完成一轮后新增一行。没有跑出的值留空，不用主观估计补齐。

| 日期 | 数据集版本 | 配置 | Recall@20 | Hit@5 | MRR@10 | nDCG@10 | p50/p95 | 结论 |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| 2026-10-15 | v0 smoke（12 题） | E0 Dense-only | 0.666667 | 0.75 | 0.613426 | 0.526364 | 84.738 / 812.986 ms | 流程通过；不作正式结论 |
| 2026-10-15 | v0 smoke（12 题） | E1 BM25-only | 0.916667 | 1.0 | 0.808333 | 0.756414 | 2.776 / 5.231 ms | 草稿题中关键词检索较强；需扩充题型验证 |
| 2026-10-15 | v0 smoke（12 题） | E2 Hybrid + RRF | 1.0 | 0.75 | 0.671759 | 0.694428 | 57.075 / 64.88 ms | Top 20 覆盖完整，Top 5 排序仍需观察 |
| 2026-10-15 | v0 smoke（12 题） | E3 Hybrid + RRF + Reranker | 1.0 | 1.0 | 0.916667 | 0.887769 | 2330.644 / 2570.491 ms | 重排序提升了草稿集 Top 5 排名；延迟明显增加 |
| 2026-10-15 | v1 frozen（21 题） | E0 Dense-only | 0.547619 | 0.666667 | 0.551587 | 0.456167 | 82.224 / 85.284 ms | 语义基线；对非标准问法和多证据问题仍有遗漏 |
| 2026-10-15 | v1 frozen（21 题） | E1 BM25-only | 0.833333 | 0.761905 | 0.580952 | 0.578157 | 2.265 / 4.155 ms | 关键词召回强且很快；多跳和同义改写仍受限 |
| 2026-10-15 | v1 frozen（21 题） | E2 Hybrid + RRF | 0.880952 | 0.619048 | 0.569293 | 0.573488 | 55.507 / 58.116 ms | Top-20 覆盖最好之一，但 Top-5 排名尚未稳定 |
| 2026-10-15 | v1 frozen（21 题） | E3 Hybrid + RRF + Reranker | 0.880952 | 0.857143 | 0.781746 | 0.751122 | 2327.271 / 2344.827 ms | 当前排序质量最好；延迟约为 E2 的 40 倍 |

每次实验结果建议保存为单独的 JSONL 文件，文件名包含日期和数据集版本；运行配置写入记录头或对应 manifest，避免只有最终均值、无法定位单题结果。

### v0 smoke 结果说明

本次运行使用 `evaluation/questions.v0.jsonl` 的 12 道草稿题，运行标识为 `20261015-111642`，逐题结果位于 `artifacts/evaluation/`。它验证了 E0-E3 runner、`ranx` 指标计算、分类型汇总和结果落盘均可工作，但不能替代正式评估：题集规模小、题型分布不均，且问题与 gold chunk 尚未完成最终人工审核。特别是 E1 在该草稿集上的高分，可能反映题目中的术语与原文措辞较接近，不应外推到更广泛的语义改写问题。

### v1 冻结集正式结果

本次运行使用 `evaluation/frozen/questions.v1.test.jsonl` 的 21 道冻结测试题，运行标识为 `20261015-200121`。4 道不可回答题单独保存，不进入检索排序指标。

主要结论：

- E3 的 Hit@5、MRR@10 和 nDCG@10 均最高，说明 Cross-Encoder 主要改善了“正确证据能否排进最终上下文”以及相关结果的前置程度。
- E2 和 E3 的 Recall@20 都是 `0.880952`，说明本轮重排序没有找回原本不在候选池里的证据；它改善的是候选池内部排序。
- E1 的 Recall@20 为 `0.833333`，低于 Hybrid 的 `0.880952`，但 p50 只有 `2.265 ms`。BM25 仍然是很有价值的低延迟基线。
- E3 p50 为 `2327.271 ms`，约为 E2 的 42 倍；是否保留 Reranker，需要结合最终上下文质量和可接受延迟决定。

分类型明细和逐题记录保存在 `artifacts/evaluation/20261015-200121-E*.jsonl` 与 `20261015-200121-summary.json`。低分题和 E2→E3 排名变化已经整理到 [FAILURE_ANALYSIS.v1.md](evaluation/FAILURE_ANALYSIS.v1.md)。

另一个工程观察是 E3 的重排序延迟显著高于 E0-E2；本次结果只记录总延迟的初步数据，后续正式 runner 需要补充单独的 rerank p50/p95，并在决定是否保留该组件时同时考虑收益和延迟。

<a id="failures"></a>

## 失败分析

详细结果见 [FAILURE_ANALYSIS.v1.md](evaluation/FAILURE_ANALYSIS.v1.md)。本节保留分类框架，后续每轮实验沿用同一套口径：

| 失败类别 | 诊断方式 | 可能对应的后续改动 |
| --- | --- | --- |
| 初召回遗漏 | 正确证据不在 Dense/BM25/RRF 候选中 | Embedding、BM25 分词、查询处理 |
| 融合排名不佳 | 证据进了某一分支，但没进 RRF Top-K | RRF 参数、分支候选数量 |
| 重排压低证据 | 证据进了 RRF 候选，但没进最终 Top 5 | Reranker 模型或输入文本 |
| 分块切断证据 | 源文正确但 chunk 不完整或上下文缺失 | chunk size、overlap、标题分块 |
| 标注不完整/问题歧义 | 人工复核后发现还存在其他正确来源或问法不清 | 修订 qrels 或移除问题 |

本轮结论：`q034` 属于初始召回遗漏；`q010`、`q043`、`q057`、`q069` 展示了重排收益；`q013`、`q055` 展示了重排退化；`q010`、`q034`、`q056`、`q067` 还暴露出多跳证据不完整。不要把 reranker 的排序收益表述成 Recall 提升。

### E4 受控多查询 pilot

E4 不是完整自主 Agent，而是一个可复现的受控多查询配置：原始问题始终保留，另外使用最多两个预先生成并落盘的改写查询；所有查询的 Dense/BM25 结果统一进入 RRF，最后仍用原始问题驱动 Reranker。目标是先隔离“查询改写是否能补回初始召回”的变量。

| 运行 | 题目 | Recall@20 | Hit@5 | MRR@10 | nDCG@10 | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E3 baseline | 3 | 0.333333 | 0.333333 | 0.333333 | 0.204382 | 2429.665 ms |
| E4 multi-query pilot | 3 | 0.833333 | 1.0 | 1.0 | 0.742098 | 2998.959 ms |

运行 ID：`20261015-223933`；逐题记录位于 `artifacts/evaluation/e4-targets/`。

必需证据指标（E4）：

| 截止位置 | 平均证据覆盖率 | 完整覆盖率 |
| --- | ---: | ---: |
| Top 5 | 0.666667 | 0.333333 |
| Top 20 | 0.833333 | 0.666667 |

其中“完整覆盖率”表示一题的全部 gold chunk 都已进入对应候选范围；它比单个 Hit 更适合诊断多跳问题。

逐题观察：

- `q034`：从两条 gold 均未进 Top 20，改善为 `chapter1#27` 进入第 1；`#28` 仍缺失。
- `q055`：`chapter1#0` 进入第 1；`chapter1#1` 仍未进 Top 20。
- `q056`：`chapter3#13`、`#14` 分别进入第 1、2，完整覆盖了两条 gold。

这说明多查询改写有潜力改善初始召回，但仍不能替代“必需证据集合是否完整”的判断。该结果只是一组 3 题的目标 pilot，不作为完整 development 集结论。

### E4 development benchmark

在 44 道 development 题上使用已落盘的查询改写文件运行 E0-E4。该数据集用于选择方案，不用于最终无偏能力宣称。

运行 ID：`20261015-233435`；改写文件：`artifacts/evaluation/questions.v1.development.rewrites.jsonl`。

| 配置 | Recall@20 | Hit@5 | MRR@10 | nDCG@10 | Top-5 完整覆盖率 | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| E2 Hybrid + RRF | 0.965909 | 0.590909 | 0.502192 | 0.580410 | 0.454545 | 64.087 ms |
| E3 + Reranker | 0.965909 | 0.954545 | 0.859343 | 0.860639 | 0.886364 | 2687.381 ms |
| E4 + 多查询改写 | 0.977273 | 0.977273 | 0.864394 | 0.874076 | 0.909091 | 2859.523 ms |

按类型看，E4 的多跳题 Recall@20 为 `1.0`，Top-5 完整覆盖率为 `0.75`；语义改写题 Recall@20 为 `0.923077`，与 E3 持平；术语题没有比 E3 变差。E4 相对 E3 的主要收益是少量补回候选证据，而不是大幅改善排序。

当前工程判断：保留 E4 作为 development 上的候选方案，但不要因为这轮结果就把它设为默认线上链路。它增加了约 `172 ms` 的 p50（相对 E3），而 E3 本身已经约 `2.7 s`；应在 frozen test 上确认收益后再决定是否启用。

### E4 frozen test 对照

在 21 道冻结测试题上生成并保存固定改写文件 `artifacts/evaluation/questions.v1.test.rewrites.jsonl`，运行 ID 为 `20261015-235155`。该轮只使用已落盘改写，不在评估过程中重新调用改写模型。

| 配置 | Recall@20 | Hit@5 | MRR@10 | nDCG@10 | Top-5 完整覆盖率 | Top-20 完整覆盖率 | p50 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| E3 + Reranker | 0.880952 | 0.857143 | 0.781746 | 0.751122 | 0.619048 | 0.809524 | 2547.712 ms |
| E4 + 多查询改写 | 0.904762 | 0.952381 | 0.874603 | 0.797610 | 0.571429 | 0.809524 | 2694.484 ms |

E4 相对 E3 的变化：Recall@20 `+0.023810`、Hit@5 `+0.095238`、MRR@10 `+0.092857`、nDCG@10 `+0.046488`；p50 增加约 `146.772 ms`（约 5.8%）。但 Top-5 完整证据覆盖率下降 `0.047619`，Top-20 完整覆盖率不变，说明 E4 主要改善单条证据的排序与命中，并没有在本测试集上改善“所有必要证据都进入上下文”的能力。

按类型看，E4 对多跳题的 Recall@20 从 `0.5` 提升到 `0.75`，Top-5 命中率从 `0.5` 提升到 `1.0`；语义改写题 Recall@20 与 E3 持平（均 `0.85`），术语题未退化。由于冻结集只有 21 题，且没有生成层答案质量评估，这些结果用于当前工程决策，不作通用结论。

当前决策：E4 保留为“高质量检索”可选模式；默认低延迟模式仍使用 E3。下一阶段应先做生成层评估或按需进行单变量检索实验，不再为 E4 反复调参。

### P7d：最小 Agentic RAG 循环

已实现 `agentbook_rag.agentic_loop`。当前循环是有边界的最小版本：

1. 先执行一次 E3（Dense + BM25 + RRF + Reranker）。
2. 读取重排结果的最高分；达到阈值就停止并交给回答层。
3. 未达到阈值时调用查询改写函数，再执行一次多查询检索。
4. 第二轮后强制停止，不允许无限循环。

这里的“证据不足”暂时只用 reranker 最高分判断，规则简单、可解释，但还没有经过 development 集校准；`rewrite` 函数通过参数注入，生产环境可接 OpenAI 兼容 API，测试可以使用固定改写。该版本证明了循环结构和停止保护已经跑通，不代表 Agentic RAG 的效果已经优于 E3。

最小调用形式：

```python
from agentbook_rag.agentic_loop import run_agentic_search

result = run_agentic_search(
    question,
    retriever,
    reranker,
    rewrite=lambda query: ["补充检索查询"],
    min_score=0.0,
)
```

错误归因先于调参；标注错误应先修正并记录数据集版本，不能通过改系统参数掩盖。

<a id="next-steps"></a>

## 执行顺序

1. [x] 人工审核 `evaluation/questions.v1.candidate.jsonl`，并记录 `review_status`。
2. [x] 将审核通过的题目拆成开发集、冻结测试集和不可回答集。
3. [x] 使用 `agentbook_rag.evaluate` 对冻结集运行 E0-E3，并保存逐题 JSONL。
4. [x] 将冻结集结果和分类型指标填入本报告。
5. [x] 复核失败案例；详见 [FAILURE_ANALYSIS.v1.md](evaluation/FAILURE_ANALYSIS.v1.md)。
6. [x] 核对 `q034`、`q055`、`q056` 的原文与 gold 标注。
7. [x] 完成 3 道目标题的受控多查询 pilot，结果见上文。
8. [x] 完善多跳证据完整性判断，并用 development 集运行可复现 E4。
9. [x] 检查 development 结果中 E4 的具体改善/退化题目，确认没有明显 query drift。
10. [x] 冻结 E4 查询改写生成方式后，在 frozen test 上运行一次 E3/E4 对照。
11. [ ] 决定是否开展 chunking、中文分词、RRF `k` 或候选数量的单变量实验；在生成层评估前不盲目调参。

生成层评估可在检索基线稳定后另立阶段，再决定是否使用 Ragas/DeepEval 或人工 rubric；不与本轮检索分数混报。

### 本项目的评估顺序

1. 先固定资料、分块和问题集。
2. 用 `ranx` 比较 Dense、BM25、Hybrid、Reranker。
3. 用同一套问题比较 E3 和 E4/Agentic RAG，确认查询改写是否有收益。
4. 再评估最终答案的正确性、引用忠实度和拒答能力。
5. 网站上线后，再逐项替换分块、Embedding、BM25、RRF 或 Reranker，并重复同一套测试。

因此“先评估、后 Agentic”是为了建立基线，不代表跳过第 11 步；第 11 步现在正进入真正的决策循环实现阶段。

**参考**：[`ranx` 官方项目](https://github.com/AmenRa/ranx)；后续生成评估候选：[RAGAS](https://docs.ragas.io/)、[DeepEval](https://deepeval.com/docs)。
