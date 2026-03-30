<script lang="ts">
	import type { SessionSummary } from '$lib/types';
	import { relativeTime, shortenPath } from '$lib/utils/time';

	let { session, selected = false, onselect }: {
		session: SessionSummary;
		selected?: boolean;
		onselect: (id: string) => void;
	} = $props();

	let timeText = $derived(relativeTime(session.updated_at));
	let pathText = $derived(shortenPath(session.cwd));
</script>

<button
	class="session-card"
	class:selected
	class:is-active={session.is_active}
	onclick={() => onselect(session.id)}
	type="button"
>
	<div class="card-accent" class:accent-live={session.is_active}></div>
	<div class="card-body">
		<div class="card-top">
			<span class="status-dot" class:dot-live={session.is_active} class:dot-ended={!session.is_active}></span>
			<span class="card-summary">{session.summary || 'Untitled session'}</span>
		</div>
		<div class="card-meta">
			<span class="card-path">{pathText}</span>
			<span class="card-time">{timeText}</span>
		</div>
	</div>
</button>

<style>
	.session-card {
		position: relative;
		display: flex;
		width: 100%;
		padding: 0;
		margin: 0 0 2px;
		cursor: pointer;
		background: transparent;
		border: none;
		border-radius: 0;
		color: inherit;
		font-family: inherit;
		text-align: left;
		transition: background 0.15s ease, box-shadow 0.15s ease;
		outline: none;
	}

	.session-card:hover {
		background: var(--bg-hover);
		box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.03);
	}

	.session-card:focus-visible {
		box-shadow: inset 0 0 0 1px var(--border-active);
	}

	.session-card.selected {
		background: rgba(9, 71, 113, 0.45);
	}

	.session-card.selected:hover {
		background: rgba(9, 71, 113, 0.55);
	}

	.card-accent {
		width: 3px;
		min-width: 3px;
		flex-shrink: 0;
		border-radius: 0 2px 2px 0;
		background: transparent;
		transition: background 0.2s ease;
	}

	.session-card.selected .card-accent {
		background: var(--border-active);
	}

	.card-accent.accent-live {
		background: var(--green-bright);
	}

	.session-card.selected .card-accent.accent-live {
		background: var(--green-bright);
	}

	.card-body {
		flex: 1;
		min-width: 0;
		padding: 8px 12px 8px 10px;
	}

	.card-top {
		display: flex;
		align-items: center;
		gap: 7px;
	}

	.status-dot {
		width: 7px;
		height: 7px;
		min-width: 7px;
		border-radius: 50%;
		flex-shrink: 0;
	}

	.dot-live {
		background: var(--green-bright);
		box-shadow: 0 0 5px var(--green-bright);
		animation: pulse-dot 2s ease-in-out infinite;
	}

	.dot-ended {
		background: var(--gray-dim);
	}

	@keyframes pulse-dot {
		0%, 100% {
			opacity: 1;
			box-shadow: 0 0 5px var(--green-bright);
		}
		50% {
			opacity: 0.45;
			box-shadow: 0 0 2px var(--green-bright);
		}
	}

	.card-summary {
		font-size: 12px;
		color: var(--text-primary);
		line-height: 1.35;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		flex: 1;
	}

	.card-meta {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-top: 4px;
		padding-left: 14px;
		gap: 6px;
	}

	.card-path {
		font-size: 10px;
		color: var(--text-secondary);
		font-family: var(--font-mono);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
		min-width: 0;
	}

	.card-time {
		font-size: 10px;
		color: var(--text-secondary);
		white-space: nowrap;
		flex-shrink: 0;
	}
</style>
