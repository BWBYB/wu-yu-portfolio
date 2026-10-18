export type AgentMessage = {
	role: 'user' | 'assistant';
	content: string;
	sources?: string[];
	mode?: 'demo' | 'remote' | 'local-rag';
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
	mode: 'local-rag';
};
