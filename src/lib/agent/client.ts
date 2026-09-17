import { getDemoResponse } from './demo';
import type { AgentMessage, AgentResponse } from './types';

// This single boundary can later switch from local answers to a remote /api/chat request.
export async function askKnowledgeBase(question: string, history: AgentMessage[]): Promise<AgentResponse> {
	return getDemoResponse(question, history);
}
