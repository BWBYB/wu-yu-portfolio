# Agent 公开前保护层设计

## 1. 背景与目标

个人知识库 Agent V1 已在 Vercel Preview 完成浏览器、API、检索边界和 Runtime Logs 验收。当前接口已经具备消息长度限制、历史条数限制、模型调用超时和“无检索命中不调用模型”的成本边界，但 `POST /api/chat` 仍缺少跨实例有效的请求频率限制。

本阶段目标是在不扩充知识资料、不引入付费运行时依赖、不提升 Production 的前提下，为公开 Agent 建立可验证的基础滥用防护：

- 使用 Vercel Firewall 对 `POST /api/chat` 按 IP 计数。
- 先观察、后在 Preview 执行 429，避免直接影响真实访问。
- 让前端明确区分限流与模型失败。
- 使用不会调用模型的问题验收规则，避免测试本身消耗模型额度。
- 将中转站账户额度上限保留为正式公开前的最终成本保险。

## 2. 已确认的现状

### 应用层

- `/api/chat` 限制单条消息最多 2000 个字符、历史最多 8 条。
- 模型客户端超时为 30 秒，Vercel Function 最大时长为 60 秒，浏览器请求上限为 75 秒。
- 无检索命中时，FastAPI 直接返回固定边界回答，不构造 Prompt，也不调用模型。
- FastAPI 日志已经能够把应用内 429 归类为 `rate_limit`，但 Vercel Firewall 在请求进入 Function 前生效，因此 Firewall 拦截不会出现在应用 Runtime Log 中。
- 前端当前把所有非 2xx 响应统一显示为“这次回答没有生成成功，请重试”，不能解释 429。

### Vercel 项目

2026-09-19 的只读检查结果：

- Vercel 系统级防护处于活动状态。
- 项目当前没有自定义 Firewall 规则、IP Block 或待发布草稿。
- Custom Firewall Rules 在项目上显示为可配置。
- IP Bypass 需要 Pro/Enterprise，OWASP 规则集需要额外套餐；本阶段不依赖这些能力。
- Vercel Firewall IP 频率计数按区域维护，不是严格的全球共享计数器。

CLI 显示“可配置”不等于已证明 Hobby 账户能够成功创建并发布该频率规则。规则创建阶段必须把平台是否接受配置作为一个显式验收点；若平台拒绝，不绕过套餐限制。

## 3. 方案选择

### 采用：Vercel Firewall 分阶段 IP 限流

优点：

- 在请求进入 Python Function 和模型调用之前生效。
- 不增加 Python 依赖、数据库、凭据或新的常驻服务。
- 适合当前低流量求职展示网站。
- 可以先记录匹配情况，再逐步执行 429。

限制：

- 按 IP 计数可能影响共享网络，也可能被多 IP 绕过。
- 计数按 Vercel 区域维护，不能作为严格的全局模型预算。
- Firewall 流量与应用 Runtime Logs 分属不同观察面。

### 暂不采用：共享 Redis/Upstash 计数

共享存储可以提供更精确的跨实例计数和自定义额度窗口，但会增加外部服务、环境变量、失败模式与免费额度依赖。当前流量和求职展示目标不足以证明这部分复杂度有必要。

### 不接受：只隐藏 Preview URL

隐藏 URL、消息长度和历史限制不能限制重复模型调用，不满足公开 Agent 的上线门槛。

## 4. 分层保护架构

```text
Browser
  -> Vercel system protection
  -> Vercel Firewall rule for POST /api/chat
  -> FastAPI validation and lexical retrieval
       -> no match: deterministic 200, no model call
       -> match: bounded prompt and model call
  -> HeiyuCode account quota / balance cap
```

各层职责：

- Vercel 系统保护：处理平台识别的 DDoS 流量，不由应用配置。
- Firewall 规则：限制单一 IP 对模型入口的突发请求。
- FastAPI：校验请求规模、控制知识边界和模型超时。
- 中转站额度上限：控制 Firewall 无法覆盖的多 IP、跨区域或长期累计消费。

任何一层都不能被描述为“完全防止费用”。Production 公开需要 Firewall 执行规则和供应商额度上限同时存在。

## 5. Firewall 规则契约

规则名称使用稳定、可检索的英文名称：`Agent chat per-IP limit`。

匹配条件：

- `path` 等于 `/api/chat`
- `method` 等于 `POST`

计数配置：

- 固定窗口 60 秒
- 每个 IP 最多 10 次
- 超限动作在不同阶段切换

`GET /api/health`、静态页面和其他请求不得匹配此规则。

### 阶段 1：只记录

- 使用 `rate_limit` 计数配置。
- 超限动作设为 `log`。
- 不加入环境条件，以便确认真实匹配范围，但不拦截任何请求。
- 创建后只形成 Vercel 草稿；先检查 `vercel firewall diff`，由用户亲自在终端发布。

### 阶段 2：仅 Preview 执行

