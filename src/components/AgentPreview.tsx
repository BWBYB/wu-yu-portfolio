import ChatPanel from './ChatPanel';

export default function AgentPreview({ compact = false }: { compact?: boolean }) {
	return (
		<div className={`agent-preview ${compact ? 'agent-preview--compact' : ''}`}>
			<div className="agent-preview__intro">
				<p className="eyebrow">RAG V1.1 / 01</p>
				<h2>先问一个<br /><em>关于我的问题。</em></h2>
				<p>线上 Preview 使用 FastAPI 和轻量检索，从已整理的简历与 SPMTrack 资料中选择相关片段再生成回答。本地未配置 API 时仍保留演示模式。</p>
			</div>
			<ChatPanel />
		</div>
	);
}
