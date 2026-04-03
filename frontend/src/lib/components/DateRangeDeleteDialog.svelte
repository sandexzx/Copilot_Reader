<script lang="ts">
	import { sessionsStore } from '$lib/stores/sessions.svelte';

	let { onclose }: { onclose: () => void } = $props();

	let dateFrom = $state('');
	let dateTo = $state('');
	let isSubmitting = $state(false);

	let validRange = $derived(dateFrom !== '' && dateTo !== '' && dateFrom <= dateTo);

	let sessionsInRange = $derived.by(() => {
		if (!dateFrom || !dateTo) return [];
		const from = new Date(dateFrom);
		const to = new Date(dateTo);
		to.setHours(23, 59, 59, 999);
		return sessionsStore.sessions.filter(s => {
			if (s.is_active) return false;
			const updated = new Date(s.updated_at);
			return updated >= from && updated <= to;
		});
	});

	let validationError = $derived.by(() => {
		if (dateFrom && dateTo && dateFrom > dateTo) return 'Дата «От» не может быть позже даты «До»';
		return '';
	});

	async function handleConfirm() {
		if (!validRange || sessionsInRange.length === 0) return;
		isSubmitting = true;
		try {
			await sessionsStore.deleteByDateRange(dateFrom, dateTo);
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
			<div class="date-fields">
				<label class="field">
					<span class="field-label">От</span>
					<input
						type="date"
						class="field-input"
						bind:value={dateFrom}
					/>
				</label>
				<label class="field">
					<span class="field-label">До</span>
					<input
						type="date"
						class="field-input"
						bind:value={dateTo}
					/>
				</label>
			</div>

			{#if validationError}
				<div class="validation-error">{validationError}</div>
			{/if}

			{#if validRange}
				<div class="preview">
					{#if sessionsInRange.length === 0}
						<span class="preview-empty">Нет неактивных сессий в выбранном диапазоне</span>
					{:else}
						<span class="preview-count">
							Будет удалено: <strong>{sessionsInRange.length}</strong> неактивных сессий
						</span>
					{/if}
				</div>
			{/if}
		</div>

		<div class="modal-footer">
			<button class="btn btn-secondary" onclick={onclose}>Отмена</button>
			<button
				class="btn btn-danger"
				onclick={handleConfirm}
				disabled={!validRange || sessionsInRange.length === 0 || isSubmitting}
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

	.date-fields {
		display: flex;
		gap: 12px;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 4px;
		flex: 1;
	}

	.field-label {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-secondary);
	}

	.field-input {
		height: 32px;
		background: var(--bg-input);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0 10px;
		color: var(--text-primary);
		font-size: 12px;
		font-family: var(--font-sans);
		outline: none;
		color-scheme: dark;
	}

	.field-input:focus {
		border-color: var(--border-active);
	}

	.validation-error {
		font-size: 11px;
		color: var(--red);
	}

	.preview {
		padding: 8px 10px;
		border-radius: var(--radius-sm);
		background: rgba(255, 255, 255, 0.04);
		border: 1px solid var(--border);
	}

	.preview-empty {
		font-size: 11px;
		color: var(--text-secondary);
	}

	.preview-count {
		font-size: 11px;
		color: var(--text-primary);
	}

	.preview-count strong {
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
