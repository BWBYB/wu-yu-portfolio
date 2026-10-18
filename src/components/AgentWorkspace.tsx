import {
	Bot,
	Check,
	ChevronDown,
	Copy,
	Menu,
	MessageSquare,
	Moon,
	PanelLeftClose,
	PanelLeftOpen,
	Plus,
	Quote,
	Send,
	Settings2,
	Sun,
	Trash2,
	X,
	Monitor,
} from 'lucide-react';
import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent } from 'react';
import { askAgentBook, askKnowledgeBase } from '@/lib/agent/client';
import type { AgentBookResponse, AgentMessage, AgentResponse } from '@/lib/agent/types';

type WorkspaceAgentId = 'personal' | 'book';
type WorkspaceTheme = 'system' | 'light' | 'warm' | 'dark';

type WorkspaceConversation = {
	id: string;
	agent: WorkspaceAgentId;
	title: string;
	messages: AgentMessage[];
	providerConversationId?: string;
	updatedAt: number;
};

type WorkspaceState = {
	activeAgent: WorkspaceAgentId;
	selected: Record<WorkspaceAgentId, string>;
	conversations: Record<WorkspaceAgentId, WorkspaceConversation[]>;
	collapsed: boolean;
	theme: WorkspaceTheme;
};

const STORAGE_KEY = 'wuyu-agent-workspace-v1';
const agents: Record<WorkspaceAgentId, { name: string; mark: string; hint: string; prompts: string[]; welcome: string; description: string }> = {
	personal: {
		name: '了解 WU YU', mark: '我', hint: '关于我的项目与经历',
		prompts: ['你是谁？', '你在 SPMTrack 里负责什么？', '为什么选择 React 和 FastAPI？', '你目前正在学习什么？'],
		welcome: '你好，我是吴禹。', description: '可以问我项目经历、技术选择和学习方向。',
	},
	book: {
		name: 'AI-Agent-Book', mark: '书', hint: 'Agent 学习资料问答',
		prompts: ['什么是 Agent？', '用户记忆和知识库有什么区别？', 'RAG 是如何增强知识库问答的？', '模型 API 的消息有哪些角色？'],
		welcome: '把学习资料，变成可问的知识。', description: '回答来自已导入的 Agent Book 学习资料。',
	},
};
const themeOptions: { id: WorkspaceTheme; label: string; Icon: typeof Sun }[] = [
	{ id: 'system', label: '跟随系统', Icon: Monitor },
	{ id: 'light', label: '极简灰白', Icon: Sun },
	{ id: 'warm', label: '暖色', Icon: Sun },
	{ id: 'dark', label: '深色', Icon: Moon },
];

