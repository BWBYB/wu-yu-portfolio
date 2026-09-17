import ChatPanel from './ChatPanel';

export default function AgentPreview({ compact = false }: { compact?: boolean }) {
	return (
		<div className={`agent-preview ${compact ? 'agent-preview--compact' : ''}`}>
			<div className="agent-preview__intro">
				<p className="eyebrow">DEMO MODE / 01</p>
				<h2>先问一个<br /><em>关于我的问题。</em></h2>
				<p>这是网站第一版的本地演示。回答来自我整理的简历和 SPMTrack 资料，未来会接入真正的知识库 Agent。</p>
			</div>
			<ChatPanel />
		</div>
	);
}
