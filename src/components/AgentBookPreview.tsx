import ChatPanel from './ChatPanel';

const recommendedPrompts = [
	'什么是 Agent？',
	'用户记忆和知识库有什么区别？',
	'RAG 是如何增强知识库问答的？',
	'模型 API 的消息有哪些角色？',
];

export default function AgentBookPreview() {
	return (
		<div className="agent-preview agent-book-preview">
			<div className="agent-preview__intro">
				<p className="eyebrow">AGENT BOOK / RAG</p>
				<h2>把学习资料，<br /><em>变成可问的知识。</em></h2>
				<p>这是 Agent Book 学习资料的本地 Agentic RAG 问答。回答只来自已导入的学习资料，并显示实际检索到的来源。</p>
			</div>
			<ChatPanel variant="agent-book" recommendedPrompts={recommendedPrompts} />
		</div>
	);
}
