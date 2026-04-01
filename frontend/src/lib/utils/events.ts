/** Event display utilities — description formatting and type-to-color mapping. */

import type { Event } from '$lib/types';

/** CSS color variable for each event type category. */
const TYPE_COLOR_MAP: Record<string, string> = {
	session: 'var(--color-session)',
	user: 'var(--color-user)',
	assistant: 'var(--color-assistant)',
	tool: 'var(--color-tool)',
	subagent: 'var(--color-subagent)',
	hook: 'var(--color-hook)',
	error: 'var(--color-error)',
	abort: 'var(--color-error)'
};

/** Background tint for badge by type category. */
const TYPE_BG_MAP: Record<string, string> = {
	session: 'rgba(86,156,214,.18)',
	user: 'rgba(78,201,176,.18)',
	assistant: 'rgba(197,134,192,.18)',
	tool: 'rgba(206,145,120,.18)',
	subagent: 'rgba(156,220,254,.18)',
	hook: 'rgba(106,106,106,.18)',
	error: 'rgba(244,71,71,.18)',
	abort: 'rgba(244,71,71,.18)'
};

export function getEventCategory(eventType: string): string {
	return eventType.split('.')[0];
}

export function getEventColor(eventType: string): string {
	const cat = getEventCategory(eventType);
	return TYPE_COLOR_MAP[cat] ?? 'var(--text-secondary)';
}

export function getEventBgColor(eventType: string): string {
	const cat = getEventCategory(eventType);
	return TYPE_BG_MAP[cat] ?? 'rgba(106,106,106,.18)';
}

function truncate(s: string, max: number): string {
	return s.length > max ? s.slice(0, max) + '…' : s;
}

function str(v: unknown): string {
	return typeof v === 'string' ? v : String(v ?? '');
}

