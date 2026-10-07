# 个人知识库 Agent 线上预发布闭环设计

日期：2026-09-19
状态：对话中已批准总体架构，等待书面设计审核

## 1. 背景与目标

个人网站当前已经具备静态 Astro 页面、React 聊天界面和 FastAPI Version 0 问答后端。后端使用固定的个人资料与 SPMTrack 资料构造上下文，通过 HeiyuCode 的 Responses API 调用模型。真实本地验证已经证明 `/api/chat` 能返回远程回答和资料来源，但曾观察到约 52.57 秒的模型响应时间。

本阶段目标不是宣告正式稳定上线，而是在 0 托管成本约束下完成一次可回滚的线上预发布闭环：

```text
Vercel Preview 页面
  -> 同域 /api/chat
  -> Vercel Python Function 中的现有 FastAPI 应用
  -> HeiyuCode Responses API
  -> 页面显示回答、远程模式和资料来源
```

生产网站在 Preview 验收通过前保持不变。任何免费额度、执行时长或滥用防护门槛不满足时，结果应停留在 Preview，不以降低安全标准换取公开上线。

## 2. 已批准的架构决策

采用同一个 GitHub 仓库、同一个 Vercel 项目承载 Astro 静态页面与 Python Function。线上浏览器使用同域 `/api/chat`，不再依赖一个独立公网后端域名。

选择这一方案的原因：

- 不新增付费托管服务。
- 每个部署分支可以同时预览对应的前端与后端版本。
- 浏览器请求保持同域，避免 Preview URL 变化导致的 CORS 配置漂移。
- 服务端密钥仅进入 Python Function 环境，不出现在 Astro 客户端包中。
- Preview 经验证后可以提升为 Production，而不需要重新组合两套独立部署。

明确不采用的首选方案：

- 不先拆成两个 Vercel 项目；当前规模下会增加 URL、CORS 和环境变量协调成本。
- 不先使用会休眠的免费容器实例；模型请求本身已经较慢，额外冷启动会扩大超时风险。

## 3. 范围

### 本阶段包含

- 为现有 FastAPI 应用增加薄部署入口，不复制业务逻辑。
- 将公开线上接口统一为 `GET /api/health` 和 `POST /api/chat`。
- 保留现有本地开发方式和测试入口。
- 配置 Vercel Python Function 的文件打包与执行时长。
- 为指定部署分支配置 Preview 环境变量。
- 让线上前端通过相对地址 `/api/chat` 访问同一部署中的后端。
- 增加必要的部署测试、日志字段和安全边界。
- 完成 Preview 的 API、浏览器、日志和秘密泄漏检查。
- Preview 全部通过后，再由用户决定是否提升为 Production。

### 本阶段不包含

- LangChain、ChromaDB、embedding、切分和向量检索。
- 登录、用户账户或持久化聊天记录。
- 流式输出、多模型自动切换或后台队列。
- 独立数据库和复杂监控平台。
- 为满足上线而购买 Vercel 或其他托管服务。
- 自动修改 Production 环境或自动提升部署。

## 4. 组件与职责

### Astro 与 React 前端

- 保持静态构建。
- `askKnowledgeBase` 继续作为唯一远程调用边界。
- 本地未配置 `PUBLIC_AGENT_API_URL` 时保留演示模式。
- Preview 和 Production 将 `PUBLIC_AGENT_API_URL` 设置为 `/`，客户端由此请求同域 `/api/chat`。
- 请求过程中继续显示加载状态，失败后保留问题并提供重试。
- 远程成功响应显示 `远程模式` 和服务端返回的来源列表。

### Vercel 部署适配层

- 只负责让 Vercel Python Runtime 暴露已有 FastAPI `app`。
- 不在适配层重新实现 prompt、资料加载、请求校验或模型调用。
- 显式把 `backend/app/**` 与 `knowledge/**` 纳入 Function 部署包，避免动态路径读取导致线上缺少 Markdown 文件。
- 通过项目配置声明 Python Function 最大执行时长；实际可用上限必须在当前 Hobby 环境中通过 Preview 部署验证，不能只依据本地配置推断。

### FastAPI 应用

- 保留当前请求和响应结构。
- 新增或映射 `GET /api/health`，原有本地健康检查可以继续兼容。
- `POST /api/chat` 仍执行长度、历史条数与响应结构校验。
- 继续把配置问题映射为 503，把上游模型问题映射为稳定的公开错误，不返回供应商原始异常。

### HeiyuCode

