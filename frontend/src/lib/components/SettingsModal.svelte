<script lang="ts">
	import { settingsStore } from '$lib/stores/settings.svelte';

	interface AiModel {
		id: string;
		provider: string;
	}

	let localApiKey = $state(settingsStore.apiKey);
	let localModel = $state(settingsStore.model);
	let models = $state<AiModel[]>([]);
	let loadingModels = $state(false);
	let modelError = $state('');

	async function fetchModels() {
		loadingModels = true;
		modelError = '';
		try {
			const resp = await fetch('/api/ai/models');
			if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
			const data = await resp.json();
			models = data.models || [];
		} catch (e) {
			modelError = `Ошибка загрузки: ${e instanceof Error ? e.message : e}`;
		} finally {
			loadingModels = false;
		}
	}

	function handleSave() {
		settingsStore.apiKey = localApiKey.trim();
		settingsStore.model = localModel;
		settingsStore.showSettings = false;
	}

	function handleCancel() {
		settingsStore.showSettings = false;
	}

	function handleBackdrop(e: MouseEvent) {
		if (e.target === e.currentTarget) handleCancel();
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Escape') handleCancel();
	}

	$effect(() => {
		if (settingsStore.showSettings) {
			localApiKey = settingsStore.apiKey;
			localModel = settingsStore.model;
			fetchModels();
		}
	});
</script>

{#if settingsStore.showSettings}
	<!-- svelte-ignore a11y_no_static_element_interactions -->
	<div class="modal-backdrop" onclick={handleBackdrop} onkeydown={handleKeydown}>
		<div class="modal" role="dialog" aria-label="Настройки AI">
			<div class="modal-header">
				<h3>⚙️ Настройки перевода</h3>
				<button class="close-btn" onclick={handleCancel}>✕</button>
			</div>

			<div class="modal-body">
				<label class="field">
					<span class="field-label">API ключ AITunnel</span>
					<input
						type="password"
						bind:value={localApiKey}
						placeholder="sk-aitunnel-..."
						class="field-input"
					/>
					<span class="field-hint">
						Получите на <a href="https://aitunnel.ru" target="_blank" rel="noopener">aitunnel.ru</a>
					</span>
				</label>

				<label class="field">
					<span class="field-label">Модель</span>
					{#if loadingModels}
						<div class="loading">Загрузка моделей…</div>
					{:else if modelError}
						<div class="error">{modelError}</div>
						<input
							type="text"
							bind:value={localModel}
							placeholder="gpt-4.1"
							class="field-input"
						/>
					{:else if models.length > 0}
						<select bind:value={localModel} class="field-select">
							{#each models as m (m.id)}
								<option value={m.id}>{m.id} ({m.provider})</option>
							{/each}
						</select>
					{:else}
						<input
							type="text"
							bind:value={localModel}
							placeholder="gpt-4.1"
							class="field-input"
						/>
					{/if}
				</label>
			</div>

			<div class="modal-footer">
				<button class="btn btn-secondary" onclick={handleCancel}>Отмена</button>
				<button class="btn btn-primary" onclick={handleSave}>Сохранить</button>
			</div>
		</div>
	</div>
{/if}

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
		width: 420px;
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
		gap: 16px;
	}

	.field {
		display: flex;
		flex-direction: column;
		gap: 4px;
	}

	.field-label {
		font-size: 12px;
		font-weight: 500;
		color: var(--text-secondary);
	}

	.field-input, .field-select {
		height: 32px;
		background: var(--bg-input);
		border: 1px solid var(--border);
		border-radius: 4px;
		padding: 0 10px;
		color: var(--text-primary);
		font-size: 12px;
		font-family: var(--font-mono);
		outline: none;
	}

	.field-input:focus, .field-select:focus {
		border-color: var(--border-active);
	}

	.field-select {
		cursor: pointer;
	}

	.field-select option {
		background: var(--bg-panel);
		color: var(--text-primary);
	}

	.field-hint {
		font-size: 10px;
		color: var(--text-secondary);
	}

	.field-hint a {
		color: var(--text-accent);
	}

	.loading {
		font-size: 11px;
		color: var(--text-secondary);
		padding: 6px 0;
	}

	.error {
		font-size: 11px;
		color: #f44747;
		padding: 4px 0;
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

	.btn-primary {
		background: var(--text-accent);
		color: #fff;
		border-color: var(--text-accent);
	}

	.btn-primary:hover {
		filter: brightness(1.15);
	}
</style>
