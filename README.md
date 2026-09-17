# 吴禹的个人作品集

一个正在从全栈工程走向 AI Agent 的个人作品集网站，使用 Astro、React 与 Tailwind CSS 构建。

网站以求职展示为目标，包含个人介绍、项目经历、博客入口、简历下载，以及一个可替换为真实后端的个人知识库问答 Agent 演示。

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

## Agent 演进路线

当前网站使用本地演示数据，前端已经通过适配层封装问答调用。后续可以按以下顺序接入真实能力：

1. 使用 FastAPI 提供 `/api/chat`
2. 先将个人资料拼接为上下文，让模型完成基础问答
3. 将简历、项目说明和博客切分为文档片段
4. 增加 embeddings 与向量检索
5. 根据部署需求选择 ChromaDB 等向量数据库
6. 再引入 LangChain，补充来源引用、超时、限流和日志

生产环境中，OpenAI 中转站密钥只放在后端环境变量，不提交到仓库。

## 项目资料

- SPMTrack：<https://github.com/BWBYB/SPMTrack>
- 设计文档：`docs/superpowers/specs/2026-09-16-personal-portfolio-agent-design.md`
- 实施计划：`docs/superpowers/plans/2026-09-16-personal-portfolio-agent-plan.md`
