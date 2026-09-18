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

- 待补：Vercel 部署适配文件与路由说明。
- 待补：为什么不在浏览器中直接调用模型。

## 4. 部署适配阶段

- 复用现有 FastAPI app，不复制业务代码。
- 显式打包 `backend/app/**` 与 `knowledge/**`。
- 增加 `/api/health` 与 `/api/chat` 的线上验证；本地 `/health` 继续兼容。
- 前端在 `PUBLIC_AGENT_API_URL=/` 时使用同域 `/api/chat`，未设置变量时仍保持演示模式。
- 已加入脱敏结构化日志：请求 ID、路由、状态、耗时、输入长度/历史条数、来源数和错误类别。
- 待补：首次 Preview 构建日志和健康检查结果。当前机器尚未安装 Vercel CLI，无法执行公网部署。

## 5. 超时与冷启动

- 本地真实模型请求曾耗时约 52.57 秒。
- 超时需要满足：上游模型 < 云函数 < 浏览器。
- 免费 Hobby 环境的实际 Function 上限必须通过部署验证。
- 待补：冷请求、热请求、最快、最慢和平均耗时。

## 6. 环境变量与密钥边界

- 模型 Key 只进入服务端敏感变量。
- Preview 使用指定分支的环境变量，Production 暂不配置。
- 前端只获得 `PUBLIC_AGENT_API_URL=/`，不能获得模型 Key。
- 待补：客户端构建产物秘密扫描方法与结果。

## 7. 免费条件下的滥用防护

- 消息长度和历史条数限制只是输入保护，不是频率限制。
- Preview URL 暂不公开。
- Production 前需要跨实例有效的免费限流或等价保护。
- 待补：Vercel Hobby 当前可用能力与最终选择。
- 待补：429 验证和供应商额度上限。

## 8. Preview 端到端验收

- [ ] `/api/health` 返回 200。
- [ ] `/api/chat` 返回回答、远程模式和两个来源。
- [ ] 未知问题不会编造。
- [ ] 连续真实请求完成并记录耗时。
- [ ] 页面显示远程回答和来源。
- [ ] 移动端、错误、重试和清空状态正常。
- [ ] Runtime Logs 和浏览器控制台没有未处理错误。

当前状态：代码已在隔离分支通过本地前端 17/17、后端 32/32、Astro 检查和静态构建；公网验收尚未开始。需要先恢复 GitHub CLI 登录并安装/登录 Vercel CLI，再配置 Preview 环境变量。

## 9. 是否提升到 Production

- 免费 Function 时长能否稳定覆盖真实请求。
- 是否已经具备有效限流和额度保护。
- 是否修正“本地演示”“未来接入”等过时文案。
- 是否明确标注 Version 0 固定资料问答，而不是完整 RAG。
- 是否存在经过验证的回滚路径。

## 10. 阶段结论与下一步

- 当前结论：架构与实施计划已批准，部署代码仍待实现。
- 基线验证：隔离分支中的前端测试为 16/16，后端测试为 27/27，Astro 检查与静态构建均通过。
- 平台检查：本机尚未安装 Vercel CLI，且当前无法从项目账户读取 Hobby Function 时长、Firewall 限流或环境变量状态；这些能力不能凭本地配置推断。
- 当前上线决策：先按 Preview-only 实施；在完成真实 Preview 验收、Function 时长验证和跨实例限流确认前，不配置 Production Key，也不提升 Production。
- 后续方向：线上 Version 0 稳定后再进入 RAG Version 1。

### 下一次终端操作草稿

```bash
gh auth login -h github.com
npm install --global vercel
vercel login
vercel link
vercel env ls preview
git push -u <github-remote> codex/online-preview-closure
```

恢复认证后，先在 Preview 环境配置服务端变量，再用 `vercel deploy` 或 GitHub Preview 构建；真实 Key 只通过交互式环境变量输入，不写入 shell 历史、仓库或博客。

## 写作素材清单

- [ ] 架构图
- [ ] Vercel Preview 构建截图
- [ ] 健康检查和聊天接口的脱敏终端输出
- [ ] 冷热请求耗时表
- [ ] 浏览器远程模式与来源截图
- [ ] Vercel Runtime Logs 脱敏截图
- [ ] 限流 429 验证
- [ ] Production 提升或暂缓决定
