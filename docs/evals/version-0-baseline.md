# Version 0 评测基线

本报告由离线评测运行器生成，仅记录聚合指标和可定位的案例 ID，不记录问题、回答、请求头或供应商原始错误。

## 指标

指标定义：来源命中率只统计有期望来源的案例；关键事实覆盖率是字符串代理检查；资料外正确拒答率要求 HTTP 200、无来源且未调用模型；无命中模型短路率统计边界案例中无来源且未调用模型的比例；错误检索率统计来源不相交或资料外出现来源的案例。

- `total_cases`: 28
- `category_counts`: {'adversarial': 5, 'out_of_scope': 5, 'paraphrase': 5, 'profile_fact': 6, 'project_fact': 7}
- `http_success_rate`: 1.0
- `source_hit_rate`: 1.0
- `required_fact_coverage`: 1.0
- `out_of_scope_refusal_rate`: 0.1
- `no_match_model_short_circuit_rate`: 0.1
- `retrieval_error_rate`: 0.3214
- `mean_latency_ms`: 1.85
- `p95_latency_ms`: 2.01

## 失败案例

- `boundary-002`: model_call_mismatch; boundary_mismatch
- `boundary-003`: model_call_mismatch; boundary_mismatch
- `boundary-004`: model_call_mismatch; boundary_mismatch
- `boundary-005`: model_call_mismatch; boundary_mismatch
- `adversarial-001`: model_call_mismatch; boundary_mismatch
- `adversarial-002`: model_call_mismatch; boundary_mismatch
- `adversarial-003`: model_call_mismatch; boundary_mismatch
- `adversarial-004`: model_call_mismatch; boundary_mismatch
- `adversarial-005`: model_call_mismatch; boundary_mismatch

## 局限

自动指标不能代表语义正确率、回答自然度或完整的提示词注入抵抗力，需结合人工复核。
