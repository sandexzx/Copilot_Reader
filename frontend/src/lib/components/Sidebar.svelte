<script lang="ts">
  import SessionCard from './SessionCard.svelte';
  import DailyUsage from './DailyUsage.svelte';
  import DeleteToolbar from './DeleteToolbar.svelte';
  import ConfirmDialog from './ConfirmDialog.svelte';
  import DateRangeDeleteDialog from './DateRangeDeleteDialog.svelte';
  import { sessionsStore } from '$lib/stores/sessions.svelte';
  import type { SessionSummary } from '$lib/types';

  let { onselect }: { onselect: (session: SessionSummary) => void } = $props();

  let searchInput = $state('');
  let searchQuery = $state('');
  let debounceTimer: ReturnType<typeof setTimeout> | undefined;
  let showConfirmDialog = $state(false);
  let showDateRangeDialog = $state(false);

  function handleSearchInput(e: Event) {
    const value = (e.target as HTMLInputElement).value;
    searchInput = value;
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      searchQuery = value;
    }, 200);
  }

  let filtered = $derived.by(() => {
    const q = searchQuery.toLowerCase().trim();
    if (!q) return sessionsStore.sessions;
    return sessionsStore.sessions.filter(s =>
      s.summary.toLowerCase().includes(q) || s.cwd.toLowerCase().includes(q)
    );
  });

  let activeSessions = $derived(filtered.filter(s => s.is_active));
  let inactiveSessions = $derived(filtered.filter(s => !s.is_active));

  function handleSelect(id: string) {
    const session = sessionsStore.sessions.find(s => s.id === id);
    if (session) {
      sessionsStore.selectSession(id);
      onselect(session);
    }
  }
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
      <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2z" fill="#333"/>
      <path d="M12 2C6.477 2 2 6.477 2 12s4.477 10 10 10 10-4.477 10-10S17.523 2 12 2zm-.5 4.5a1.5 1.5 0 0 1 2.838.68l-.338 2.82h2.5a1 1 0 0 1 .928 1.371l-2.5 6a1 1 0 0 1-.928.629H10a1 1 0 0 1-1-1v-4.5a1 1 0 0 1 1-1h1.08l.42-3.5a1.5 1.5 0 0 1 0-1.5z" fill="#569cd6"/>
      <circle cx="9" cy="10" r="1.5" fill="#4ec9b0"/>
      <circle cx="15" cy="10" r="1.5" fill="#4ec9b0"/>
      <path d="M8.5 14.5c0 0 1.5 2 3.5 2s3.5-2 3.5-2" stroke="#4ec9b0" stroke-width="1.2" stroke-linecap="round" fill="none"/>
    </svg>
    <div class="sidebar-title-group">
      <div class="sidebar-title">Copilot Reader</div>
      <div class="sidebar-subtitle">Session Explorer</div>
    </div>
    <button
      class="manage-btn"
      class:active={sessionsStore.manageMode}
      onclick={() => sessionsStore.toggleManageMode()}
      title={sessionsStore.manageMode ? 'Выйти из режима управления' : 'Управление сессиями'}
    >
      {sessionsStore.manageMode ? '✕' : '✎'}
    </button>
  </div>

  <div class="search-wrapper">
    <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
      <circle cx="11" cy="11" r="8"/>
      <line x1="21" y1="21" x2="16.65" y2="16.65"/>
    </svg>
    <input
      class="search-input"
      type="text"
      placeholder="Filter sessions…"
      value={searchInput}
      oninput={handleSearchInput}
    />
  </div>

  <DailyUsage />

  <div class="session-list">
    {#if sessionsStore.isLoading}
      <div class="session-list-status">
        <div class="loading-spinner"></div>
        <span>Loading sessions…</span>
      </div>
    {:else if sessionsStore.error}
      <div class="session-list-status error">
        {sessionsStore.error}
      </div>
    {:else if filtered.length === 0}
      <div class="session-list-status">
        {searchQuery ? 'No matching sessions' : 'No sessions found'}
      </div>
    {:else}
      {#if activeSessions.length > 0}
        <div class="sidebar-section-label">Active ({activeSessions.length})</div>
        {#each activeSessions as session (session.id)}
          <SessionCard
            {session}
            selected={sessionsStore.selectedSessionId === session.id}
            manageMode={sessionsStore.manageMode}
            onselect={handleSelect}
          />
        {/each}
      {/if}

      {#if inactiveSessions.length > 0}
        <div class="sidebar-section-label">Recent</div>
        {#each inactiveSessions as session (session.id)}
          <SessionCard
            {session}
            selected={sessionsStore.selectedSessionId === session.id}
            manageMode={sessionsStore.manageMode}
            onselect={handleSelect}
          />
        {/each}
      {/if}
    {/if}
  </div>

  {#if sessionsStore.manageMode}
    <DeleteToolbar
      onconfirmdelete={() => showConfirmDialog = true}
      ondaterange={() => showDateRangeDialog = true}
    />
  {/if}
</aside>

{#if showConfirmDialog}
  <ConfirmDialog
    title="Удаление сессий"
    message={`Удалить ${sessionsStore.selectedCount} выбранных сессий? Это действие необратимо.`}
    confirmLabel="Удалить"
    onconfirm={() => { showConfirmDialog = false; sessionsStore.deleteSelected(); }}
    oncancel={() => showConfirmDialog = false}
  />
{/if}

{#if showDateRangeDialog}
  <DateRangeDeleteDialog onclose={() => showDateRangeDialog = false} />
{/if}

<style>
  .sidebar {
    width: var(--sidebar-width);
    min-width: var(--sidebar-width);
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .sidebar-header {
    padding: 12px 14px;
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .sidebar-header svg {
    flex-shrink: 0;
  }

  .sidebar-title-group {
    flex: 1;
    min-width: 0;
  }

  .sidebar-title {
    font-size: 13px;
    font-weight: 600;
    color: var(--text-primary);
    white-space: nowrap;
  }

  .sidebar-subtitle {
    font-size: 10px;
    color: var(--text-secondary);
    margin-top: 1px;
  }

  .manage-btn {
    background: none;
    border: 1px solid transparent;
    color: var(--text-secondary);
    font-size: 14px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    transition: all 0.15s;
    line-height: 1;
    flex-shrink: 0;
  }

  .manage-btn:hover {
    color: var(--text-primary);
    background: rgba(255, 255, 255, 0.06);
  }

  .manage-btn.active {
    color: var(--red);
    border-color: rgba(244, 71, 71, 0.3);
    background: rgba(244, 71, 71, 0.1);
  }

  .search-wrapper {
    position: relative;
    padding: 8px 10px;
    border-bottom: 1px solid var(--border);
  }

  .search-icon {
    position: absolute;
    left: 18px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--text-secondary);
    pointer-events: none;
  }

  .search-input {
    width: 100%;
    height: 28px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0 8px 0 28px;
    color: var(--text-primary);
    font-size: 11px;
    font-family: var(--font-sans);
    outline: none;
    transition: border-color 0.15s ease;
  }

  .search-input:focus {
    border-color: var(--border-active);
  }

  .search-input::placeholder {
    color: var(--text-secondary);
  }

  .sidebar-section-label {
    padding: 10px 14px 4px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    color: var(--text-secondary);
    letter-spacing: 0.8px;
    user-select: none;
  }

  .session-list {
    flex: 1;
    overflow-y: auto;
    padding: 0 0 4px;
  }

  .session-list-status {
    padding: 24px 14px;
    font-size: 11px;
    color: var(--text-secondary);
    text-align: center;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
  }

  .session-list-status.error {
    color: var(--red);
  }

  .loading-spinner {
    width: 18px;
    height: 18px;
    border: 2px solid var(--border);
    border-top-color: var(--border-active);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }
</style>