function newId() {
	return `chat-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function makeConversation(agent: WorkspaceAgentId, title = '开始对话'): WorkspaceConversation {
	return { id: newId(), agent, title, messages: [], updatedAt: Date.now() };
}

function createInitialState(): WorkspaceState {
	const personal = makeConversation('personal');
	const book = makeConversation('book');
	return {
		activeAgent: 'personal', selected: { personal: personal.id, book: book.id },
		conversations: { personal: [personal], book: [book] }, collapsed: false, theme: 'system',
	};
}

function isAgent(value: unknown): value is WorkspaceAgentId {
	return value === 'personal' || value === 'book';
}

function isTheme(value: unknown): value is WorkspaceTheme {
	return value === 'system' || value === 'light' || value === 'warm' || value === 'dark';
}

function validMessage(value: unknown): value is AgentMessage {
	if (!value || typeof value !== 'object') return false;
	const message = value as Record<string, unknown>;
	return (message.role === 'user' || message.role === 'assistant') && typeof message.content === 'string';
}

function readWorkspaceState(): WorkspaceState {
	const fallback = createInitialState();
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (!raw) return fallback;
		const value: unknown = JSON.parse(raw);
		if (!value || typeof value !== 'object') return fallback;
		const saved = value as Partial<WorkspaceState>;
		if (!isAgent(saved.activeAgent) || !saved.conversations || typeof saved.conversations !== 'object') return fallback;
		const conversations = {} as WorkspaceState['conversations'];
		for (const agent of ['personal', 'book'] as const) {
			const list = saved.conversations[agent];
			if (!Array.isArray(list)) return fallback;
			conversations[agent] = list.filter((item): item is WorkspaceConversation => Boolean(
				item && typeof item.id === 'string' && typeof item.title === 'string' &&
				item.agent === agent && Array.isArray(item.messages) && item.messages.every(validMessage),
			)).map((item) => ({ ...item, updatedAt: Number(item.updatedAt) || Date.now() }));
			if (!conversations[agent].length) conversations[agent] = [makeConversation(agent)];
		}
		const selected = { personal: '', book: '' };
		for (const agent of ['personal', 'book'] as const) {
			const candidate = saved.selected?.[agent];
			selected[agent] = conversations[agent].some((chat) => chat.id === candidate) ? candidate! : conversations[agent][0]!.id;
		}
		return {
			activeAgent: saved.activeAgent,
			selected,
			conversations,
			collapsed: Boolean(saved.collapsed),
			theme: isTheme(saved.theme) ? saved.theme : 'system',
		};
	} catch {
		return fallback;
	}
}

function responseTime(timestamp: number) {
	return new Intl.DateTimeFormat('zh-CN', { hour: '2-digit', minute: '2-digit' }).format(new Date(timestamp));
}

function safeTitle(question: string) {
	const value = question.trim();
	return value.length > 30 ? `${value.slice(0, 29)}…` : value;
}

export default function AgentWorkspace() {
	const [workspace, setWorkspace] = useState<WorkspaceState>(createInitialState);
	const [input, setInput] = useState('');
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);
	const [failedQuestion, setFailedQuestion] = useState<string | null>(null);
	const [agentMenuOpen, setAgentMenuOpen] = useState(false);
	const [settingsOpen, setSettingsOpen] = useState(false);
	const [citationsOpen, setCitationsOpen] = useState<Record<string, boolean>>({});
	const [copiedMessage, setCopiedMessage] = useState<string | null>(null);
	const [mobileOpen, setMobileOpen] = useState(false);
	const [storageReady, setStorageReady] = useState(false);
	const requestVersion = useRef(0);
	const agent = agents[workspace.activeAgent];
	const chats = workspace.conversations[workspace.activeAgent];
	const currentChat = chats.find(({ id }) => id === workspace.selected[workspace.activeAgent]) ?? chats[0];
	const sidebarCollapsed = workspace.collapsed && !mobileOpen;

	useEffect(() => {
		setWorkspace(readWorkspaceState());
		setStorageReady(true);
	}, []);

	useEffect(() => {
		if (!storageReady) return;
		try {
			window.localStorage.setItem(STORAGE_KEY, JSON.stringify(workspace));
		} catch {
			// Private browsing or a full storage quota should not block chat use.
		}
	}, [storageReady, workspace]);

	function updateConversation(id: string, update: (conversation: WorkspaceConversation) => WorkspaceConversation) {
		setWorkspace((current) => ({
			...current,
			conversations: {
				...current.conversations,
				[current.activeAgent]: current.conversations[current.activeAgent].map((chat) => chat.id === id ? update(chat) : chat),
			},
		}));
	}

	function selectConversation(id: string) {
		requestVersion.current += 1;
		setLoading(false);
		setError(null);
		setFailedQuestion(null);
		setWorkspace((current) => ({ ...current, selected: { ...current.selected, [current.activeAgent]: id } }));
		setMobileOpen(false);
	}

	function newConversation() {
		requestVersion.current += 1;
		const conversation = makeConversation(workspace.activeAgent);
		setWorkspace((current) => ({
			...current,
			selected: { ...current.selected, [current.activeAgent]: conversation.id },
			conversations: { ...current.conversations, [current.activeAgent]: [conversation, ...current.conversations[current.activeAgent]] },
		}));
		setLoading(false);
		setInput('');
		setError(null);
		setFailedQuestion(null);
		setMobileOpen(false);
	}

	function switchAgent(next: WorkspaceAgentId) {
		requestVersion.current += 1;
		setLoading(false);
		setError(null);
		setFailedQuestion(null);
		setAgentMenuOpen(false);
		setWorkspace((current) => ({ ...current, activeAgent: next }));
	}

	function removeConversation(event: MouseEvent<HTMLButtonElement>, id: string) {
		event.stopPropagation();
		requestVersion.current += 1;
		setWorkspace((current) => {
			const remaining = current.conversations[current.activeAgent].filter((chat) => chat.id !== id);
			const nextChats = remaining.length ? remaining : [makeConversation(current.activeAgent)];
			const selected = current.selected[current.activeAgent] === id ? nextChats[0].id : current.selected[current.activeAgent];
			return {
				...current,
				selected: { ...current.selected, [current.activeAgent]: selected },
				conversations: { ...current.conversations, [current.activeAgent]: nextChats },
			};
		});
		setLoading(false);
		setError(null);
		setFailedQuestion(null);
	}

	function renameConversation(event: MouseEvent<HTMLButtonElement>, chat: WorkspaceConversation) {
		event.stopPropagation();
		const title = window.prompt('修改对话标题', chat.title);
		if (title?.trim()) updateConversation(chat.id, (current) => ({ ...current, title: title.trim() }));
	}

	function clearCurrentConversation() {
		if (!currentChat) return;
		requestVersion.current += 1;
		updateConversation(currentChat.id, (chat) => ({ ...chat, title: '新对话', messages: [], providerConversationId: undefined, updatedAt: Date.now() }));
		setLoading(false);
		setInput('');
		setError(null);
		setFailedQuestion(null);
		setCitationsOpen({});
	}

	async function send(question: string, retry = false) {
		const value = question.trim();
		if (!value || loading || !currentChat) return;
		const chatId = currentChat.id;
		const selectedAgent = workspace.activeAgent;
		const history = retry ? currentChat.messages.slice(0, -1) : currentChat.messages;
		if (!retry) {
			updateConversation(chatId, (chat) => ({
				...chat,
				title: chat.messages.length === 0 ? safeTitle(value) : chat.title,
				messages: [...chat.messages, { role: 'user', content: value }],
				updatedAt: Date.now(),
			}));
		}
		setInput('');
		setError(null);
		setFailedQuestion(null);
		setLoading(true);
		const version = ++requestVersion.current;
		try {
			const result: AgentResponse | AgentBookResponse = selectedAgent === 'book'
				? await askAgentBook(value, currentChat.providerConversationId ?? null)
				: await askKnowledgeBase(value, history);
			if (requestVersion.current !== version) return;
			updateConversation(chatId, (chat) => ({
				...chat,
				providerConversationId: result.mode === 'local-rag' ? result.conversation_id : chat.providerConversationId,
				messages: [...chat.messages, { role: 'assistant', content: result.answer, sources: result.sources, mode: result.mode }],
				updatedAt: Date.now(),
			}));
		} catch (caught) {
			if (requestVersion.current !== version) return;
			setError(caught instanceof Error ? caught.message : '这次回答没有生成成功，请重试。');
			setFailedQuestion(value);
		} finally {
			if (requestVersion.current === version) setLoading(false);
		}
	}

	function handleComposerKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
		if (event.key === 'Enter' && !event.shiftKey) {
			event.preventDefault();
			void send(input);
		}
	}

	async function copyMessage(id: string, content: string) {
		try {
			await navigator.clipboard.writeText(content);
			setCopiedMessage(id);
			window.setTimeout(() => setCopiedMessage((current) => current === id ? null : current), 1500);
		} catch {
			setError('无法访问剪贴板，请手动选择并复制回复。');
		}
	}

	function openRowOnKeyboard(event: KeyboardEvent<HTMLDivElement>, id: string) {
		if (event.target !== event.currentTarget) return;
		if (event.key === 'Enter' || event.key === ' ') {
			event.preventDefault();
			selectConversation(id);
		}
	}

	return (
		<div className="agent-workspace" data-testid="agent-workspace" data-agent-theme={workspace.theme}>
			{mobileOpen && <button className="agent-workspace__overlay" type="button" aria-label="关闭对话列表" onClick={() => setMobileOpen(false)} />}
			<aside className={`agent-workspace__sidebar${sidebarCollapsed ? ' is-collapsed' : ''}${mobileOpen ? ' is-mobile-open' : ''}`} aria-label="Agent 对话侧栏">
				<div className="agent-workspace__side-header">
					{!sidebarCollapsed && <span className="agent-workspace__brand"><Bot size={18} aria-hidden="true" /> WU YU · AGENT</span>}
					<button className="agent-workspace__icon-button agent-workspace__collapse" type="button" aria-label={sidebarCollapsed ? '展开侧栏' : '折叠侧栏'} title={sidebarCollapsed ? '展开侧栏' : '折叠侧栏'} onClick={() => setWorkspace((current) => ({ ...current, collapsed: !current.collapsed }))}>
						{sidebarCollapsed ? <PanelLeftOpen size={18} aria-hidden="true" /> : <PanelLeftClose size={18} aria-hidden="true" />}
					</button>
				</div>

				<div className="agent-workspace__agent-picker">
					{!sidebarCollapsed && <span className="agent-workspace__section-label">选择助手</span>}
					<button className="agent-workspace__agent-trigger" type="button" aria-label={`切换助手，当前为 ${agent.name}`} aria-expanded={agentMenuOpen} onClick={() => { setAgentMenuOpen((open) => !open); setSettingsOpen(false); }}>
						<span className="agent-workspace__agent-mark">{agent.mark}</span>
						{!sidebarCollapsed && <><span className="agent-workspace__agent-copy"><strong>{agent.name}</strong><small>{agent.hint}</small></span><ChevronDown size={15} aria-hidden="true" /></>}
						{sidebarCollapsed && <span className="agent-workspace__collapsed-chevron" aria-hidden="true">›</span>}
					</button>
					{agentMenuOpen && <div className="agent-workspace__agent-menu" role="menu" aria-label="选择助手">
						{(Object.keys(agents) as WorkspaceAgentId[]).map((id) => <button key={id} className="agent-workspace__menu-option" type="button" role="menuitemradio" aria-checked={workspace.activeAgent === id} onClick={() => switchAgent(id)}><span className="agent-workspace__agent-mark">{agents[id].mark}</span><span><strong>{agents[id].name}</strong><small>{agents[id].hint}</small></span>{workspace.activeAgent === id && <Check size={15} aria-hidden="true" />}</button>)}
					</div>}
				</div>

				<div className="agent-workspace__conversation-heading">
					{!sidebarCollapsed && <span>对话</span>}
					<button className="agent-workspace__icon-button" type="button" aria-label="新建对话" title="新建对话" onClick={newConversation}><Plus size={18} aria-hidden="true" />{!sidebarCollapsed && <span className="agent-workspace__tooltip">新建对话</span>}</button>
				</div>
				<div className="agent-workspace__chat-list" aria-label="历史对话">
					{chats.map((chat) => <div key={chat.id} className={`agent-workspace__chat-row${chat.id === currentChat?.id ? ' is-active' : ''}`} role="group" tabIndex={0} aria-label={`打开对话 ${chat.title}`} onClick={() => selectConversation(chat.id)} onKeyDown={(event) => openRowOnKeyboard(event, chat.id)}>
						<button className="agent-workspace__chat-open" type="button" aria-label={`打开对话 ${chat.title}`} onClick={() => selectConversation(chat.id)}><MessageSquare size={16} aria-hidden="true" /><span className="agent-workspace__chat-initial" aria-hidden="true">{Array.from(chat.title)[0] || '聊'}</span><span className="agent-workspace__chat-title">{chat.title}</span></button>
						<div className="agent-workspace__chat-actions">
							<button className="agent-workspace__row-action" type="button" aria-label={`重命名对话 ${chat.title}`} title="重命名" onClick={(event) => renameConversation(event, chat)}>✎</button>
							<button className="agent-workspace__row-action" type="button" aria-label={`删除对话 ${chat.title}`} title="删除" onClick={(event) => removeConversation(event, chat.id)}><X size={15} aria-hidden="true" /></button>
						</div>
					</div>)}
				</div>
				<div className="agent-workspace__side-footer">{!sidebarCollapsed && <span>个人网站 · Agent 工作台</span>}<span className="agent-workspace__avatar">WU</span></div>
			</aside>

			<div className="agent-workspace__main" role="region" aria-label="工作区">
				<header className="agent-workspace__topbar">
					<button className="agent-workspace__icon-button agent-workspace__mobile-menu" type="button" aria-label="打开对话列表" aria-expanded={mobileOpen} onClick={() => setMobileOpen(true)}><Menu size={18} aria-hidden="true" /></button>
					<div className="agent-workspace__top-title"><span className="agent-workspace__agent-mark">{agent.mark}</span><div><strong>{agent.name}</strong><small>{agent.hint}</small></div></div>
					<div className="agent-workspace__settings-wrap">
						<button className="agent-workspace__icon-button" type="button" aria-label="打开设置" aria-expanded={settingsOpen} onClick={() => { setSettingsOpen((open) => !open); setAgentMenuOpen(false); }}><Settings2 size={18} aria-hidden="true" /></button>
						{settingsOpen && <div className="agent-workspace__settings-menu" role="menu" aria-label="设置"><strong>设置</strong><span>外观主题</span>{themeOptions.map(({ id, label, Icon }) => <button key={id} type="button" role="menuitemradio" aria-checked={workspace.theme === id} onClick={() => setWorkspace((current) => ({ ...current, theme: id }))}><Icon size={15} aria-hidden="true" /><span>{label}</span>{workspace.theme === id && <Check size={14} aria-hidden="true" />}</button>)}</div>}
					</div>
				</header>

				<section className="agent-workspace__chat-area" aria-label={`${agent.name} 对话`}>
					{currentChat?.messages.length ? <div className="agent-workspace__messages">
						{currentChat.messages.map((message, index) => {
							const messageId = `${currentChat.id}-${index}`;
							if (message.role === 'user') return <article key={messageId} className="agent-workspace__message is-user"><p>{message.content}</p></article>;
							return <article key={messageId} className="agent-workspace__message is-assistant"><span className="agent-workspace__message-avatar">{agent.mark}</span><div className="agent-workspace__message-content"><p className="agent-workspace__message-text">{message.content}</p><div className="agent-workspace__message-actions" role="group" aria-label="回复操作"><button type="button" aria-label={copiedMessage === messageId ? '已复制回复' : '复制回复'} title={copiedMessage === messageId ? '已复制' : '复制'} onClick={() => void copyMessage(messageId, message.content)}><Copy size={15} aria-hidden="true" /><span>{copiedMessage === messageId ? '已复制' : '复制'}</span></button><button type="button" aria-label={citationsOpen[messageId] ? '隐藏参考来源' : '显示参考来源'} title="引用" aria-expanded={Boolean(citationsOpen[messageId])} onClick={() => setCitationsOpen((current) => ({ ...current, [messageId]: !current[messageId] }))}><Quote size={15} aria-hidden="true" /><span>引用</span></button><time dateTime={new Date(currentChat.updatedAt).toISOString()} title={new Date(currentChat.updatedAt).toLocaleString('zh-CN')}>{responseTime(currentChat.updatedAt)}</time></div>{citationsOpen[messageId] && <div className="agent-workspace__citations" role="region" aria-label="参考来源"><strong>参考来源</strong>{message.sources?.length ? <ul>{message.sources.map((source, sourceIndex) => <li key={`${source}-${sourceIndex}`}>{source}</li>)}</ul> : <p>未提供参考来源</p>}</div>}</div></article>;
						})}
						{loading && <article className="agent-workspace__message is-assistant is-loading"><span className="agent-workspace__message-avatar">{agent.mark}</span><div className="agent-workspace__message-content"><p>正在整理回答<span className="agent-workspace__dots" aria-hidden="true">...</span></p></div></article>}
					</div> : <div className="agent-workspace__welcome"><span className="agent-workspace__welcome-mark">{agent.mark}</span><p className="agent-workspace__eyebrow">{workspace.activeAgent === 'book' ? 'AGENT BOOK / RAG' : 'PERSONAL AGENT'}</p><h1>{agent.welcome}</h1><p className="agent-workspace__welcome-copy">{agent.description}</p><div className="agent-workspace__prompts">{agent.prompts.map((prompt) => <button key={prompt} type="button" disabled={loading} onClick={() => void send(prompt)}>{prompt}<span aria-hidden="true">↗</span></button>)}</div></div>}
					{error && <div className="agent-workspace__error" role="alert"><span>{error}</span>{failedQuestion && <button type="button" onClick={() => void send(failedQuestion, true)}>重试</button>}</div>}
				</section>

				<form className="agent-workspace__composer-zone" onSubmit={(event) => { event.preventDefault(); void send(input); }}>
					{currentChat?.messages.length > 0 && <button className="agent-workspace__clear" type="button" aria-label="清空当前对话" title="清空当前对话" onClick={clearCurrentConversation}><Trash2 size={15} aria-hidden="true" /><span>清空</span></button>}
					<div className="agent-workspace__composer"><label className="sr-only" htmlFor="agent-workspace-input">向 {agent.name} 提问</label><textarea id="agent-workspace-input" value={input} onChange={(event) => setInput(event.target.value)} onKeyDown={handleComposerKeyDown} placeholder="向 Agent 发送消息" rows={1} disabled={loading} /><button type="submit" aria-label="发送" title="发送" disabled={!input.trim() || loading}><Send size={17} aria-hidden="true" /></button></div>
					<p>Enter 发送 · Shift + Enter 换行</p>
				</form>
			</div>
		</div>
	);
}
