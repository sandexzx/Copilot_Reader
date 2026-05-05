<script lang="ts">
  import StatCard from './StatCard.svelte';
  import { eventsStore } from '$lib/stores/events.svelte';
  import { sessionsStore } from '$lib/stores/sessions.svelte';
  import { dailyUsageStore } from '$lib/stores/dailyUsage.svelte';

  let stats = $derived(eventsStore.stats);
  let loading = $derived(eventsStore.isLoading);

  let isActive = $derived(
    sessionsStore.sessions.find(s => s.id === sessionsStore.selectedSessionId)?.is_active ?? false
  );

  const TOKEN_HINT = 'Данные появятся после завершения сессии';
  const OUTPUT_RATE_LIMIT = 640_000;

  $effect(() => {
    dailyUsageStore.init();
  });

  let dailyOutputTokens = $derived(dailyUsageStore.data?.totals?.output_tokens ?? 0);

  function formatDuration(seconds: number): string {
    if (seconds < 60) return `${Math.round(seconds)}s`;
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return `${m}m ${s}s`;
  }

  let modelDisplay = $derived(
    stats?.models_used?.length ? stats.models_used[0] : '—'
  );

  interface BarItem {
    label: string;
    amount: number;
    color: string;
  }

  let nonOutputBars = $derived.by((): BarItem[] => {
    if (!stats) return [];
    return [
      { label: 'Input', amount: stats.input_tokens, color: 'var(--blue)' },
      { label: 'Cache Read', amount: stats.cache_read_tokens, color: 'var(--green)' },
      { label: 'Cache Write', amount: stats.cache_write_tokens, color: 'var(--orange)' },
    ];
  });

  let maxTokens = $derived(
    Math.max(...nonOutputBars.map(b => b.amount), 1)
  );

  let sessionOutputPct = $derived(
    Math.min(((stats?.output_tokens ?? 0) / OUTPUT_RATE_LIMIT) * 100, 100)
  );
  let dailyOutputPct = $derived(
    Math.min((dailyOutputTokens / OUTPUT_RATE_LIMIT) * 100, 100)
  );
  let dailyOutputRatio = $derived(dailyOutputTokens / OUTPUT_RATE_LIMIT);
  let outputWarning = $derived(dailyOutputRatio > 0.8);
</script>

