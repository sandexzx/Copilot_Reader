<script lang="ts">
  import StatsPanel from './StatsPanel.svelte';
  import EventTree from './EventTree.svelte';

  interface Props {
    sessionId?: string | null;
  }

  let { sessionId = null }: Props = $props();

  const tabs = ['Statistics', 'Tree View', 'Raw JSON'];
  let activeTab = $state('Statistics');
</script>

<div class="detail-panel">
  <div class="tab-bar">
    {#each tabs as tab}
      <button
        class="tab"
        class:active={activeTab === tab}
        onclick={() => activeTab = tab}
      >
        {tab}
      </button>
    {/each}
  </div>
  <div class="tab-content">
    {#if activeTab === 'Statistics'}
      <div class="tab-pane">
        <StatsPanel {sessionId} />
      </div>
    {:else if activeTab === 'Tree View'}
      <div class="tab-pane">
        <EventTree {sessionId} />
      </div>
    {:else if activeTab === 'Raw JSON'}
      <div class="tab-pane">
        <div class="json-empty">No raw data available</div>
      </div>
    {/if}
  </div>
</div>

<style>
  .detail-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .tab-bar {
    height: 32px;
    min-height: 32px;
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: stretch;
  }

  .tab {
    padding: 0 16px;
    font-size: 12px;
    color: var(--text-secondary);
    cursor: pointer;
    display: flex;
    align-items: center;
    border: none;
    border-bottom: 2px solid transparent;
    background: none;
    font-family: var(--font-sans);
    transition: color 0.15s;
  }

  .tab:hover {
    color: var(--text-primary);
  }

  .tab.active {
    color: var(--text-primary);
    border-bottom-color: var(--border-active);
  }

  .tab-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
  }

  .tab-pane {
    display: block;
  }

  .json-empty {
    color: var(--text-secondary);
    font-size: 11px;
    text-align: center;
    padding: 20px 0;
  }
</style>