- 继续使用服务端配置的 Responses API。
- API Key 只存在于 Vercel Preview/Production 的敏感环境变量中。
- 本阶段不改变供应商、不引入浏览器直连，也不把 Codex 本机配置文件复制到项目。

## 5. 路由与数据流

### 健康检查

```text
GET /api/health
  -> FastAPI
  -> {"status":"ok"}
```

健康检查不访问模型，不要求模型 Key，也不暴露模型名、供应商地址或配置状态。

### 聊天请求

```text
React ChatPanel
  -> askKnowledgeBase(question, history)
  -> POST /api/chat
  -> FastAPI validation
  -> load knowledge/profile.md and knowledge/spmtrack.md
  -> HeiyuCode Responses API
  -> { answer, sources, mode: "remote" }
  -> render answer and provenance
```

浏览器请求体只包含当前问题和最多 8 条历史消息。响应继续使用当前稳定契约，部署阶段不扩展协议字段。

## 6. 环境与秘密管理

### Preview 环境

第一轮只给指定部署分支配置：

- `OPENAI_API_KEY`
- `OPENAI_BASE_URL`
- `OPENAI_MODEL`
- `OPENAI_API_MODE`
- `LLM_TIMEOUT_SECONDS`
- `MAX_HISTORY`
- `MAX_MESSAGE_CHARS`
- `PUBLIC_AGENT_API_URL=/`

Preview 使用分支专用环境变量，避免任何普通分支预览自动获得模型 Key。Production 在 Preview 验收完成前不配置真实模型 Key。

### 安全约束

- `OPENAI_API_KEY` 必须作为服务端敏感变量，名称不得带 `PUBLIC_`。
- `.env`、Vercel 拉取的本地环境文件和真实响应日志不得提交 Git。
- 构建产物需要搜索供应商 Key 的特征片段与服务端变量名，确认客户端包没有秘密。
- 日志不得记录完整问题、完整回答、历史消息或供应商原始错误。

## 7. 超时与性能预算

当前前端请求上限是 75 秒，而一次真实模型调用曾耗时约 52.57 秒。线上闭环必须保证超时由内向外递增：

```text
上游模型超时 < Vercel Function 最大时长 < 浏览器请求上限
```

三层之间需要保留清理和错误响应时间，不能把三个值设成同一个数字。实施阶段先读取当前 Hobby 项目实际允许的最大 Function 时长，再用 Preview 冷启动与热请求数据确定最终预算。

硬门槛：

- 如果 Hobby 实际上限不能稳定容纳调用与错误返回，本阶段不得提升 Production。
- 如果连续真实请求出现接近浏览器上限的长尾，先降低上游延迟或重新设计交互，不继续增大等待时间掩盖问题。
- SDK 自动重试必须计入总时间预算；不能让单次超时乘以多次重试后超过 Function 或浏览器上限。

## 8. 滥用防护与 0 成本边界

现有消息长度和历史条数限制继续作为第一层输入保护，但它们不等同于频率限制。

Preview 阶段：

- 仅用于本人和受邀检查，不在简历或公开渠道宣传 URL。
- 检查当前 Vercel 项目是否能在 Hobby 免费范围内对 `/api/chat` 使用基于 IP 的 Firewall 频率限制。
- 同时为 HeiyuCode 账户设置可用的额度或余额上限，避免托管免费但模型调用失控。

Production 门槛：

- 必须有跨实例有效的请求频率限制或等价的平台级保护。
- 超限返回 429，不调用模型。
- 如果 Vercel Hobby 不提供可用的免费限流能力，则评估一个有明确免费额度的共享计数存储；若仍无法满足 0 成本约束，Agent 只保留 Preview，不公开 Production。
- 不采用 Python 进程内字典作为正式限流，因为无服务器实例之间不共享状态，重启后也会丢失。

## 9. 日志与可观察性

每个聊天请求记录结构化、脱敏的运行元数据：

- 请求 ID
- 部署环境与提交 SHA
- HTTP 结果类别
- 总耗时
- 问题字符数和历史消息条数
- 来源数量
- 错误类别，例如 validation、configuration、provider、timeout 或 rate_limit

不得记录问题正文、回答正文、API Key 或上游完整错误文本。Vercel Runtime Logs 用于 Preview 验收和短期故障定位，不作为聊天数据存储。

## 10. 错误与降级行为

