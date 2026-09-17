export type AgentMessage = {
	role: 'user' | 'assistant';
	content: string;
};

export type AgentResponse = {
	answer: string;
	sources?: string[];
	mode: 'demo' | 'remote';
};
