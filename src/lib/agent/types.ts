export type AgentMessage = {
	role: 'user' | 'assistant';
	content: string;
	sources?: string[];
	mode?: 'demo' | 'remote';
};

export type AgentResponse = {
	answer: string;
	sources?: string[];
	mode: 'demo' | 'remote';
};