{#if loading && !stats}
  <div class="skeleton-grid">
    {#each Array(8) as _}
      <div class="skeleton-card">
        <div class="skeleton-label"></div>
        <div class="skeleton-value"></div>
      </div>
    {/each}
  </div>
  <div class="skeleton-chart">
    <div class="skeleton-label" style="width: 120px; margin-bottom: 12px"></div>
    {#each Array(4) as _}
      <div class="skeleton-bar-row">
        <div class="skeleton-label" style="width: 80px"></div>
        <div class="skeleton-bar"></div>
        <div class="skeleton-label" style="width: 60px"></div>
      </div>
    {/each}
  </div>
{:else if !stats}
  <div class="stats-empty">Выберите сессию для просмотра статистики</div>
{:else}
    <div class="stat-grid">
      <StatCard label="Model" value={modelDisplay} color="accent" accentColor="var(--blue)" animate={false} index={0} />
      <StatCard label="Duration" value={formatDuration(stats.duration_seconds)} color="green" accentColor="var(--cyan)" animate={false} index={1} />
      <StatCard label="Tokens In" value={stats.input_tokens} color="green" accentColor="var(--blue)" index={2} hint={isActive ? TOKEN_HINT : undefined} />
      <StatCard label="Tokens Out" value={stats.output_tokens} color="green" accentColor="var(--purple)" index={3} hint={isActive ? TOKEN_HINT : undefined} />
      <StatCard label="Cache Read" value={stats.cache_read_tokens} color="green" accentColor="var(--green)" index={4} hint={isActive ? TOKEN_HINT : undefined} />
      <StatCard label="Tool Calls" value={stats.tool_calls} color="green" accentColor="var(--orange)" index={5} />
      <StatCard label="User Messages" value={stats.user_messages} color="green" accentColor="var(--green)" index={6} />
      <StatCard label="Assistant Turns" value={stats.assistant_turns} color="green" accentColor="var(--purple)" index={7} />
    </div>

    <div class="chart-section">
      <div class="chart-title">Token Usage by Category</div>
      <div class="bar-chart">
        {#each nonOutputBars as bar}
          <div class="bar-row">
            <span class="bar-label">{bar.label}</span>
            <div class="bar-track">
              <div
                class="bar-fill"
                style="width: {(bar.amount / maxTokens) * 100}%; background: {bar.color}"
              ></div>
            </div>
            <span class="bar-amount">{bar.amount.toLocaleString()}</span>
          </div>
        {/each}

        <!-- Output bar: dual-layer -->
        <div class="bar-row">
          <span class="bar-label">Output</span>
          <div class="bar-track" class:output-warning={outputWarning}>
            <div
              class="bar-fill bar-fill-daily"
              style="width: {dailyOutputPct}%"
            ></div>
            <div
              class="bar-fill bar-fill-session"
              style="width: {sessionOutputPct}%"
            ></div>
          </div>
          <span class="bar-amount">
            {(stats?.output_tokens ?? 0).toLocaleString()} / {dailyOutputTokens.toLocaleString()}
          </span>
        </div>
        <div class="output-legend">
          <span class="legend-item"><span class="legend-dot session-dot"></span> Session</span>
          <span class="legend-item"><span class="legend-dot daily-dot"></span> Today</span>
          <span class="legend-pct">{Math.round(dailyOutputRatio * 100)}% of 640K limit</span>
        </div>
      </div>
    </div>
{/if}

<style>
  .stats-empty {
    color: var(--text-secondary);
    font-size: 11px;
    text-align: center;
    padding: 20px 0;
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 8px;
    margin-bottom: 20px;
  }

  .chart-section {
    margin-top: 8px;
  }

  .chart-title {
    font-size: 10px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.8px;
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  }

  .bar-chart {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .bar-label {
    font-size: 11px;
    color: var(--text-secondary);
    width: 100px;
    text-align: right;
    font-family: var(--font-mono);
    flex-shrink: 0;
  }

  .bar-track {
    flex: 1;
    height: 16px;
    background: rgba(30, 30, 30, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 4px;
    overflow: hidden;
    position: relative;
  }

  .bar-fill {
    height: 100%;
    border-radius: 3px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.1);
    transition: width 1.5s cubic-bezier(0.22, 0.61, 0.36, 1);
  }

  .bar-amount {
    font-size: 10px;
    color: var(--text-secondary);
    min-width: 70px;
    font-family: var(--font-mono);
    flex-shrink: 0;
    white-space: nowrap;
  }

  /* Skeleton loading */
  .skeleton-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
  }

  .skeleton-card {
    background: var(--bg-main);
    border: 1px solid var(--border);
    border-radius: 8px;
    border-left: 3px solid var(--border);
    padding: 12px 14px;
  }

  .skeleton-label {
    height: 10px;
    width: 60px;
    background: linear-gradient(90deg, var(--bg-panel) 25%, var(--bg-input) 50%, var(--bg-panel) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 3px;
    margin-bottom: 8px;
  }

  .skeleton-value {
    height: 20px;
    width: 80px;
    background: linear-gradient(90deg, var(--bg-panel) 25%, var(--bg-input) 50%, var(--bg-panel) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 3px;
  }

  .skeleton-chart {
    margin-top: 8px;
  }

  .skeleton-bar-row {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 6px;
  }

  .skeleton-bar {
    flex: 1;
    height: 16px;
    background: linear-gradient(90deg, var(--bg-panel) 25%, var(--bg-input) 50%, var(--bg-panel) 75%);
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 3px;
  }

  @keyframes shimmer {
    0% { background-position: 200% 0; }
    100% { background-position: -200% 0; }
  }

  @media (prefers-reduced-motion: reduce) {
    .bar-fill {
      transition-duration: 0.01ms;
    }
  }

  /* Output bar dual-fill */
  .bar-fill-daily {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: rgba(197, 134, 192, 0.25);
    z-index: 1;
    border-radius: 3px;
  }

  .bar-fill-session {
    position: absolute;
    top: 0;
    left: 0;
    height: 100%;
    background: var(--purple);
    z-index: 2;
    border-radius: 3px;
  }

  .bar-track.output-warning {
    border-color: var(--orange);
  }

  .output-legend {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-left: 110px;
    margin-top: 2px;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 9px;
    color: var(--text-secondary);
    font-family: var(--font-mono);
  }

  .legend-dot {
    display: inline-block;
    width: 7px;
    height: 7px;
    border-radius: 50%;
  }

  .session-dot {
    background: var(--purple);
  }

  .daily-dot {
    background: rgba(197, 134, 192, 0.45);
  }

  .legend-pct {
    font-size: 9px;
    color: var(--text-secondary);
    font-family: var(--font-mono);
    margin-left: auto;
  }
</style>
