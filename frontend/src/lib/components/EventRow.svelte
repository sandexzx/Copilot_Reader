<script lang="ts">
	import type { Event } from '$lib/types';
	import { formatTimestamp, formatEventDescription, getEventColor, getEventBgColor, getEventCategory, colorizeJson } from '$lib/utils/events';

	let { event }: { event: Event } = $props();

	let expanded = $state(false);

	let timestamp = $derived(formatTimestamp(event.timestamp));
	let description = $derived(formatEventDescription(event));
	let color = $derived(getEventColor(event.type));
	let bgColor = $derived(getEventBgColor(event.type));
	let category = $derived(getEventCategory(event.type));
	let detailHtml = $derived(colorizeJson(event.data));
	let model = $derived((event.data?.model ?? event.data?.currentModel ?? '') as string);

	let fileChip = $derived.by(() => {
		const d = event.data;
		const toolName = (d?.toolName ?? d?.tool_name ?? event.tool_name ?? '') as string;
		if (['edit', 'view', 'create', 'grep', 'glob'].includes(toolName)) {
			const args = d?.arguments as Record<string, unknown> | undefined;
			const path = (args?.path ?? d?.path ?? '') as string;
			if (path) {
				const parts = path.split('/');
				return parts[parts.length - 1];
			}
		}
		return '';
	});

	let commandChip = $derived.by(() => {
		const d = event.data;
		const toolName = (d?.toolName ?? d?.tool_name ?? event.tool_name ?? '') as string;
		if (toolName === 'bash' && event.type === 'tool.execution_start') {
			const args = d?.arguments as Record<string, unknown> | undefined;
			const cmd = (args?.command ?? '') as string;
			if (cmd) {
				return cmd.length > 50 ? cmd.slice(0, 50) + '…' : cmd;
			}
		}
		return '';
	});

	let patternChip = $derived.by(() => {
		const d = event.data;
		const toolName = (d?.toolName ?? d?.tool_name ?? event.tool_name ?? '') as string;
		if (toolName === 'grep' && event.type === 'tool.execution_start') {
			const args = d?.arguments as Record<string, unknown> | undefined;
			const pattern = (args?.pattern ?? '') as string;
			if (pattern) {
				return pattern.length > 40 ? pattern.slice(0, 40) + '…' : pattern;
			}
		}
		return '';
	});

	let sqlChip = $derived.by(() => {
		const d = event.data;
		const toolName = (d?.toolName ?? d?.tool_name ?? event.tool_name ?? '') as string;
		if (toolName === 'sql' && event.type === 'tool.execution_start') {
			const args = d?.arguments as Record<string, unknown> | undefined;
			const query = (args?.query ?? '') as string;
			if (query) {
				return query.length > 60 ? query.slice(0, 60) + '…' : query;
			}
		}
		return '';
	});

	let taskChip = $derived.by(() => {
		const d = event.data;
		const toolName = (d?.toolName ?? d?.tool_name ?? event.tool_name ?? '') as string;
		if (toolName === 'task' && event.type === 'tool.execution_start') {
			const args = d?.arguments as Record<string, unknown> | undefined;
			const agentType = (args?.agent_type ?? '') as string;
			const mode = (args?.mode ?? '') as string;
			if (agentType) {
				return mode ? `${agentType} (${mode})` : agentType;
			}
		}
		return '';
	});

	let resultChip = $derived.by(() => {
		if (event.type !== 'tool.execution_complete') return '';
		const d = event.data;
		const result = d?.result as Record<string, unknown> | undefined;
		const content = (result?.content ?? '') as string;
		if (content) {
			const clean = content.replace(/\n/g, ' ').trim();
			return clean.length > 80 ? clean.slice(0, 80) + '…' : clean;
		}
		return '';
	});

	let successIndicator = $derived.by(() => {
		if (event.type !== 'tool.execution_complete') return '';
		const d = event.data;
		const success = d?.success;
		if (success === true) return '✅';
		if (success === false) return '❌';
		return '';
	});

	function toggle() {
		expanded = !expanded;
	}
</script>

