import type { AgentMessage, AgentResponse } from './types';

const source = 'SPMTrack 项目资料';

function response(answer: string, sources: string[] = [source]): AgentResponse {
	return { answer, sources, mode: 'demo' };
}

export function getDemoResponse(question: string, _history: AgentMessage[]): AgentResponse {
	const normalized = question.trim().toLowerCase();

	if (!normalized) {
		return response('请先输入一个问题，我会根据目前整理好的个人资料回答。', ['个人资料']);
	}

	if (normalized.includes('谁') || normalized.includes('介绍') || normalized.includes('背景')) {
		return response('我是吴禹，华侨大学计算机科学与技术专业 2026 届本科生，正在从全栈开发走向 AI Agent 开发。我的项目实践以 React、FastAPI、Spring Boot 和 Docker 为主。', ['个人资料']);
	}

	if (normalized.includes('spmtrack') && (normalized.includes('负责') || normalized.includes('做了什么') || normalized.includes('贡献'))) {
		return response('在 SPMTrack 中，我主要负责应用层的工程化交付：用 React + TypeScript 搭建视频任务工作台，实现 Canvas ROI 框选；参与 Spring Boot 网关接口封装；用 FastAPI 管理任务队列、状态机、日志和结果；同时参与 Recharts 监控、Docker 部署和 smoke test 验证。');
	}

	if (normalized.includes('技术') || normalized.includes('架构') || normalized.includes('为什么')) {
		return response('SPMTrack 把浏览器交互、网关、推理服务和跟踪引擎分成四层。React 负责任务工作台，Spring Boot 保持浏览器 API 稳定，FastAPI 负责长任务生命周期，底层继续复用 PyTorch、OpenCV 和原有脚本。这样可以让用户流程清晰，也便于调试和复现。');
	}

	if (normalized.includes('学习') || normalized.includes('agent') || normalized.includes('rag') || normalized.includes('方向')) {
		return response('我目前正在学习 AI Agent、RAG、LangChain 和向量数据库，希望把已有的全栈交付经验延伸到 AI 应用开发。这个网站本身会先作为知识库问答 Agent 的界面原型。', ['个人资料']);
	}

	if (normalized.includes('校园') || normalized.includes('辩论') || normalized.includes('学生会')) {
		return response('我曾在学院学生会办公室负责团务、会议执行和活动支持，也担任过学院辩论队副队长，参与管理 5 人核心团队、组织 4 场跨院友谊赛，并在任期内进入“新生杯”全校 8 强。', ['校园经历']);
	}

	return response('目前资料中没有这个问题的可靠答案。你可以试试询问我的项目经历、技术选择、学习方向或校园经历。', ['资料边界']);
}
