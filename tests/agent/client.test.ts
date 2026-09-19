import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AgentRequestError, askKnowledgeBase } from '@/lib/agent/client';

describe('remote knowledge-base adapter', () => {
	const history = [
		{ role: 'user' as const, content: '你是谁？' },
		{ role: 'assistant' as const, content: '我是吴禹。', mode: 'demo' as const, sources: ['个人资料'] },
	];

	beforeEach(() => {
		vi.stubEnv('PUBLIC_AGENT_API_URL', 'http://localhost:8000/');
		vi.stubGlobal('fetch', vi.fn());
	});

	afterEach(() => {
		vi.unstubAllEnvs();
		vi.unstubAllGlobals();
		vi.useRealTimers();
	});

	it('posts the exact role/content-only request body and preserves remote metadata', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '远程回答', sources: ['个人资料'], mode: 'remote' }), { status: 200 }));

		await expect(askKnowledgeBase('  你是谁？  ', history)).resolves.toEqual({ answer: '远程回答', sources: ['个人资料'], mode: 'remote' });
		expect(fetch).toHaveBeenCalledWith('http://localhost:8000/api/chat', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ message: '  你是谁？  ', history: [{ role: 'user', content: '你是谁？' }, { role: 'assistant', content: '我是吴禹。' }] }),
			signal: expect.any(AbortSignal),
		});
	});

	it('uses the same-origin chat route for the Preview root URL', async () => {
		vi.stubEnv('PUBLIC_AGENT_API_URL', '/');
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '同域回答', sources: ['个人资料'], mode: 'remote' }), { status: 200 }));

		await expect(askKnowledgeBase('问题', [])).resolves.toEqual({ answer: '同域回答', sources: ['个人资料'], mode: 'remote' });
		expect(fetch).toHaveBeenCalledWith('/api/chat', expect.objectContaining({ method: 'POST' }));
	});

	it('limits remote request history to the backend limit', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '远程回答', sources: ['个人资料'], mode: 'remote' }), { status: 200 }));
		const longHistory = Array.from({ length: 10 }, (_, index) => ({
			role: index % 2 === 0 ? 'user' as const : 'assistant' as const,
			content: `消息 ${index + 1}`,
		}));

		await askKnowledgeBase('新问题', longHistory);

		const request = JSON.parse(String(vi.mocked(fetch).mock.calls[0][1]?.body));
		expect(request.history).toEqual(longHistory.slice(-8));
	});

	it('rejects non-2xx responses', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response('service unavailable', { status: 503 }));

		await expect(askKnowledgeBase('问题', [])).rejects.toThrow(/503/);
	});

	it('preserves the status of a rate-limited response', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response('rate limited', { status: 429 }));

		try {
			await askKnowledgeBase('问题', []);
			expect.fail('expected the request to reject');
		} catch (error) {
			expect(error).toBeInstanceOf(AgentRequestError);
			expect(error).toMatchObject({ status: 429 });
		}
	});

	it('rejects malformed response payloads', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '缺少 mode', sources: [] }), { status: 200 }));

		await expect(askKnowledgeBase('问题', [])).rejects.toThrow(/Invalid agent response/);
	});

	it('rejects a remote response with a blank answer', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '   ', sources: ['个人资料'], mode: 'remote' }), { status: 200 }));

		await expect(askKnowledgeBase('问题', [])).rejects.toThrow(/Invalid agent response/);
	});

	it('rejects a remote response without a source list', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '有效回答', mode: 'remote' }), { status: 200 }));

		await expect(askKnowledgeBase('问题', [])).rejects.toThrow(/Invalid agent response/);
	});

	it('keeps a slow request alive until the 75 second timeout', async () => {
		vi.useFakeTimers();
		let aborted = false;
		vi.mocked(fetch).mockImplementation((_input, init) => new Promise((_resolve, reject) => {
			init?.signal?.addEventListener('abort', () => {
				aborted = true;
				reject(new DOMException('Aborted', 'AbortError'));
			});
		}));

		const request = askKnowledgeBase('问题', []);
		const rejection = expect(request).rejects.toThrow(/timed out|aborted/i);
		await vi.advanceTimersByTimeAsync(74_999);
		expect(aborted).toBe(false);
		await vi.advanceTimersByTimeAsync(1);

		await rejection;
		expect(aborted).toBe(true);
	});
});
