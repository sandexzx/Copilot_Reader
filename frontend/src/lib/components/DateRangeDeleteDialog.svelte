<script lang="ts">
	import { sessionsStore } from '$lib/stores/sessions.svelte';
	import { deleteSessions } from '$lib/api';

	let { onclose }: { onclose: () => void } = $props();

	let isSubmitting = $state(false);
	let selectedDates = $state<Set<string>>(new Set());

	interface DateGroup {
		date: string;
		dateLabel: string;
		total: number;
		inactive: number;
		active: number;
	}

	let dateGroups: DateGroup[] = $derived.by(() => {
		const groups = new Map<string, { total: number; inactive: number; active: number }>();

		for (const s of sessionsStore.sessions) {
			const dateKey = s.updated_at.slice(0, 10);
			const existing = groups.get(dateKey) || { total: 0, inactive: 0, active: 0 };
			existing.total++;
			if (s.is_active) {
				existing.active++;
			} else {
				existing.inactive++;
			}
			groups.set(dateKey, existing);
		}

		return Array.from(groups.entries())
			.sort((a, b) => b[0].localeCompare(a[0]))
			.map(([date, counts]) => ({
				date,
				dateLabel: formatDate(date),
				...counts,
			}));
	});

	function formatDate(dateStr: string): string {
		const d = new Date(dateStr + 'T00:00:00');
		return d.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
	}

	function toggleDate(date: string) {
		const next = new Set(selectedDates);
		if (next.has(date)) {
			next.delete(date);
		} else {
			next.add(date);
		}
		selectedDates = next;
	}

	function selectAll() {
		selectedDates = new Set(dateGroups.filter(g => g.inactive > 0).map(g => g.date));
	}

	function clearAll() {
		selectedDates = new Set();
	}

	let totalToDelete = $derived.by(() => {
		let count = 0;
		for (const group of dateGroups) {
			if (selectedDates.has(group.date)) {
				count += group.inactive;
			}
		}
		return count;
	});

	async function handleConfirm() {
		if (totalToDelete === 0) return;
		isSubmitting = true;
		try {
			const idsToDelete = sessionsStore.sessions
				.filter(s => {
					if (s.is_active) return false;
					const dateKey = s.updated_at.slice(0, 10);
					return selectedDates.has(dateKey);
				})
				.map(s => s.id);

			const result = await deleteSessions(idsToDelete);
			sessionsStore.lastDeleteResult = result;
			if (sessionsStore.selectedSessionId && result.deleted.includes(sessionsStore.selectedSessionId)) {
				sessionsStore.selectedSessionId = null;
			}
			await sessionsStore.loadSessions();
			onclose();
		} finally {
			isSubmitting = false;
		}
	}

	function handleBackdrop(e: MouseEvent) {
		if (e.target === e.currentTarget) onclose();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') onclose();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="modal-backdrop" onclick={handleBackdrop} onkeydown={handleKeydown}>
	<div class="modal" role="dialog" aria-label="Удаление по датам">
		<div class="modal-header">
			<h3>Удаление по датам</h3>
			<button class="close-btn" onclick={onclose}>✕</button>
		</div>

		<div class="modal-body">
			{#if dateGroups.length === 0}
				<div class="empty-state">Нет сессий для отображения</div>
			{:else}
				<div class="date-actions">
					<button class="link-btn" onclick={selectAll}>Выбрать все</button>
					<button class="link-btn" onclick={clearAll}>Сбросить</button>
				</div>

				<div class="date-list">
					{#each dateGroups as group (group.date)}
						<label class="date-row" class:disabled={group.inactive === 0}>
							<input
								type="checkbox"
								checked={selectedDates.has(group.date)}
								disabled={group.inactive === 0}
								onchange={() => toggleDate(group.date)}
							/>
							<div class="date-info">
								<span class="date-label">{group.dateLabel}</span>
								<span class="date-count">
									{group.inactive} к удалению{#if group.active > 0}<span class="active-note">, {group.active} активн.</span>{/if}
								</span>
							</div>
						</label>
					{/each}
				</div>
			{/if}

			{#if totalToDelete > 0}
				<div class="preview">
					Будет удалено: <strong>{totalToDelete}</strong> неактивных сессий
				</div>
			{/if}
		</div>

		<div class="modal-footer">
			<button class="btn btn-secondary" onclick={onclose}>Отмена</button>
			<button
				class="btn btn-danger"
				onclick={handleConfirm}
				disabled={totalToDelete === 0 || isSubmitting}
			>
				{#if isSubmitting}
					<span class="spinner"></span>
				{/if}
				Удалить
			</button>
		</div>
	</div>
</div>

<style>
	.modal-backdrop {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.6);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		backdrop-filter: blur(2px);
	}

	.modal {
		background: var(--bg-panel);
		border: 1px solid var(--border);
		border-radius: 8px;
		width: 380px;
		max-width: 90vw;
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: 16px 20px;
		border-bottom: 1px solid var(--border);
	}

	.modal-header h3 {
		margin: 0;
		font-size: 14px;
		font-weight: 600;
		color: var(--text-primary);
	}

	.close-btn {
		background: none;
		border: none;
		color: var(--text-secondary);
		font-size: 16px;
		cursor: pointer;
		padding: 2px 6px;
		border-radius: 4px;
		transition: background 0.15s;
	}

	.close-btn:hover {
		background: rgba(255, 255, 255, 0.1);
		color: var(--text-primary);
	}

	.modal-body {
		padding: 20px;
		display: flex;
		flex-direction: column;
		gap: 12px;
	}

	.date-actions {
		display: flex;
		gap: 12px;
		padding-bottom: 8px;
		border-bottom: 1px solid var(--border);
	}

	.link-btn {
		background: none;
		border: none;
		color: var(--border-active);
		font-size: 11px;
		cursor: pointer;
		padding: 0;
		text-decoration: underline;
		text-underline-offset: 2px;
	}

	.link-btn:hover {
		color: var(--text-primary);
	}

	.date-list {
		max-height: 320px;
		overflow-y: auto;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.date-row {
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 6px 8px;
		border-radius: var(--radius-sm);
		cursor: pointer;
		transition: background 0.15s;
	}

	.date-row:hover:not(.disabled) {
		background: var(--bg-hover);
	}

	.date-row.disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.date-row input[type="checkbox"] {
		width: 14px;
		height: 14px;
		accent-color: var(--border-active);
		cursor: inherit;
		flex-shrink: 0;
	}

	.date-info {
		display: flex;
		flex-direction: column;
		gap: 1px;
		min-width: 0;
	}

	.date-label {
		font-size: 12px;
		color: var(--text-primary);
		font-weight: 500;
	}

	.date-count {
		font-size: 10px;
		color: var(--text-secondary);
	}

	.active-note {
		color: var(--green-bright);
	}

	.empty-state {
		text-align: center;
		padding: 20px;
		font-size: 12px;
		color: var(--text-secondary);
	}

	.preview {
		padding: 8px 10px;
		border-radius: var(--radius-sm);
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border);
		font-size: 11px;
		color: var(--text-primary);
	}

	.preview strong {
		color: var(--red);
	}

	.modal-footer {
		display: flex;
		justify-content: flex-end;
		gap: 8px;
		padding: 12px 20px;
		border-top: 1px solid var(--border);
	}

	.btn {
		height: 28px;
		padding: 0 14px;
		border-radius: 4px;
		font-size: 12px;
		font-weight: 500;
		cursor: pointer;
		border: 1px solid transparent;
		transition: background 0.15s;
		display: flex;
		align-items: center;
		justify-content: center;
		gap: 6px;
	}

	.btn:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}

	.btn-secondary {
		background: transparent;
		border-color: var(--border);
		color: var(--text-secondary);
	}

	.btn-secondary:hover {
		background: rgba(255, 255, 255, 0.05);
	}

	.btn-danger {
		background: var(--red);
		color: #fff;
		border-color: var(--red);
	}

	.btn-danger:hover:not(:disabled) {
		filter: brightness(1.2);
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
