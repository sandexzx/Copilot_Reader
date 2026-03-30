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
