export type AgentMessage = {
	role: 'user' | 'assistant';
	content: string;
	sources?: string[];
	mode?: 'demo' | 'remote' | 'dify';
};

export type AgentResponse = {
	answer: string;
	sources?: string[];
	mode: 'demo' | 'remote';
};

export type AgentBookResponse = {
	answer: string;
	conversation_id: string;
	sources: string[];
	mode: 'dify';
};