- 422：请求为空、过长、历史过多或结构不合法。
- 429：超过公开频率限制，不调用上游模型。
- 502：上游模型失败、响应无效或在预算内没有完成。
- 503：服务端配置缺失。
- 浏览器网络错误或非 2xx：显示可重试的稳定提示，保留用户问题。
- 未设置 `PUBLIC_AGENT_API_URL`：网站保持明确的本地演示模式，不静默伪装成远程回答。

线上远程配置存在时，失败不得回退为演示回答，否则访客无法区分真实模型与固定答案。

## 11. Preview 验收

### 自动化检查

- 前端完整测试通过。
- 后端完整测试通过。
- Astro check 与生产构建通过。
- 部署适配层有测试证明它暴露的是现有 FastAPI app，而不是第二份实现。
- `/api/health`、输入限制、稳定错误和来源字段都有接口测试。

### 公网 API 检查

- `GET /api/health` 返回 200 和固定 JSON。
- `POST /api/chat` 返回 200、非空回答、`mode=remote` 和两个来源。
- 未知问题明确表示资料中没有信息，不进行推测。
- 连续执行至少 5 次真实问题，记录首请求、热请求、最快、最慢和平均耗时。
- 检查一次无效请求和一次超长请求，确认不会调用模型。

### 浏览器检查

- Preview 页面通过同域 `/api/chat` 得到真实回答。
- 页面显示远程模式和两个资料来源。
- 加载、失败、重试和清空行为正常。
- 桌面与移动宽度没有溢出或遮挡。
- 浏览器控制台没有错误，网络请求没有 CORS 失败。

### 部署与秘密检查

- Vercel 构建和 Runtime Logs 没有未处理异常。
- 客户端构建产物不包含 API Key 或服务端秘密。
- Preview 环境变量只作用于指定部署分支。
- 实测 Function 最大时长与配置一致。
- 已确认回滚到上一稳定部署的方法。

## 12. Production 提升门槛

只有以下条件全部满足，才向用户提出 Production 提升选项：

- Preview API 与浏览器端到端验收全部通过。
- 免费 Function 时长能够稳定覆盖真实请求。
- 免费托管用量处于可接受范围。
- 公开频率限制或等价保护有效。
- 生产密钥已作为敏感变量配置且未泄漏。
- 首页中“本地演示”“未来接入”等过时文案已经更正。
- 页面明确说明这是“Version 0 固定资料问答”，不声称已经完成 RAG。
- 存在经过验证的回滚路径。

Production 提升必须由用户明确批准。提升后重新执行健康检查、一次真实问答、浏览器验证和日志检查。

## 13. 分阶段交付与博客草稿

每完成一个阶段，同步更新 Markdown 草稿大纲：

1. 部署适配阶段：记录 Astro 与 FastAPI 如何进入同一 Preview。
2. 环境与安全阶段：记录密钥边界、分支环境变量和免费限流选择。
3. Preview 验收阶段：记录冷启动、真实耗时、错误案例和端到端证据。
4. Production 阶段：记录提升、生产 smoke test、回滚与最终结论。

草稿只记录脱敏配置名、验证方法和结果，不记录真实 Key、账户信息、完整供应商错误或可复用秘密。

## 14. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 模型响应加上云函数开销超过 75 秒 | 先测 Preview 冷热延迟；按内到外设置超时；不满足门槛则停止 Production |
| Python Function 未打包知识文件 | 显式包含 `knowledge/**`；线上问答验证来源与内容 |
| Preview URL 变化导致 CORS 失败 | 线上统一使用同域相对 API 地址 |
| 公共接口消耗模型额度 | Preview 不公开；Production 前必须启用跨实例限流和供应商额度上限 |
| Key 进入客户端构建 | 仅使用服务端变量；构建产物执行秘密扫描 |
| 快速迭代破坏正式站点 | 每个分支先生成 Preview；通过验收后才提升 Production |
| 免费平台限制发生变化 | 部署时读取当前项目配置并实测；不把旧文档或配置值当作运行证据 |
| Version 0 被误解为完整 RAG | 页面和博客明确标注固定资料问答与后续 RAG 路线 |

## 15. 参考资料

- Vercel FastAPI：<https://vercel.com/docs/frameworks/backend/fastapi>
- Vercel Python Runtime：<https://vercel.com/docs/functions/runtimes/python>
- Vercel Function Duration：<https://vercel.com/docs/functions/configuring-functions/duration>
- Vercel Preview 与 Production 提升：<https://vercel.com/docs/deployments/promote-preview-to-production>
- Vercel 环境变量：<https://vercel.com/docs/environment-variables/manage-across-environments>
