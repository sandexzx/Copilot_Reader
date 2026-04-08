<script lang="ts">
  import { dailyUsageStore } from '$lib/stores/dailyUsage.svelte';

  let expanded = $state(true);

  // Pricing per 1M tokens (USD)
  const MODEL_PRICING: Record<string, { input: number; output: number }> = {
    'claude-opus-4.6': { input: 5, output: 25 },
  };
  const USD_TO_RUB = 81.25;
  const OUTPUT_RATE_LIMIT = 320_000;

  let data = $derived(dailyUsageStore.data);
  let loading = $derived(dailyUsageStore.loading);

  let dailyOutputTokens = $derived(data?.totals?.output_tokens ?? 0);
  let dailyOutputRatio = $derived(dailyOutputTokens / OUTPUT_RATE_LIMIT);
  let dailyOutputPct = $derived(Math.min(dailyOutputRatio * 100, 100));
  let rateLimitColor = $derived(
    dailyOutputRatio > 0.95 ? 'var(--red)' :
    dailyOutputRatio > 0.8 ? 'var(--orange)' :
    dailyOutputRatio > 0.5 ? 'var(--color-warning)' :
    'var(--green)'
  );
  let rateLimitWarning = $derived(dailyOutputRatio > 0.8);

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
        <div class="rate-limit-section">
          <div class="rate-limit-labels">
            <span class="rate-limit-title">Output Limit</span>
            <span class="rate-limit-value" style="color: {rateLimitColor}">
              {Math.round(dailyOutputPct)}% · {formatTokens(dailyOutputTokens)} / 320K
            </span>
          </div>
          <div class="rate-limit-track" class:rate-warning={rateLimitWarning}>
            <div
              class="rate-limit-fill"
              class:rate-warning-fill={rateLimitWarning}
              style="width: {dailyOutputPct}%; background: {rateLimitColor}"
            ></div>
          </div>
        </div>
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

  .rate-limit-section {
    margin-top: 6px;
    padding: 5px 4px 0;
    border-top: 1px solid var(--border);
  }

  .rate-limit-labels {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 4px;
  }

  .rate-limit-title {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .rate-limit-value {
    font-size: 10px;
    font-family: var(--font-mono);
    font-weight: 600;
  }

  .rate-limit-track {
    width: 100%;
    height: 6px;
    background: rgba(30, 30, 30, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 3px;
    overflow: hidden;
    position: relative;
  }

  .rate-limit-track.rate-warning {
    border-color: var(--orange);
  }

  .rate-limit-fill {
    height: 100%;
    border-radius: 2px;
    transition: width 1s ease, background 0.5s ease;
    min-width: 1px;
  }

  .rate-limit-fill.rate-warning-fill {
    box-shadow: 0 0 6px rgba(206, 145, 120, 0.5);
    animation: rate-glow 2s ease-in-out infinite;
  }

  @keyframes rate-glow {
    0%, 100% {
      box-shadow: 0 0 4px rgba(206, 145, 120, 0.3);
    }
    50% {
      box-shadow: 0 0 8px rgba(206, 145, 120, 0.7);
    }
  }
</style>
