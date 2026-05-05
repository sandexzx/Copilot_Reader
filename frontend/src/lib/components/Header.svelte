<script lang="ts">
  import { settingsStore } from '$lib/stores/settings.svelte';
  import { dailyUsageStore } from '$lib/stores/dailyUsage.svelte';
  import { fetchCopilotUser } from '$lib/api';
  import type { CopilotUserInfo } from '$lib/types';

  const OUTPUT_RATE_LIMIT = 640_000;

  let { sessionId = '', isConnected = false, isActive = false } = $props();

  let dailyOutputTokens = $derived(dailyUsageStore.data?.totals?.output_tokens ?? 0);
  let dailyOutputRatio = $derived(dailyOutputTokens / OUTPUT_RATE_LIMIT);
  let dailyOutputPct = $derived(Math.min(dailyOutputRatio * 100, 100));
  let rateLimitColor = $derived(
    dailyOutputRatio > 0.8 ? 'var(--red)' :
    dailyOutputRatio > 0.5 ? 'var(--color-warning)' :
    'var(--green)'
  );

  let copilotUser = $state<CopilotUserInfo | null>(null);

  function openSettings() {
    settingsStore.showSettings = true;
  }

  $effect(() => {
    dailyUsageStore.init();
    fetchCopilotUser().then(u => copilotUser = u).catch(() => {});
  });
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
  {#if copilotUser?.current_user}
    <div class="user-badge" title={copilotUser.all_users.length > 1 ? `Accounts: ${copilotUser.all_users.join(', ')}` : copilotUser.current_user}>
      <span class="user-icon">👤</span>
      <span class="user-login">{copilotUser.current_user}</span>
      {#if copilotUser.all_users.length > 1}
        <span class="user-count">{copilotUser.all_users.length}</span>
      {/if}
    </div>
  {/if}
  {#if dailyUsageStore.data}
    <div class="rate-limit-badge" title="Daily output tokens: {dailyOutputTokens.toLocaleString()} / 640K">
      <span class="rate-label">Rate</span>
      <div class="rate-track">
        <div class="rate-fill" style="width: {dailyOutputPct}%; background: {rateLimitColor}"></div>
      </div>
      <span class="rate-pct" style="color: {rateLimitColor}">{Math.round(dailyOutputPct)}%</span>
    </div>
  {/if}
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

  .rate-limit-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .user-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
    padding: 2px 8px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--border);
    border-radius: 10px;
  }

  .user-icon {
    font-size: 11px;
    line-height: 1;
  }

  .user-login {
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--text-accent);
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .user-count {
    font-size: 9px;
    font-family: var(--font-mono);
    color: var(--text-secondary);
    background: rgba(255, 255, 255, 0.08);
    padding: 0 4px;
    border-radius: 6px;
    line-height: 15px;
  }

  .rate-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-family: var(--font-mono);
  }

  .rate-track {
    width: 80px;
    height: 6px;
    background: var(--bg-input);
    border-radius: 3px;
    overflow: hidden;
    position: relative;
  }

  .rate-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 1s ease, background 0.5s ease;
    min-width: 2px;
  }

  .rate-pct {
    font-size: 11px;
    font-weight: 600;
    font-family: var(--font-mono);
    min-width: 28px;
    text-align: right;
  }
</style>
