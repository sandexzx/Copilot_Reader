<script lang="ts">
  import { settingsStore } from '$lib/stores/settings.svelte';

  let { sessionId = '', isConnected = false, isActive = false } = $props();

  function openSettings() {
    settingsStore.showSettings = true;
  }
</script>

<header class="header">
  <div class="breadcrumb">
    <span>Sessions</span>
    <span class="bc-sep">›</span>
    <span>{sessionId || '—'}</span>
    <span class="bc-sep">›</span>
    <span class="bc-current">Events</span>
  </div>
  {#if sessionId}
    {#if isConnected}
      <div class="status-live">
        <div class="dot"></div>
        LIVE
      </div>
    {:else if !isActive}
      <div class="status-ended">ENDED</div>
    {/if}
  {/if}
  <div class="header-spacer"></div>
  <button class="settings-btn" onclick={openSettings} title="Настройки AI перевода" class:configured={settingsStore.isConfigured}>
    ⚙️
  </button>
  <input class="search-bar" type="text" placeholder="Search events… (⌘K)">
</header>

<style>
  .header {
    height: var(--header-height);
    min-height: var(--header-height);
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 16px;
    gap: 12px;
  }

  .breadcrumb {
    font-size: 12px;
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .breadcrumb span {
    color: var(--text-accent);
    cursor: pointer;
  }

  .breadcrumb span:hover {
    text-decoration: underline;
  }

  .bc-sep {
    color: var(--gray-dim);
    cursor: default !important;
  }

  .bc-sep:hover {
    text-decoration: none !important;
  }

  .bc-current {
    color: var(--text-primary) !important;
    cursor: default !important;
  }

  .bc-current:hover {
    text-decoration: none !important;
  }

  .status-live {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11px;
    font-weight: 600;
    color: var(--green-bright);
    flex-shrink: 0;
  }

  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--green-bright);
    animation: pulse 2s infinite;
  }

  @keyframes pulse {
    0%, 100% {
      opacity: 1;
      box-shadow: 0 0 3px var(--green-bright);
    }
    50% {
      opacity: 0.4;
      box-shadow: none;
    }
  }

  .status-ended {
    font-size: 11px;
    font-weight: 600;
    color: var(--gray-dim);
    flex-shrink: 0;
  }

  .header-spacer {
    flex: 1;
  }

  .search-bar {
    width: 220px;
    height: 24px;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    padding: 0 8px;
    color: var(--text-primary);
    font-size: 11px;
    font-family: var(--font-sans);
    outline: none;
  }

  .search-bar:focus {
    border-color: var(--border-active);
  }

  .search-bar::placeholder {
    color: var(--text-secondary);
  }

  .settings-btn {
    background: none;
    border: 1px solid transparent;
    font-size: 16px;
    cursor: pointer;
    padding: 2px 6px;
    border-radius: 4px;
    transition: background 0.15s, border-color 0.15s;
    filter: grayscale(0.5);
    line-height: 1;
  }

  .settings-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    filter: none;
  }

  .settings-btn.configured {
    filter: none;
    border-color: rgba(78, 201, 176, 0.3);
  }
</style>
