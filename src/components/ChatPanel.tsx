import { RotateCcw, Send, Trash2 } from 'lucide-react';
import { useMemo, useState, type KeyboardEvent } from 'react';
import { askKnowledgeBase } from '@/lib/agent/client';
import type { AgentMessage } from '@/lib/agent/types';

type ChatPanelProps = {
	recommendedPrompts?: readonly string[];
};

const defaultPrompts = ['你是谁？', '你在 SPMTrack 里负责什么？', '为什么选择 React 和 FastAPI？', '你目前正在学习什么？'];

export default function ChatPanel({ recommendedPrompts = defaultPrompts }: ChatPanelProps) {
	const [messages, setMessages] = useState<AgentMessage[]>([]);
	const [input, setInput] = useState('');
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [failedQuestion, setFailedQuestion] = useState<string | null>(null);

	const hasMessages = messages.length > 0;
	const canSend = useMemo(() => input.trim().length > 0 && !isLoading, [input, isLoading]);

	async function submitQuestion(question: string) {
		const trimmed = question.trim();
		if (!trimmed || isLoading) return;
		const nextHistory: AgentMessage[] = [...messages, { role: 'user', content: trimmed }];
		setMessages(nextHistory);
		setInput('');
		setError(null);
		setFailedQuestion(null);
		setIsLoading(true);

		try {
			const result = await askKnowledgeBase(trimmed, messages);
			setMessages([...nextHistory, { role: 'assistant', content: result.answer }]);
		} catch {
			setError('这次回答没有生成成功，请重试。');
			setFailedQuestion(trimmed);
		} finally {
			setIsLoading(false);
		}
	}

	function handleSubmit(event: { preventDefault: () => void }) {
		event.preventDefault();
		void submitQuestion(input);
	}

	function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			void submitQuestion(input);
		}
	}

	function clearConversation() {
		setMessages([]);
		setInput('');
		setError(null);
		setFailedQuestion(null);
	}

	return (
		<div className="chat-panel">
			<div className="chat-panel__head">
				<div>
					<p className="eyebrow">PERSONAL KNOWLEDGE BASE</p>
					<h3>和我的资料聊聊</h3>
				</div>
				<button className="icon-button chat-panel__clear" type="button" aria-label="清空对话" title="清空对话" onClick={clearConversation}>
					<Trash2 size={16} strokeWidth={1.8} aria-hidden="true" />
				</button>
			</div>

			<div className="chat-panel__prompts" aria-label="推荐问题">
				{recommendedPrompts.map((prompt) => (
					<button className="prompt-chip" type="button" key={prompt} disabled={isLoading} onClick={() => void submitQuestion(prompt)}>{prompt}</button>
				))}
			</div>

			<div className="chat-panel__log" role="log" aria-live="polite" aria-label="对话记录">
				{!hasMessages && !isLoading && <p className="chat-panel__empty">还没有问题。可以从上面的推荐问题开始。</p>}
				{messages.map((message, index) => (
					<div className={`chat-message chat-message--${message.role}`} key={`${message.role}-${index}-${message.content}`}>
						<span className="chat-message__role">{message.role === 'user' ? '你' : 'WU YU · AGENT'}</span>
						<p>{message.content}</p>
						{message.role === 'assistant' && <span className="chat-message__mode">演示模式 · 基于当前整理的资料</span>}
					</div>
				))}
				{isLoading && <div className="chat-message chat-message--assistant chat-message--loading"><span className="chat-message__role">WU YU · AGENT</span><p>正在整理回答<span className="loading-dots" aria-hidden="true">...</span></p></div>}
			</div>

			{error && (
				<div className="chat-panel__error" role="alert">
					<span>{error}</span>
					{failedQuestion && <button className="text-button" type="button" onClick={() => void submitQuestion(failedQuestion)}><RotateCcw size={14} aria-hidden="true" /> 重试</button>}
				</div>
			)}

			<form className="chat-panel__form" onSubmit={handleSubmit}>
				<label className="sr-only" htmlFor="knowledge-question">向我的知识库提问</label>
				<textarea id="knowledge-question" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleInputKeyDown} placeholder="向我的知识库提问..." rows={1} disabled={isLoading} />
				<button className="send-button" type="submit" aria-label="发送" title="发送" disabled={!canSend}><Send size={16} strokeWidth={1.8} aria-hidden="true" /></button>
			</form>
		</div>
	);
}
