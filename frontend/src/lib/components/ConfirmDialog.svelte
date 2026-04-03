<script lang="ts">
	let { title, message, confirmLabel = 'Подтвердить', onconfirm, oncancel }: {
		title: string;
		message: string;
		confirmLabel?: string;
		onconfirm: () => void;
		oncancel: () => void;
	} = $props();

	function handleBackdrop(e: MouseEvent) {
		if (e.target === e.currentTarget) oncancel();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') oncancel();
	}
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="modal-backdrop" onclick={handleBackdrop} onkeydown={handleKeydown}>
	<div class="modal" role="dialog" aria-label={title}>
		<div class="modal-header">
			<h3>{title}</h3>
			<button class="close-btn" onclick={oncancel}>✕</button>
		</div>
		<div class="modal-body">
			<p class="modal-message">{message}</p>
		</div>
		<div class="modal-footer">
			<button class="btn btn-secondary" onclick={oncancel}>Отмена</button>
			<button class="btn btn-danger" onclick={onconfirm}>{confirmLabel}</button>
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
	}

	.modal-message {
		margin: 0;
		font-size: 13px;
		color: var(--text-primary);
		line-height: 1.5;
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

	.btn-danger:hover {
		filter: brightness(1.2);
	}
</style>
