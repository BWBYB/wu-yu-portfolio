import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AgentWorkspace from '@/components/AgentWorkspace';
import { askAgentBook, askKnowledgeBase } from '@/lib/agent/client';

vi.mock('@/lib/agent/client', () => ({
	askAgentBook: vi.fn(),
	askKnowledgeBase: vi.fn(),
}));

const mockedBook = vi.mocked(askAgentBook);
const mockedPersonal = vi.mocked(askKnowledgeBase);

describe('AgentWorkspace', () => {
	beforeEach(() => {
		window.localStorage.clear();
		vi.resetAllMocks();
		mockedPersonal.mockResolvedValue({ answer: '我是吴禹。', mode: 'demo', sources: ['个人资料'] });
		mockedBook.mockResolvedValue({ answer: 'Agent 是可循环调用工具的系统。', conversation_id: 'book-1', sources: ['第一章'], mode: 'local-rag' });
	});

	afterEach(() => {
		vi.restoreAllMocks();
	});

	it('starts with the personal assistant and can switch to Agent Book', async () => {
		const user = userEvent.setup();
		render(<AgentWorkspace />);

		expect(screen.getByRole('button', { name: /切换助手，当前为 了解 WU YU/ })).toBeVisible();
		await user.click(screen.getByRole('button', { name: /切换助手/ }));
		await user.click(screen.getByRole('menuitemradio', { name: /AI-Agent-Book/ }));

		expect(screen.getByRole('button', { name: /切换助手，当前为 AI-Agent-Book/ })).toBeVisible();
	});

	it('sends through the selected adapter and renders citation sources', async () => {
		const user = userEvent.setup();
		render(<AgentWorkspace />);

		await user.click(screen.getByRole('button', { name: /切换助手/ }));
		await user.click(screen.getByRole('menuitemradio', { name: /AI-Agent-Book/ }));
		await user.click(screen.getByRole('button', { name: /什么是 Agent/ }));

		expect(await screen.findByText('Agent 是可循环调用工具的系统。')).toBeVisible();
		expect(mockedBook).toHaveBeenCalledWith('什么是 Agent？', null);
		await user.click(screen.getByRole('button', { name: /显示参考来源/ }));
		expect(screen.getByRole('region', { name: /参考来源/ })).toHaveTextContent('第一章');
	});

	it('opens a conversation from its row and preserves retry state', async () => {
		const user = userEvent.setup();
		mockedPersonal.mockRejectedValueOnce(new Error('network unavailable'));
		render(<AgentWorkspace />);

		await user.click(screen.getByRole('button', { name: '新建对话' }));
		const sameTitleRows = screen.getAllByRole('group', { name: '打开对话 开始对话' });
		await user.click(sameTitleRows[1]!);
		await user.click(screen.getByRole('button', { name: /你是谁/ }));

		expect(await screen.findByRole('button', { name: /重试/ })).toBeVisible();
		expect(screen.getByRole('article')).toHaveTextContent('你是谁？');
	});

	it('keeps the mobile conversation drawer expanded when the desktop rail is collapsed', async () => {
		const user = userEvent.setup();
		render(<AgentWorkspace />);

		await user.click(screen.getByRole('button', { name: '折叠侧栏' }));
		expect(screen.queryByText('选择助手')).not.toBeInTheDocument();

		await user.click(screen.getByRole('button', { name: '打开对话列表' }));
		expect(screen.getByText('选择助手')).toBeVisible();
		expect(screen.getByText('对话')).toBeVisible();

		await user.click(screen.getByRole('button', { name: '关闭对话列表' }));
		expect(screen.queryByText('选择助手')).not.toBeInTheDocument();
	});

	it('persists the selected theme and assistant across a remount', async () => {
		const user = userEvent.setup();
		const view = render(<AgentWorkspace />);

		await user.click(screen.getByRole('button', { name: /切换助手/ }));
		await user.click(screen.getByRole('menuitemradio', { name: /AI-Agent-Book/ }));
		await user.click(screen.getByRole('button', { name: /打开设置/ }));
		await user.click(screen.getByRole('menuitemradio', { name: /深色/ }));

		expect(screen.getByTestId('agent-workspace')).toHaveAttribute('data-agent-theme', 'dark');
		view.unmount();
		render(<AgentWorkspace />);
		expect(screen.getByRole('button', { name: /切换助手，当前为 AI-Agent-Book/ })).toBeVisible();
		expect(screen.getByTestId('agent-workspace')).toHaveAttribute('data-agent-theme', 'dark');
	});

	it('supports Enter to send while Shift+Enter keeps the text in the composer', async () => {
		const user = userEvent.setup();
		render(<AgentWorkspace />);
		const input = screen.getByRole('textbox', { name: /向 了解 WU YU 提问/ });

		await user.type(input, '你是谁？');
		fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
		expect(input).toHaveValue('你是谁？');
		fireEvent.keyDown(input, { key: 'Enter' });
		await waitFor(() => expect(screen.getByText('我是吴禹。')).toBeVisible());
	});
});
