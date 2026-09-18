---
title: 从本地 API 到线上 Preview：个人知识库 Agent 的部署记录
slug: online-preview-deployment
date: 2026-09
status: organizing
summary: 记录 Astro、FastAPI 与模型接口进入同一个 Vercel Preview 的设计、验证、安全边界和上线取舍。
tags:
  - Vercel
  - FastAPI
  - Deployment
---

> 草稿状态：已完成设计阶段大纲，后续按部署适配、安全配置、Preview 验收和 Production 决策逐段补充。本文不记录真实 API Key、账户信息或完整供应商错误。

## 1. 为什么快速迭代时仍然需要线上 Preview

- 本地成功不能证明云函数时长、文件打包、环境变量和公网模型访问都正确。
- Preview 是隔离的线上实验环境，不等同于正式生产发布。
- 正式网站保持稳定，只有经过验收的 Preview 才有资格提升。

## 2. 0 成本约束下的方案比较

- 同一个 Vercel 项目：Astro 静态页面与 FastAPI Python Function 同域部署。
- 两个 Vercel 项目：边界更独立，但增加 URL、CORS 和环境变量协调。
- 免费容器平台：可能休眠，冷启动会放大当前约 52.57 秒的模型延迟。
- 最终选择与理由：同项目、同域 `/api/chat`、Preview-first。

## 3. 目标架构

```text
Browser
  -> Astro / React
  -> same-origin /api/chat
  -> FastAPI on Vercel Python Function
  -> HeiyuCode Responses API
```

- 部署适配文件为 `api/index.py`、`api/[...path].py` 与 `vercel.json`，由入口复用已有 FastAPI app，并显式包含资料文件。
- 根目录 `requirements.txt` 直接列出运行时依赖；Vercel Python 构建器不接受 `-r backend/requirements.txt` 这种递归引用。
- 浏览器不直连模型，因为 Key 必须留在服务端，且同域 Function 可以统一错误和日志边界。

## 4. 部署适配阶段

- 复用现有 FastAPI app，不复制业务代码。
- 显式打包 `backend/app/**` 与 `knowledge/**`。
- 增加 `/api/health` 与 `/api/chat` 的线上验证；本地 `/health` 继续兼容。
- 前端在 `PUBLIC_AGENT_API_URL=/` 时使用同域 `/api/chat`，未设置变量时仍保持演示模式。
- 已加入脱敏结构化日志：请求 ID、路由、状态、耗时、输入长度/历史条数、来源数和错误类别。
- 首次 Preview 因 `includeFiles` 类型不符合 Vercel schema 失败；修正为 brace glob 后，第二次 Preview 因根依赖文件的 `-r` 递归引用失败；改为直接依赖列表后构建成功。
- 最终 Preview：`https://wu-yu-portfolio-6ktcjw0ft-bwbybs-projects.vercel.app`，状态为 Ready。
- Agent V1 在现有 Preview 代码上增加了无依赖的片段检索：先按标题和段落切分资料，再只把命中片段放进 Prompt；`sources` 不再固定返回全部资料。

## 5. 超时与冷启动

- 本地真实模型请求曾耗时约 52.57 秒。
- 超时需要满足：上游模型 < 云函数 < 浏览器。
- 免费 Hobby 环境的实际 Function 上限必须通过部署验证。
- 待补：冷请求、热请求、最快、最慢和平均耗时。

## 6. 环境变量与密钥边界

- 模型 Key 只进入服务端敏感变量。
- Preview 使用指定分支的环境变量，Production 暂不配置。
- 前端只获得 `PUBLIC_AGENT_API_URL=/`，不能获得模型 Key。
- 客户端构建产物扫描中只命中压缩 CSS 的 `mask-` 字符串，复查未发现 `OPENAI_API_KEY`、真实 `sk-` Key 或中转站地址。

## 7. 免费条件下的滥用防护

- 消息长度和历史条数限制只是输入保护，不是频率限制。
- Preview URL 暂不公开。
- Production 前需要跨实例有效的免费限流或等价保护。
- 待补：Vercel Hobby 当前可用能力与最终选择。
- 待补：429 验证和供应商额度上限。

## 8. Preview 端到端验收

- [x] `/api/health` 返回 200。
- [x] `/api/chat` 相关问题返回 `mode: remote`、`SPMTrack 项目资料`，命中 3 个片段；本次 Runtime Log 记录耗时约 9.7 秒。
- [x] 未知问题命中 0 个片段、返回 `sources: []`，模型明确说明资料不足。
- [ ] 连续真实请求完成并记录耗时。
- [ ] 页面显示远程回答和来源。
- [ ] 移动端、错误、重试和清空状态正常。
- [x] Runtime Logs 已确认请求进入 `/api/chat`，中转站返回 200，日志只记录脱敏元数据。

当前状态：代码已在隔离分支通过本地前端 17/17、后端与部署入口 40/40、检索测试 4/4、Astro 检查和静态构建；公网 Preview 已 Ready，相关问题、未知问题和 Runtime Logs 验收通过。浏览器视觉验收仍需在登录或关闭 Deployment Protection 后完成，不能仅凭接口成功代替。

本地构建秘密扫描的初次模式命中来自压缩 JavaScript 中的 `mask-` CSS 字符串；复查没有发现 `OPENAI_API_KEY`、真实 `sk-` Key 或 HeiyuCode 地址。扫描结果不能替代线上构建和 Runtime Logs 检查。

## 9. 是否提升到 Production

- 免费 Function 时长能否稳定覆盖真实请求。
- 是否已经具备有效限流和额度保护。
- 是否修正“本地演示”“未来接入”等过时文案。
- 是否明确标注 Version 0 固定资料问答，而不是完整 RAG。
- 是否存在经过验证的回滚路径。

## 10. 阶段结论与下一步

- 当前结论：部署适配代码已完成，Preview 已可运行；环境变量已存在，不需要重复创建。
- 基线验证：隔离分支中的前端测试为 17/17，后端与部署入口测试为 40/40，另有 4 个检索测试；Astro 检查与静态构建均通过。
- 平台检查：Preview 构建生成 `api/index` 与 `api/[...path]` 两个 Python Function；健康检查和真实模型请求均已通过。Hobby Function 时长、Firewall 限流仍不能凭本地配置推断。
- 当前上线决策：先按 Preview-only 实施；在完成真实 Preview 验收、Function 时长验证和跨实例限流确认前，不配置 Production Key，也不提升 Production。
- 后续方向：先完成 Agent V1 Preview 的相关问题、未知问题和日志验收，再扩充资料，最后评估 Embedding、ChromaDB 和 LangChain。

### 下一次终端操作草稿

```bash
vercel ls --limit 10
vercel inspect <preview-url> --wait
vercel curl <preview-url>/api/health
vercel curl <preview-url>/api/chat -- --request POST \
  --header 'Content-Type: application/json' \
  --data '{"message":"请介绍一下吴禹的技术栈","history":[]}'
vercel logs <preview-url> --limit 50
```

恢复认证后，先在 Preview 环境配置服务端变量，再用 `vercel deploy` 或 GitHub Preview 构建；真实 Key 只通过交互式环境变量输入，不写入 shell 历史、仓库或博客。

## 写作素材清单

- [ ] 架构图
- [ ] Vercel Preview 构建截图
- [x] 健康检查和聊天接口的脱敏终端输出
- [ ] 冷热请求耗时表
- [ ] 浏览器远程模式与来源截图（Preview Deployment Protection 仍需登录后采集）
- [x] Vercel Runtime Logs 脱敏截图
- [ ] 限流 429 验证
- [ ] Production 提升或暂缓决定