- 保留路径、方法、窗口、阈值和 IP key。
- 增加 `environment = preview` 条件。
- 超限动作改为标准 `rate_limit`，预期返回 HTTP 429。
- 修改后再次检查完整条件，防止 `edit` 覆盖条件时误删路径或方法。
- 仍由用户亲自在终端发布。

### 阶段 3：Production 决策

本规格不配置 Production、不移除 `environment = preview` 条件，也不提升部署。只有满足以下条件后，才能另行确认 Production 执行：

- Preview 429 验收通过。
- Firewall 流量检查未发现合法访问被误伤。
- 中转站账户已经设置可接受的额度或余额上限。
- 用户再次明确批准 Production。

## 6. 前端 429 行为

`src/lib/agent/client.ts` 增加可辨识的远程请求错误，至少保留 HTTP status。它不解析 Firewall 可能返回的 HTML，也不向界面暴露原始响应正文。

`src/components/ChatPanel.tsx` 根据错误类型显示：

- 429：`请求有点频繁，请稍后再试。`
- 其他网络、配置或模型错误：保留 `这次回答没有生成成功，请重试。`

429 状态不显示立即重试按钮，避免界面鼓励用户连续触发相同窗口；输入框在请求结束后恢复可用。普通失败继续保留现有手动重试行为。

不增加倒计时，因为 Vercel Firewall 是否提供稳定 `Retry-After` 还未验证，伪造倒计时会给出错误承诺。

## 7. 验证策略

### 自动化测试

- Agent client 在 429 时抛出带 `status=429` 的可辨识错误。
- Agent client 对 502/503 和无效响应继续保持现有行为。
- ChatPanel 在 429 时显示专用提示且不显示重试按钮。
- ChatPanel 在普通失败时仍显示通用提示与重试按钮。
- 前端全部测试、Astro check 和 Astro build 继续通过。
- 后端完整测试继续通过，证明前端改动没有改变 API 契约。

### Firewall 草稿检查

- `vercel firewall rules inspect` 显示规则只匹配 `POST /api/chat`。
- `vercel firewall diff` 不包含 IP Block、Attack Mode、Bot Protection 或其他无关变更。
- 阶段 1 超限动作是 `log`；阶段 2 才是 Preview 429。

### Preview 验收

等待一个新的 60 秒计数窗口后，使用同一 IP 在窗口内发送 11 次未知问题，例如“你最喜欢什么颜色？”。这些请求会经过 Firewall，但在 FastAPI 检索后短路，不调用中转站模型。

阶段 1 预期：

- 11 次请求均不因本规则被拒绝。
- Firewall 流量中出现该规则的匹配或超限记录。
- Runtime Logs 中未知问题仍为 `retrieved_chunks: 0`，没有中转站请求。

阶段 2 预期：

- 窗口内前 10 次请求正常处理。
- 后续请求至少一次返回 429。
- 浏览器显示专用频率提示，不显示立即重试按钮。
- `/api/health` 和静态页面仍可访问。

如果 Vercel CLI、Deployment Protection 或区域路由导致本地突发测试不能稳定命中同一计数器，改用 Firewall Traffic 证据和浏览器手动复验，不通过提高请求数量来制造模型费用。

## 8. 错误处理与回退

- Firewall 规则创建被套餐拒绝：停止本方案的实施，记录平台限制，Agent 保持 Preview-only；不自动接入 Redis。
- 规则误匹配合法流量：把规则恢复为 `log` 或禁用草稿，检查完整条件后重新发布。
- 前端无法识别 Firewall 429：保留 HTTP status，不依赖响应 JSON；用真实 Preview 响应修正测试夹具。
- Firewall 配置变更不能通过代码回滚：博客和实施记录必须保存规则名、阶段、diff 和手动恢复命令。
- 不启用 Attack Mode，不暂停系统级防护，不创建宽泛的路径或 User-Agent 拦截规则。

## 9. 文档与阶段草稿

更新 `src/content/posts/online-preview-deployment.md`，记录：

- 为什么输入限制不等于频率限制。
- Hobby 项目的实际 Firewall 能力检查结果。
- log -> Preview 429 -> Production 决策的分阶段原因。
- 使用未知问题验收以避免模型费用的方法。
- IP/区域计数的局限和供应商额度上限的必要性。

文档不得记录访问者 IP、API Key、OIDC token、完整问题正文或供应商原始响应。

## 10. 非目标

- 不扩充简历、项目或博客知识语料。
- 不接入 LangChain、ChromaDB、Embedding 或 Redis。
- 不实现用户登录、验证码、永久封禁或自定义管理后台。
- 不启用付费 OWASP、IP Bypass 或 Observability Plus。
- 不提升 Production，不配置 Production 模型 Key。
- 不宣称基础 IP 限流等同于严格成本预算或完整安全体系。

## 11. 完成标准

本阶段在以下条件同时满足时完成：

- 前端能明确处理 429，自动化测试与构建通过。
- Firewall 阶段 1 草稿经过检查并由用户发布。
- Firewall 阶段 2 在 Preview 返回可复现的 429。
- 未知问题突发验收没有产生模型调用。
- 阶段博客大纲已更新。
- Production 保持未提升状态。