/** Build a human-readable one-line description for an event. */
export function formatEventDescription(event: Event): string {
	const d = event.data;

	switch (event.type) {
		case 'session.start': {
			const version = str(d.version ?? d.copilotVersion ?? '');
			const cwd = str(d.cwd ?? d.workingDirectory ?? '');
			const parts: string[] = ['Session started'];
			if (version) parts[0] += ` (v${version})`;
			if (cwd) parts.push(`— ${cwd}`);
			return parts.join(' ');
		}
		case 'session.shutdown': {
			const dur = d.duration ?? d.duration_seconds ?? d.durationMs;
			const pr = d.premium_requests ?? d.premiumRequests ?? 0;
			const parts: string[] = ['Session ended'];
			if (dur != null) parts.push(`— ${dur}s`);
			if (pr) parts.push(`, ${pr} premium requests`);
			return parts.join('');
		}
		case 'session.compaction_complete': {
			const summary = str(d.summaryContent ?? '');
			const tokens = d.compactionTokensUsed ?? d.preCompactionTokens;
			const parts: string[] = ['Context compacted'];
			if (tokens != null) parts.push(`(${tokens} tokens)`);
			if (summary) parts.push(`— ${truncate(summary.replace(/\n/g, ' '), 80)}`);
			return parts.join(' ');
		}
		case 'user.message': {
			const content = str(d.content ?? d.message ?? d.text ?? '');
			return content ? truncate(content, 100) : 'User message';
		}
		case 'assistant.message': {
			const toolCalls = d.tool_calls ?? d.toolCalls ?? d.toolRequests;
			if (Array.isArray(toolCalls) && toolCalls.length > 0) {
				const names = toolCalls
					.map((t: Record<string, unknown>) => str(t.name ?? ''))
					.filter(Boolean);
				if (names.length > 0) {
					const unique = [...new Set(names)];
					return truncate(unique.join(', '), 100);
				}
				return `${toolCalls.length} tool call${toolCalls.length === 1 ? '' : 's'}`;
			}
			const content = str(d.content ?? d.message ?? d.text ?? '');
			if (content) return truncate(content, 100);
			const reasoning = str(d.reasoningText ?? '');
			if (reasoning) return truncate(reasoning, 100);
			return 'Assistant response';
		}
		case 'tool.execution_start': {
			const name = str(d.toolName ?? d.tool_name ?? d.name ?? '');
			const args = d.arguments as Record<string, unknown> | undefined;
			if (name === 'bash' && args) {
				const cmd = str(args.command ?? '');
				const argDesc = str(args.description ?? '');
				if (cmd) {
					const cmdPart = `$ ${truncate(cmd, 70)}`;
					return argDesc ? `bash → ${truncate(argDesc, 40)} | ${cmdPart}` : `bash → ${cmdPart}`;
				}
			}
			if (name === 'grep' && args) {
				const pattern = str(args.pattern ?? '');
				if (pattern) {
					let result = `grep → /${truncate(pattern, 50)}/`;
					const searchPath = str(args.path ?? '');
					if (searchPath) {
						const segments = searchPath.split('/');
						result += ` in ${segments[segments.length - 1]}`;
					}
					if (args.glob) result += ' (glob)';
					const mode = str(args.output_mode ?? '');
					if (mode && mode !== 'files_with_matches') result += ` [${mode}]`;
					return result;
				}
			}
			if (name === 'glob' && args) {
				const pattern = str(args.pattern ?? '');
				if (pattern) {
					let result = `glob → ${truncate(pattern, 60)}`;
					const searchPath = str(args.path ?? '');
					if (searchPath) {
						const segments = searchPath.split('/');
						result += ` in ${segments[segments.length - 1]}`;
					}
					return result;
				}
			}
			if (name === 'sql' && args) {
				const desc = str(args.description ?? '');
				const query = str(args.query ?? '');
				if (desc && query) {
					return `sql → ${truncate(desc, 40)} | ${truncate(query, 50)}`;
				}
				if (query) return `sql → ${truncate(query, 70)}`;
				return desc ? `sql → ${truncate(desc, 70)}` : 'sql';
			}
			if (name === 'task' && args) {
				const agentType = str(args.agent_type ?? '');
				const desc = str(args.description ?? '');
				const mode = str(args.mode ?? '');
				const parts: string[] = ['task'];
				if (agentType) parts.push(`→ ${agentType}`);
				if (desc) parts.push(`"${truncate(desc, 40)}"`);
				if (mode) parts.push(`[${mode}]`);
				return parts.join(' ');
			}
			if (name === 'report_intent' && args) {
				const intent = str(args.intent ?? '');
				if (intent) return `🎯 ${truncate(intent, 80)}`;
			}
			const desc = str(d.description ?? d.input ?? '');
			if (name && desc) return `${name} → ${truncate(desc, 80)}`;
			return name || 'Tool started';
		}
		case 'tool.execution_complete': {
			const name = str(d.toolName ?? d.tool_name ?? event.tool_name ?? d.name ?? '');
			const failed = d.error || d.failed || d.exitCode;
			if (name === 'bash') {
				if (failed) {
					const exitCode = d.exitCode;
					return typeof exitCode === 'number' ? `bash ✗ exit ${exitCode}` : 'bash ✗ failed';
				}
				return 'bash ✓';
			}
			if (name === 'grep' && !failed) {
				const result = d.result as Record<string, unknown> | undefined;
				const content = str(result?.content ?? '');
				if (content) {
					const lines = content.split('\n').filter((l) => l.trim() !== '');
					const count = lines.length;
					const noun = count === 1 ? 'match' : 'matches';
					return `grep ✓ — ${count} ${noun}`;
				}
				return 'grep ✓';
			}
			if (name === 'sql') {
				const telemetry = d.toolTelemetry as Record<string, unknown> | undefined;
				const props = telemetry?.properties as Record<string, unknown> | undefined;
				const metrics = telemetry?.metrics as Record<string, unknown> | undefined;
				const queryType = str(props?.queryType ?? '');
				const rowsReturned = metrics?.rowsReturned as number | undefined;
				const rowsAffected = metrics?.rowsAffected as number | undefined;

				let desc = `sql ${failed ? '✗' : '✓'}`;
				if (queryType) desc += ` ${queryType}`;
				if (rowsReturned != null && rowsReturned > 0) desc += ` — ${rowsReturned} row${rowsReturned === 1 ? '' : 's'}`;
				if (rowsAffected != null && rowsAffected > 0) desc += ` — ${rowsAffected} affected`;
				return desc;
			}
			if (name === 'task') {
				const telemetry = d.toolTelemetry as Record<string, unknown> | undefined;
				const props = telemetry?.properties as Record<string, unknown> | undefined;
				const agentType = str(props?.agent_type ?? '');
				const agentId = str(props?.agent_id ?? '');

				let desc = `task ${failed ? '✗' : '✓'}`;
				if (agentType) desc += ` ${agentType}`;
				if (agentId) desc += ` (${agentId})`;
				return desc;
			}
			return name ? `${name} ${failed ? '✗ failed' : '✓'}` : 'Tool completed';
		}
		case 'subagent.started': {
			const agent = str(d.agentName ?? d.agent_name ?? d.name ?? '');
			return agent ? `Started: ${agent}` : 'Subagent started';
		}
		case 'subagent.completed': {
			const agent = str(d.agentName ?? d.agent_name ?? d.name ?? '');
			return agent ? `${agent} ✓` : 'Subagent completed';
		}
		case 'abort':
			return 'User aborted';
		default:
			return event.type;
	}
}

/** Format a timestamp string to HH:MM:SS.mmm */
export function formatTimestamp(ts: string): string {
	try {
		const d = new Date(ts);
		const h = String(d.getHours()).padStart(2, '0');
		const m = String(d.getMinutes()).padStart(2, '0');
		const s = String(d.getSeconds()).padStart(2, '0');
		const ms = String(d.getMilliseconds()).padStart(3, '0');
		return `${h}:${m}:${s}.${ms}`;
	} catch {
		return ts;
	}
}

/** Render JSON with basic syntax coloring as HTML spans. */
export function colorizeJson(data: unknown): string {
	const raw = JSON.stringify(data, null, 2);
	if (!raw) return '';
	return raw.replace(
		/("(?:\\.|[^"\\])*")\s*:/g,
		'<span class="json-key">$1</span>:'
	).replace(
		/:\s*("(?:\\.|[^"\\])*")/g,
		(match, val) => match.replace(val, `<span class="json-str">${val}</span>`)
	).replace(
		/:\s*(\d+(?:\.\d+)?)/g,
		(match, val) => match.replace(val, `<span class="json-num">${val}</span>`)
	).replace(
		/:\s*(true|false|null)/g,
		(match, val) => match.replace(val, `<span class="json-bool">${val}</span>`)
	);
}
