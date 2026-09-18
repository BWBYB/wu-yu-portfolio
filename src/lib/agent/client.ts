import { getDemoResponse } from './demo';
import type { AgentMessage, AgentResponse } from './types';

const REQUEST_TIMEOUT_MS = 10_000;
const MAX_HISTORY_MESSAGES = 8;

function isValidRemoteResponse(value: unknown): value is AgentResponse {
	if (!value || typeof value !== 'object') return false;
	const response = value as Record<string, unknown>;
	return (
		typeof response.answer === 'string' &&
		response.answer.trim().length > 0 &&
		response.mode === 'remote' &&
		Array.isArray(response.sources) &&
		response.sources.every((source) => typeof source === 'string')
	);
}

async function askRemote(question: string, history: AgentMessage[], baseUrl: string): Promise<AgentResponse> {
	const controller = new AbortController();
	let timedOut = false;
	const timeout = setTimeout(() => {
		timedOut = true;
		controller.abort();
	}, REQUEST_TIMEOUT_MS);

	try {
		const response = await fetch(`${baseUrl.replace(/\/$/, '')}/api/chat`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				message: question,
				history: history.slice(-MAX_HISTORY_MESSAGES).map(({ role, content }) => ({ role, content })),
			}),
			signal: controller.signal,
		});

		if (!response.ok) {
			throw new Error(`Remote agent request failed with status ${response.status}`);
		}

		let payload: unknown;
		try {
			payload = await response.json();
		} catch {
			throw new Error('Invalid agent response: expected JSON');
		}
		if (!isValidRemoteResponse(payload)) {
			throw new Error('Invalid agent response');
		}
		return payload;
	} catch (error) {
		if (timedOut) throw new Error('Remote agent request timed out');
		throw error;
	} finally {
		clearTimeout(timeout);
	}
}

export async function askKnowledgeBase(question: string, history: AgentMessage[]): Promise<AgentResponse> {
	const baseUrl = import.meta.env.PUBLIC_AGENT_API_URL?.trim();
	if (!baseUrl) return getDemoResponse(question, history);
	return askRemote(question, history, baseUrl);
}
