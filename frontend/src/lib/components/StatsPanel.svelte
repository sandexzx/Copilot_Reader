<script lang="ts">
  import StatCard from './StatCard.svelte';
  import { fetchSessionStats } from '$lib/api';
  import type { SessionStats } from '$lib/types';

  interface Props {
    sessionId: string | null;
  }

  let { sessionId }: Props = $props();

  let stats = $state<SessionStats | null>(null);
  let loading = $state(false);
  let error = $state<string | null>(null);
  let animKey = $state(0);

  $effect(() => {
    if (!sessionId) {
      stats = null;
      loading = false;
      error = null;
      return;
    }

    const id = sessionId;
    let cancelled = false;

    loading = true;
    error = null;
    stats = null;

    fetchSessionStats(id).then((result) => {
      if (cancelled) return;
      stats = result;
      animKey++;
      loading = false;
    }).catch((e) => {
      if (cancelled) return;
      error = e instanceof Error ? e.message : 'Failed to load stats';
      loading = false;
    });

    return () => {
      cancelled = true;
    };
  });

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

  let bars = $derived.by((): BarItem[] => {
    if (!stats) return [];
    return [
      { label: 'Input', amount: stats.input_tokens, color: 'var(--blue)' },
      { label: 'Output', amount: stats.output_tokens, color: 'var(--purple)' },
      { label: 'Cache Read', amount: stats.cache_read_tokens, color: 'var(--green)' },
      { label: 'Cache Write', amount: stats.cache_write_tokens, color: 'var(--orange)' },
    ];
  });

  let maxTokens = $derived(
    Math.max(...bars.map(b => b.amount), 1)
  );

  let mounted = $state(false);

  $effect(() => {
    if (stats) {
      // Trigger bar animation after a tick
      mounted = false;
      requestAnimationFrame(() => { mounted = true; });
    }
  });
</script>

{#if !sessionId}
  <div class="stats-empty">Select a session to view statistics</div>
{:else if loading}
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
{:else if error}
  <div class="stats-error">{error}</div>
{:else if stats}
  {#key animKey}
    <div class="stat-grid">
      <StatCard label="Model" value={modelDisplay} color="accent" accentColor="var(--blue)" animate={false} />
      <StatCard label="Duration" value={formatDuration(stats.duration_seconds)} color="green" accentColor="var(--cyan)" animate={false} />
      <StatCard label="Tokens In" value={stats.input_tokens} color="green" accentColor="var(--blue)" />
      <StatCard label="Tokens Out" value={stats.output_tokens} color="green" accentColor="var(--purple)" />
      <StatCard label="Cache Read" value={stats.cache_read_tokens} color="green" accentColor="var(--green)" />
      <StatCard label="Tool Calls" value={stats.tool_calls} color="green" accentColor="var(--orange)" />
      <StatCard label="User Messages" value={stats.user_messages} color="green" accentColor="var(--green)" />
      <StatCard label="Assistant Turns" value={stats.assistant_turns} color="green" accentColor="var(--purple)" />
    </div>

    <div class="chart-section">
      <div class="chart-title">Token Usage by Category</div>
      <div class="bar-chart">
        {#each bars as bar}
          <div class="bar-row">
            <span class="bar-label">{bar.label}</span>
            <div class="bar-track">
              <div
                class="bar-fill"
                style="width: {mounted ? (bar.amount / maxTokens) * 100 : 0}%; background: {bar.color}"
              ></div>
            </div>
            <span class="bar-amount">{bar.amount.toLocaleString()}</span>
          </div>
        {/each}
      </div>
    </div>
  {/key}
{/if}

<style>
  .stats-empty,
  .stats-error {
    color: var(--text-secondary);
    font-size: 11px;
    text-align: center;
    padding: 20px 0;
  }

  .stats-error {
    color: var(--red);
  }

  .stat-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
  }

  .chart-section {
    margin-top: 8px;
  }

  .chart-title {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.6px;
    margin-bottom: 10px;
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
    background: var(--bg-main);
    border-radius: 3px;
    overflow: hidden;
    position: relative;
  }

  .bar-fill {
    height: 100%;
    border-radius: 3px;
    transition: width 1.5s cubic-bezier(0.22, 0.61, 0.36, 1);
  }

  .bar-amount {
    font-size: 10px;
    color: var(--text-secondary);
    width: 70px;
    font-family: var(--font-mono);
    flex-shrink: 0;
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
</style>