<div class="event-row-wrapper">
	<div
		class="event-row"
		class:expanded
		onclick={toggle}
		role="button"
		tabindex="0"
		onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } }}
	>
		<span class="event-time">{timestamp}</span>
		<span class="event-badge" style="color: {color}; background: {bgColor};">
			{event.type}
		</span>
		{#if model}
			<span class="model-chip">{model}</span>
		{/if}
		{#if fileChip}
			<span class="file-chip">📄 {fileChip}</span>
		{/if}
		{#if commandChip}
			<span class="command-chip">$ {commandChip}</span>
		{/if}
		{#if patternChip}
			<span class="pattern-chip">/{patternChip}/</span>
		{/if}
		{#if sqlChip}
			<span class="sql-chip" title={sqlChip}>🗃 {sqlChip}</span>
		{/if}
		{#if taskChip}
			<span class="task-chip">🤖 {taskChip}</span>
		{/if}
		{#if resultChip}
			<span class="result-chip" title={resultChip}>{successIndicator} {resultChip}</span>
		{/if}
		<span class="event-desc">{description}</span>
		<span class="event-expand">{expanded ? '▾' : '▸'}</span>
	</div>
	{#if expanded}
		<div class="event-detail">
			<pre>{@html detailHtml}</pre>
		</div>
	{/if}
</div>

<style>
	.event-row-wrapper {
		animation: fadeSlideIn 0.3s forwards;
		opacity: 0;
		transform: translateY(6px);
	}

	@keyframes fadeSlideIn {
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.event-row {
		display: flex;
		align-items: flex-start;
		padding: 3px 12px;
		border-bottom: 1px solid rgba(60, 60, 60, 0.3);
		cursor: pointer;
		transition: background 0.1s;
		gap: 8px;
		line-height: 1.5;
	}

	.event-row:hover {
		background: var(--bg-hover);
	}

	.event-row.expanded {
		background: rgba(9, 71, 113, 0.15);
	}

	.event-time {
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		flex-shrink: 0;
		min-width: 85px;
		user-select: text;
	}

	.event-badge {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 10px;
		font-weight: 600;
		min-width: 130px;
		max-width: 160px;
		text-align: center;
		flex-shrink: 0;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.model-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: var(--cyan);
		background: rgba(156, 220, 254, 0.12);
		flex-shrink: 0;
		white-space: nowrap;
		font-family: var(--font-mono);
	}

	.file-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: var(--orange);
		background: rgba(206, 145, 120, 0.12);
		flex-shrink: 0;
		white-space: nowrap;
		font-family: var(--font-mono);
		max-width: 180px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.command-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: var(--green, #4ec9b0);
		background: rgba(78, 201, 176, 0.12);
		flex-shrink: 0;
		white-space: nowrap;
		font-family: var(--font-mono);
		max-width: 260px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.pattern-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: var(--yellow, #dcdcaa);
		background: rgba(220, 220, 170, 0.12);
		flex-shrink: 0;
		white-space: nowrap;
		font-family: var(--font-mono);
		max-width: 200px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.sql-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: #e8c56d;
		background: rgba(232, 197, 109, 0.12);
		flex-shrink: 0;
		white-space: nowrap;
		font-family: var(--font-mono);
		max-width: 320px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.task-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: var(--cyan);
		background: rgba(156, 220, 254, 0.12);
		flex-shrink: 0;
		white-space: nowrap;
		font-family: var(--font-mono);
		max-width: 200px;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.result-chip {
		padding: 1px 6px;
		border-radius: 3px;
		font-size: 9px;
		font-weight: 500;
		color: var(--text-secondary);
		background: rgba(106, 106, 106, 0.12);
		flex-shrink: 1;
		white-space: nowrap;
		font-family: var(--font-mono);
		max-width: 400px;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.event-desc {
		flex: 1;
		color: var(--text-primary);
		font-size: 12px;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.event-expand {
		flex-shrink: 0;
		font-size: 10px;
		color: var(--text-secondary);
		width: 12px;
		text-align: center;
	}

	.event-detail {
		padding: 4px 12px 8px 112px;
		font-family: var(--font-mono);
		font-size: 11px;
		color: var(--text-secondary);
		white-space: pre;
		overflow-x: auto;
		background: rgba(0, 0, 0, 0.15);
		border-bottom: 1px solid rgba(60, 60, 60, 0.3);
	}

	.event-detail pre {
		margin: 0;
		font-family: inherit;
		font-size: inherit;
		color: inherit;
	}

	.event-detail :global(.json-key) {
		color: var(--cyan);
	}

	.event-detail :global(.json-str) {
		color: var(--orange);
	}

	.event-detail :global(.json-num) {
		color: var(--green);
	}

	.event-detail :global(.json-bool) {
		color: var(--blue);
	}
</style>
