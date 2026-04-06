<script lang="ts">
  import { dailyUsageStore } from '$lib/stores/dailyUsage.svelte';

  let expanded = $state(true);

  // Pricing per 1M tokens (USD)
  const MODEL_PRICING: Record<string, { input: number; output: number }> = {
    'claude-opus-4.6': { input: 5, output: 25 },
  };
  const USD_TO_RUB = 81.25;

  let data = $derived(dailyUsageStore.data);
  let loading = $derived(dailyUsageStore.loading);

  function formatTokens(n: number): string {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000) return (n / 1_000).toFixed(1) + 'K';
    return n.toString();
  }

  function shortenModel(name: string): string {
    return name.replace(/^claude-/, '');
  }

  let totalCostUsd = $derived.by(() => {
    if (!data) return 0;
    let cost = 0;
    for (const [model, usage] of Object.entries(data.models)) {
      const pricing = MODEL_PRICING[model];
      if (!pricing) continue;
      cost += (usage.input_tokens / 1_000_000) * pricing.input;
      cost += (usage.output_tokens / 1_000_000) * pricing.output;
    }
    return cost;
  });

  let totalCostRub = $derived(totalCostUsd * USD_TO_RUB);

  function formatCost(n: number): string {
    if (n < 0.01) return '< 0.01';
    return n.toFixed(2);
  }

  $effect(() => {
    dailyUsageStore.init();
  });

  function toggle() {
    expanded = !expanded;
  }
</script>

<div class="daily-usage">
  <button class="daily-usage-header" onclick={toggle}>
    <span class="header-left">
      <span class="header-icon">📊</span>
      <span class="header-title">Today's Usage</span>
    </span>
    {#if data}
      <span class="session-count">{data.sessions_count} sess</span>
    {/if}
    <span class="chevron">{expanded ? '▾' : '▸'}</span>
  </button>

  {#if expanded}
    {#if loading && !data}
      <div class="daily-usage-loading">
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
        <div class="loading-dot"></div>
      </div>
    {:else if data}
      <div class="daily-usage-body">
        {#each Object.entries(data.models) as [model, usage]}
          <div class="model-row">
            <span class="model-name" title={model}>{shortenModel(model)}</span>
            <div class="token-counts">
              <span class="token in" title="Input tokens">↑{formatTokens(usage.input_tokens)}</span>
              <span class="token out" title="Output tokens">↓{formatTokens(usage.output_tokens)}</span>
              <span class="token cache" title="Cache read tokens">⚡{formatTokens(usage.cache_read_tokens)}</span>
            </div>
          </div>
        {/each}
        <div class="totals-row">
          <span class="totals-label">Total</span>
          <div class="token-counts">
            <span class="token in">↑{formatTokens(data.totals.input_tokens)}</span>
            <span class="token out">↓{formatTokens(data.totals.output_tokens)}</span>
            <span class="token cache">⚡{formatTokens(data.totals.cache_read_tokens)}</span>
          </div>
        </div>
        {#if totalCostUsd > 0}
          <div class="cost-row">
            <span class="cost-label">💰 Cost</span>
            <span class="cost-value">${formatCost(totalCostUsd)} · {formatCost(totalCostRub)}₽</span>
          </div>
        {/if}
      </div>
    {/if}
  {/if}
</div>

<style>
  .daily-usage {
    border-bottom: 1px solid var(--border);
  }

  .daily-usage-header {
    display: flex;
    align-items: center;
    width: 100%;
    padding: 6px 10px;
    background: none;
    border: none;
    color: var(--text-primary);
    font-size: 11px;
    font-family: var(--font-sans);
    cursor: pointer;
    gap: 6px;
    user-select: none;
  }

  .daily-usage-header:hover {
    background: var(--bg-hover);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 4px;
    flex-shrink: 0;
  }

  .header-icon {
    font-size: 11px;
    line-height: 1;
  }

  .header-title {
    font-weight: 600;
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
  }

  .session-count {
    margin-left: auto;
    font-size: 10px;
    color: var(--text-secondary);
    font-family: var(--font-mono);
  }

  .chevron {
    font-size: 10px;
    color: var(--text-secondary);
    flex-shrink: 0;
    width: 10px;
    text-align: center;
  }

  .daily-usage-loading {
    display: flex;
    justify-content: center;
    gap: 4px;
    padding: 8px 0;
  }

  .loading-dot {
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: var(--text-secondary);
    animation: pulse 1s ease-in-out infinite;
  }

  .loading-dot:nth-child(2) { animation-delay: 0.15s; }
  .loading-dot:nth-child(3) { animation-delay: 0.3s; }

  @keyframes pulse {
    0%, 100% { opacity: 0.3; }
    50% { opacity: 1; }
  }

  .daily-usage-body {
    padding: 0 10px 8px;
    display: flex;
    flex-direction: column;
    gap: 3px;
  }

  .model-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }

  .model-row:hover {
    background: var(--bg-hover);
  }

  .model-name {
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 90px;
    flex-shrink: 1;
  }

  .token-counts {
    display: flex;
    gap: 6px;
    flex-shrink: 0;
  }

  .token {
    font-size: 10px;
    font-family: var(--font-mono);
    white-space: nowrap;
  }

  .token.in {
    color: var(--blue);
  }

  .token.out {
    color: var(--purple);
  }

  .token.cache {
    color: var(--green);
  }

  .totals-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    padding: 3px 4px 0;
    margin-top: 2px;
    border-top: 1px solid var(--border);
  }

  .totals-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .cost-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
    padding: 3px 4px 0;
    margin-top: 2px;
  }

  .cost-label {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
  }

  .cost-value {
    font-size: 10px;
    font-family: var(--font-mono);
    color: var(--orange);
  }
</style>
