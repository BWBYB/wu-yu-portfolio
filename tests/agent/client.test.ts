import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { askKnowledgeBase } from '@/lib/agent/client';

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

	it('rejects malformed response payloads', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '缺少 mode', sources: [] }), { status: 200 }));

		await expect(askKnowledgeBase('问题', [])).rejects.toThrow(/Invalid agent response/);
	});

	it('rejects a remote response without a non-empty answer and source list', async () => {
		vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({ answer: '   ', mode: 'remote' }), { status: 200 }));

		await expect(askKnowledgeBase('问题', [])).rejects.toThrow(/Invalid agent response/);
	});

	it('aborts a request after the bounded timeout', async () => {
		vi.useFakeTimers();
		vi.mocked(fetch).mockImplementation((_input, init) => new Promise((_resolve, reject) => {
			init?.signal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
		}));

		const request = askKnowledgeBase('问题', []);
		const rejection = expect(request).rejects.toThrow(/timed out|aborted/i);
		await vi.advanceTimersByTimeAsync(10_001);

		await rejection;
	});
});
