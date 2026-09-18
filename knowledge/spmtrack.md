# SPMTrack

SPMTrack 是一个将视觉跟踪研究代码封装成可演示、可复现、可部署的视频目标跟踪 Web 系统的毕业设计项目，时间为 2025.11 - 2026.06。

上游实现是 CVPR 2025 的视觉目标跟踪研究代码。项目把原本需要命令行和脚本串联的实验过程整理为浏览器流程：上传视频、选择 ROI 和起始帧、创建任务、等待队列执行、查看阶段和日志、播放结果视频。

系统由 React 前端工作台、Spring Boot 网关、FastAPI 推理服务和复用 PyTorch、OpenCV 及评测脚本的跟踪引擎组成。支持单目标 `spmtrack`、多目标 `spmtrack_mot` 和传统基线 `csrt` 三种模式。吴禹负责前端任务工作台、参与网关接口封装，并将原有推理脚本纳入队列和状态机管理；还参与监控、部署与主链路验证。

Source: src/content/projects/spmtrack.md
