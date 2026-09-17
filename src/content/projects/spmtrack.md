---
title: SPMTrack 视觉目标跟踪系统
slug: spmtrack
summary: 将视觉跟踪研究代码封装成可演示、可复现、可部署的视频目标跟踪 Web 系统。
status: published
date: 2025.11 - 2026.06
category: 毕业设计项目
tags:
  - React
  - TypeScript
  - FastAPI
  - Docker
  - PyTorch
  - OpenCV
featured: true
externalUrl: https://github.com/BWBYB/SPMTrack
---

## 项目背景

SPMTrack 的上游实现是 CVPR 2025 的视觉目标跟踪研究代码。我负责围绕这套算法搭建一条面向浏览器用户的完整应用流程，把原本需要命令行和脚本串联的实验过程，整理成可以上传视频、选择目标、创建任务、查看日志和回放结果的 Web 系统。

## 交付形态

系统由四个运行层组成：React 前端工作台负责用户操作，Spring Boot 网关提供稳定的浏览器 API 边界，FastAPI 推理服务负责任务持久化和执行调度，跟踪引擎继续复用原有的 PyTorch、OpenCV 和评测脚本。

浏览器中的主流程是：上传视频 → 选择 ROI 和起始帧 → 创建任务 → 等待队列执行 → 查看阶段和日志 → 播放结果视频。应用支持单目标 `spmtrack`、多目标 `spmtrack_mot` 和传统基线 `csrt` 三种模式。

## 我的工作

### React + TypeScript 任务工作台

搭建视频上传、任务创建、历史任务、结果回放、日志查看、资产管理和监控页面，形成完整的浏览器端操作流程。使用 Canvas 实现浏览器内 ROI 框选，把视频坐标转换成推理服务使用的源帧坐标。

### Spring Boot 网关层

参与统一封装任务创建、任务查询、取消、重试、日志获取、结果视频访问以及输入输出文件管理等接口，并处理跨域、上传限制和错误透传等联调问题。网关为浏览器保持稳定的 `/api` 路径，把长任务执行交给推理服务。

### FastAPI 任务流程

将原有推理脚本纳入队列和状态机管理。终态包括 `PENDING`、`RUNNING`、`SUCCESS`、`FAILED` 和 `CANCELED`，执行阶段包括 `preparing`、`evaluating`、`rendering` 和 `transcoding`。服务同时负责 SQLite 任务记录、每任务日志、超时控制和进程取消。

### 监控、部署与验证

使用 Recharts 展示任务统计、运行状态和失败类型；使用 Docker 组织前端、网关和推理服务；配合健康检查和 smoke test 验证上传、创建任务、查看结果和取消任务等主链路。

## 工程复盘

这个项目最重要的变化不是把算法“放进网页”，而是把研究代码周围的边界补齐：浏览器只面对稳定的任务契约，网关负责输入和访问边界，推理服务负责长任务生命周期，底层脚本继续专注于跟踪和渲染。这样的拆分让系统更容易复现，也让调试和演示有了清晰的入口。
