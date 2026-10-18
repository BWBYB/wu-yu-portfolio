# Agent 工作台设计

日期：2026-10-08  
状态：已批准，进入实现

## 1. 目标

在现有 Astro 个人网站中增加一个独立的 `/agent/` 工作台页面，提供类似 ChatGPT 的对话体验。首页继续保持当前个人网站的信息架构和暖色编辑风格；工作台承载更完整的 Agent 交互，不覆盖首页已有的 `ChatPanel`。

## 2. 用户流程

1. 用户从网站导航进入 `/agent/`。
2. 左侧显示当前助手、对话列表和新建对话按钮；默认助手为“了解 WU YU”。
3. 用户可在助手菜单切换“了解 WU YU”和“AI-Agent-Book”。
4. 用户点击推荐问题或输入问题，工作台根据当前助手调用既有的 `askKnowledgeBase()` 或 `askAgentBook()` 适配器。
5. 回复下方显示复制、引用和时间；引用资料以悬浮面板展开，不改变对话正文高度。
6. 对话标题、当前助手、主题和侧栏折叠状态保存到浏览器 `localStorage`，刷新后恢复。

## 3. 组件边界

### `AgentWorkspace.tsx`

负责工作台状态、会话切换、发送请求、错误/重试、助手切换、主题设置和侧栏状态。它只依赖 `src/lib/agent/client.ts` 的两个既有函数，不读取 API key。

### `agent.astro`

负责页面路由和 Astro hydration，使用 `BaseLayout` 提供网站头部、页脚、SEO 和跳过链接。

### `global.css`

新增 `.agent-workspace*` 样式命名空间，包括桌面侧栏、折叠态、移动抽屉、主题变量、消息操作和悬浮引用面板。不得改变现有 `.chat-panel*` 首页组件的视觉契约。

### `SiteHeader.astro` 与 `MobileMenu.tsx`

把现有“和我的 Agent 聊聊”入口指向 `/agent/`，并在桌面导航中标记工作台入口；不改变其他导航路径。

## 4. 状态与数据

```ts
type WorkspaceAgentId = 'personal' | 'book';

type WorkspaceConversation = {
  id: string;
  agent: WorkspaceAgentId;
  title: string;
  messages: AgentMessage[];
  providerConversationId?: string;
  updatedAt: number;
};
```

持久化键为 `wuyu-agent-workspace-v1`。读取 localStorage 失败、数据格式不完整或 JSON 损坏时回退到一个空的默认会话，不阻塞页面。

个人助手请求使用：

```ts
askKnowledgeBase(question: string, history: AgentMessage[]): Promise<AgentResponse>
```

Agent Book 请求使用：

```ts
askAgentBook(question: string, conversationId: string | null): Promise<AgentBookResponse>
```

## 5. 交互要求

- 助手选择器位于对话列表上方；折叠后只保留可识别的切换按钮。
- “对话”标题右侧使用加号新建对话，悬浮显示“新建对话”。
- 会话整行可打开；重命名和删除操作固定在行右侧，不触发行点击。
- 侧栏折叠为一个按钮；折叠态显示窄 rail，不显示长标题。
- 设置位于工作台右上角；主题选项在浮动二级菜单中，展开不改变设置按钮尺寸。
- 回复操作包含复制、引用、时间；引用面板为绝对定位悬浮层。
- 输入框使用自然 placeholder，不额外显示“输入消息”可见标签；保留屏幕阅读器标签。
- Enter 发送，Shift+Enter 换行；加载期间禁用重复提交。
- 失败时保留问题并提供重试；清空对话必须取消过期响应对当前会话的影响。

## 6. 非目标

- 不修改 FastAPI、Dify、ChromaDB 或任何后端配置。
- 不在浏览器中加入 API key。
- 不把原型文件复制到正式站，也不删除 `.superpowers/` 原型。
- 不引入新的 UI 组件库；使用现有 React、Lucide React 和全局 CSS。

## 7. 验收标准

- `/agent/` 可通过网站导航访问，静态构建成功。
- 两个助手均能调用对应现有适配器，个人助手无 API 配置时仍可演示，Agent Book 配置错误时显示可理解错误。
- 新建、整行切换、重命名、删除、清空、重试和引用面板行为可测试。
- 桌面展开/折叠和移动端宽度无横向溢出。
- 主题设置、会话和助手选择刷新后可恢复。
- `npm run check`、`npm run build` 和排除 worktree 后的 `npm test` 全部通过。
