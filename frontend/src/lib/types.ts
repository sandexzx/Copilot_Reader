/** TypeScript types matching backend Pydantic models. */

export interface Event {
	type: string;
	data: Record<string, unknown>;
	id: string;
	timestamp: string;
	parentId: string | null;
	tool_name?: string | null;
}

export interface SessionSummary {
	id: string;
	summary: string;
	cwd: string;
	created_at: string;
	updated_at: string;
	is_active: boolean;
	event_count: number;
}

export interface Session extends SessionSummary {
	git_root: string | null;
	branch: string | null;
	pid: number | null;
}

export interface SessionStats {
	total_events: number;
	duration_seconds: number;
	models_used: string[];
	input_tokens: number;
	output_tokens: number;
	cache_read_tokens: number;
	cache_write_tokens: number;
	tool_calls: number;
	user_messages: number;
	assistant_turns: number;
	files_modified: number;
	lines_added: number;
	lines_removed: number;
	premium_requests: number;
}

export interface TreeNode {
	event: Event;
	children: TreeNode[];
	semantic_kind: string;
	event_count: number;
	duration_ms: number | null;
	brief_description: string | null;
	status: string | null;
	agent_name: string | null;
}

export interface WebSocketMessage {
	type: string;
	data: Record<string, unknown>;
}

export interface ModelUsage {
	input_tokens: number;
	output_tokens: number;
	cache_read_tokens: number;
	cache_write_tokens: number;
	premium_requests: number;
	requests_count: number;
}

export interface DailyUsageTotals {
	input_tokens: number;
	output_tokens: number;
	cache_read_tokens: number;
	cache_write_tokens: number;
	premium_requests: number;
}

export interface DailyUsageResponse {
	date: string;
	sessions_count: number;
	models: Record<string, ModelUsage>;
	totals: DailyUsageTotals;
}
