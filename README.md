# 吴禹的个人作品集

一个正在从全栈工程走向 AI Agent 的个人作品集网站，使用 Astro、React 与 Tailwind CSS 构建。

网站以求职展示为目标，包含个人介绍、项目经历、博客入口、简历下载，以及支持本地演示与远程 Version 0 后端的个人知识库问答 Agent。

## 内容

- 个人首页：技术方向、能力关键词与求职定位
- 项目经历：完整展示 SPMTrack，其他项目暂标记为资料整理中
- 博客入口：为后续记录 RAG、Agent 和工程实践预留
- 关于我：教育经历、技术栈与校园经历
- 个人知识库 Agent：推荐问题、自由提问、加载状态和错误重试
- 简历下载：`public/resume/wu-yu-resume.pdf`

## 技术栈

- Astro 7
- React 19
- Tailwind CSS 4
- TypeScript
- Vitest + Testing Library

## 本地运行

### 前端

```bash
npm install
npm run dev
```

开发服务器默认运行在 `http://localhost:4321/`。生产构建和检查：

```bash
npm run test
npm run check
npm run build
```

未设置 `PUBLIC_AGENT_API_URL` 时，网站会继续使用本地演示回答。需要连接 Version 0 后端时，可以运行：

```bash
PUBLIC_AGENT_API_URL=http://localhost:8000 npm run dev
```

也可以将仓库根目录的 `.env.example` 复制为本地 `.env`。将 `PUBLIC_AGENT_API_URL` 留空会明确保持演示模式。

### Version 0 后端

后端需要 Python 3.11 或更高版本。首次运行时，在仓库根目录执行：

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
```

随后编辑 `backend/.env`，至少填写服务端使用的 `OPENAI_API_KEY`。如果中转站提供 OpenAI 兼容接口，同时填写 `OPENAI_BASE_URL`；模型名由 `OPENAI_MODEL` 指定。

从 `backend/` 目录启动服务：

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload --port 8000
```

健康检查位于 `GET http://localhost:8000/health`。它不调用模型，也不要求 API Key。

### 聊天接口

`POST /api/chat` 接收当前问题和最多 8 条历史消息：

```json
{
  "message": "SPMTrack 使用了哪些服务？",
  "history": [
    { "role": "user", "content": "你是谁？" },
    { "role": "assistant", "content": "我是吴禹。" }
  ]
}
```

成功响应包含回答、固定资料来源和远程模式标记：

```json
{
  "answer": "SPMTrack 由 React 工作台、Spring Boot 网关、FastAPI 推理服务和跟踪引擎组成。",
  "sources": ["个人资料", "SPMTrack 项目资料"],
  "mode": "remote"
}
```

缺少 `OPENAI_API_KEY` 等模型配置时接口返回 `503`；上游模型失败或超时时返回 `502`。公开错误只包含稳定提示，不包含供应商原始异常。

`OPENAI_API_KEY` 只由 FastAPI 后端读取，不能写入前端环境变量。真实的 `.env` 文件和 `backend/.venv/` 均不得提交到仓库；仓库只保留不含密钥的 `.env.example`。

## Agent 演进路线

网站现在支持本地演示数据和 Version 0 固定资料后端。后续可以按以下顺序演进：

1. 将简历、项目说明和博客切分为文档片段
2. 增加 embeddings 与向量检索
3. 根据部署需求选择 ChromaDB 等向量数据库
4. 再引入 LangChain，补充更细的来源引用、限流和日志

生产环境中，OpenAI 中转站密钥只放在后端环境变量，不提交到仓库。

## 项目资料

- SPMTrack：<https://github.com/BWBYB/SPMTrack>
- 设计文档：`docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md`
- 网站实施计划：`docs/superpowers/plans/2026-09-16-personal-portfolio-agent-plan.md`
- Version 0 Agent 实施计划：`docs/superpowers/plans/2026-09-18-version-0-personal-agent-plan.md`
