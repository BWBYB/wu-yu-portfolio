import { describe, expect, it } from 'vitest';
import { askKnowledgeBase } from '@/lib/agent/client';

describe('local knowledge-base adapter', () => {
	it('answers the SPMTrack responsibility prompt with demo mode and a source label', async () => {
		const response = await askKnowledgeBase('你在 SPMTrack 里负责什么？', []);

		expect(response.mode).toBe('demo');
		expect(response.answer).toContain('React');
		expect(response.sources).toContain('SPMTrack 项目资料');
	});

	it('returns a bounded fallback instead of inventing unknown facts', async () => {
		const response = await askKnowledgeBase('你最喜欢的电影是什么？', []);

		expect(response.mode).toBe('demo');
		expect(response.answer).toContain('资料中没有');
	});

	it('does not mutate conversation history', async () => {
		const history = [{ role: 'user', content: '你是谁？' }] as const;

		await askKnowledgeBase('你在学习什么？', [...history]);

		expect(history).toHaveLength(1);
	});

	it('preserves demo provenance metadata on every answer', async () => {
		const response = await askKnowledgeBase('你是谁？', []);

		expect(response).toMatchObject({ mode: 'demo', sources: ['个人资料'] });
	});
});
