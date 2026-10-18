# questions.v1 候选集审核指南

`questions.v1.candidate.jsonl` 目前是候选集，不是正式测试集。冻结前逐题确认以下四点：

1. 问题表达自然、没有双重含义，问题类型标签正确。
2. 当前 `gold_chunk_ids` 足以回答问题；如果还有同样有效的证据片段，把它加入集合。
3. 多跳题包含所有必需证据，而不是只包含其中一个片段。
4. `unanswerable` 题确实不在当前五份资料中，不要因为“当前 chunk 没命中”就标成不可回答。

当前候选集扩充到 69 道，其中 65 道可回答、4 道不可回答。本次审核确认后已拆分为 44 道开发集、21 道冻结测试集和 4 道不可回答题。不可回答题单独保留，不参与第一阶段 Recall/MRR/nDCG 总分。开发集可以用于调参，冻结测试集在正式跑完前不要反复查看结果后改参数。

题目不要全部写成术语解释题。正式集合应同时包含：精确术语问法、模糊问法、同义改写、口语化短问句，以及需要跨片段组合的多跳问题。模糊问法的 `gold_chunk_ids` 可以包含多个证据片段，但必须由人工确认这些片段足以支持回答。

新增的 `q065-q069` 专门测试非标准术语和同义指代。审核时重点确认：问题中的替代表达是否确实指向标注的正式概念；如果普通读者可能有多种理解，应修改问题、补充说明或将其排除。

## 审核记录

建议直接在候选 JSONL 中修改问题、类型和 `gold_chunk_ids`，并在 `note` 中记录审核结论，例如：

```json
{"id":"q001","question":"...","type":"term","gold_chunk_ids":["book/chapter3.md#24"],"note":"approved; gold checked"}
```

审核完成后，创建一个仅包含 ID 的拆分清单，例如 `evaluation/splits.v1.json`：

```json
{
  "version": "v1",
  "source": "evaluation/questions.v1.candidate.jsonl",
  "development_ids": ["q001"],
  "test_ids": ["q002"],
  "unanswerable_ids": ["q051"],
  "excluded_ids": []
}
```

四个数组必须覆盖候选集中的每个 ID，不能重复或遗漏。`development_ids` 和 `test_ids` 不能包含 `unanswerable` 题；不合格或重复题放入 `excluded_ids`，并在 `note` 说明原因。

## 生成正式文件

先跑结构和来源校验：

```bash
cd "/Users/Admin/Documents/ChatGPT/个人网站/agentbook-rag"
../backend/.venv/bin/python -m agentbook_rag.validate_questions \
  evaluation/questions.v1.candidate.jsonl --json
```

再根据拆分清单生成文件：

```bash
../backend/.venv/bin/python -m agentbook_rag.split_questions \
  --questions evaluation/questions.v1.candidate.jsonl \
  --manifest evaluation/splits.v1.json \
  --output-dir evaluation/frozen \
  --index-dir artifacts/qwen-dense-v1
```

只有这个命令成功生成 `questions.v1.development.jsonl`、`questions.v1.test.jsonl` 和 `questions.v1.unanswerable.jsonl` 后，才进入正式 E0-E3 对照。正式 runner 使用 `test` 文件；调参只使用 `development` 文件。
