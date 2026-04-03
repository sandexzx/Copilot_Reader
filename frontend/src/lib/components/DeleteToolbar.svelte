<script lang="ts">
	import { sessionsStore } from '$lib/stores/sessions.svelte';

	let { onconfirmdelete, ondaterange }: {
		onconfirmdelete: () => void;
		ondaterange: () => void;
	} = $props();
</script>

<div class="delete-toolbar">
	{#if sessionsStore.lastDeleteResult}
		<div class="result-row">
			<span class="result-text">
				Удалено: {sessionsStore.lastDeleteResult.deleted.length}.
				{#if sessionsStore.lastDeleteResult.skipped_active.length > 0}
					Пропущено: {sessionsStore.lastDeleteResult.skipped_active.length} (активные)
				{/if}
			</span>
			<button class="link-btn" onclick={() => sessionsStore.dismissDeleteResult()}>✕</button>
		</div>
	{:else if sessionsStore.deleteError}
		<div class="result-row error">
			<span class="result-text">{sessionsStore.deleteError}</span>
			<button class="link-btn" onclick={() => sessionsStore.dismissDeleteResult()}>✕</button>
		</div>
	{/if}

	<div class="toolbar-row">
		<span class="selected-count">Выбрано: {sessionsStore.selectedCount}</span>
		<div class="toolbar-actions">
			<button
				class="link-btn"
				onclick={() => sessionsStore.selectAllInactive()}
				disabled={sessionsStore.isDeleting}
			>Все неактивные</button>
			<button
				class="link-btn"
				onclick={() => sessionsStore.clearDeleteSelection()}
				disabled={sessionsStore.isDeleting}
			>Сбросить</button>
		</div>
	</div>

	<div class="toolbar-buttons">
		<button
			class="btn btn-danger"
			onclick={onconfirmdelete}
			disabled={sessionsStore.selectedCount === 0 || sessionsStore.isDeleting}
		>
			{#if sessionsStore.isDeleting}
				<span class="spinner"></span>
			{/if}
			Удалить
		</button>
		<button
			class="btn btn-secondary"
			onclick={ondaterange}
			disabled={sessionsStore.isDeleting}
		>По датам…</button>
	</div>
</div>

<style>
	.delete-toolbar {
		padding: 8px 10px;
		background: var(--bg-panel);
		border-top: 1px solid var(--border);
		display: flex;
		flex-direction: column;
		gap: 6px;
		flex-shrink: 0;
	}

	.toolbar-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 6px;
	}

	.selected-count {
		font-size: 11px;
		font-weight: 500;
		color: var(--text-primary);
	}

	.toolbar-actions {
		display: flex;
		gap: 8px;
	}

	.toolbar-buttons {
		display: flex;
		gap: 6px;
	}

	.link-btn {
		background: none;
		border: none;
		color: var(--text-accent);
		font-size: 11px;
		cursor: pointer;
		padding: 0;
		transition: opacity 0.15s;
	}

	.link-btn:hover {
		text-decoration: underline;
	}

	.link-btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.result-row {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 6px;
		padding: 4px 6px;
		border-radius: var(--radius-sm);
		background: rgba(115, 201, 145, 0.1);
		border: 1px solid rgba(115, 201, 145, 0.2);
	}

	.result-row.error {
		background: rgba(244, 71, 71, 0.1);
		border-color: rgba(244, 71, 71, 0.2);
	}

	.result-text {
		font-size: 11px;
		color: var(--text-primary);
	}

	.result-row.error .result-text {
		color: var(--red);
	}

	.btn {
		height: 26px;
		padding: 0 12px;
		border-radius: var(--radius-sm);
		font-size: 11px;
		font-weight: 500;
		cursor: pointer;
		border: 1px solid transparent;
		transition: background 0.15s, filter 0.15s;
		flex: 1;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
	}

	.btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-danger {
		background: var(--red);
		color: #fff;
		border-color: var(--red);
	}

	.btn-danger:hover:not(:disabled) {
		filter: brightness(1.2);
	}

	.btn-secondary {
		background: transparent;
		border-color: var(--border);
		color: var(--text-secondary);
	}

	.btn-secondary:hover:not(:disabled) {
		background: rgba(255, 255, 255, 0.05);
	}

	.spinner {
		width: 12px;
		height: 12px;
		border: 2px solid rgba(255, 255, 255, 0.3);
		border-top-color: #fff;
		border-radius: 50%;
		animation: spin 0.8s linear infinite;
	}

	@keyframes spin {
		to { transform: rotate(360deg); }
	}
</style>
