import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ChatPanel from '@/components/ChatPanel';
import { askKnowledgeBase } from '@/lib/agent/client';

vi.mock('@/lib/agent/client', () => ({
	askKnowledgeBase: vi.fn(),
}));

const mockedAsk = vi.mocked(askKnowledgeBase);

describe('ChatPanel', () => {
	beforeEach(() => {
		vi.resetAllMocks();
		mockedAsk.mockResolvedValue({
			answer: '我主要使用 React 完成任务工作台。',
			sources: ['SPMTrack 项目资料'],
			mode: 'demo',
		});
	});

	it('appends a recommended question and demo answer', async () => {
		const user = userEvent.setup();
		render(<ChatPanel recommendedPrompts={['你在 SPMTrack 里负责什么？']} />);

		await user.click(screen.getByRole('button', { name: /你在 SPMTrack 里负责什么/ }));

		expect(await screen.findByText(/React/)).toBeVisible();
		expect(screen.getByText(/演示模式/)).toBeVisible();
		expect(screen.getByText(/SPMTrack 项目资料/)).toBeVisible();
	});

	it('does not submit empty input and can clear the conversation', async () => {
		const user = userEvent.setup();
		render(<ChatPanel />);

		expect(screen.getByRole('button', { name: /发送/ })).toBeDisabled();
		await user.click(screen.getByRole('button', { name: /清空对话/ }));
		expect(screen.getByText(/还没有问题/)).toBeVisible();
	});

	it('shows a recoverable failure state', async () => {
		const user = userEvent.setup();
		mockedAsk.mockRejectedValueOnce(new Error('network unavailable'));
		render(<ChatPanel recommendedPrompts={['你是谁？']} />);

		await user.click(screen.getByRole('button', { name: /你是谁/ }));
		expect(await screen.findByRole('button', { name: /重试/ })).toBeVisible();

		mockedAsk.mockResolvedValueOnce({ answer: '我是吴禹。', mode: 'demo', sources: ['个人资料'] });
		await user.click(screen.getByRole('button', { name: /重试/ }));
		await waitFor(() => expect(screen.getByText('我是吴禹。')).toBeVisible());
		expect(mockedAsk).toHaveBeenNthCalledWith(2, '你是谁？', []);
	});

	it('submits typed questions with Enter and allows Shift+Enter for a newline', async () => {
		const user = userEvent.setup();
		render(<ChatPanel />);
		const input = screen.getByRole('textbox', { name: /向我的知识库提问/ });

		await user.type(input, '你在学习什么？');
		fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });
		expect(input).toHaveValue('你在学习什么？');
		fireEvent.keyDown(input, { key: 'Enter' });
		expect(await screen.findByText('你在学习什么？')).toBeVisible();
	});
});
