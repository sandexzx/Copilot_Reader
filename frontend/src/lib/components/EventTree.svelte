<script lang="ts">
  import { eventsStore } from '$lib/stores/events.svelte';
  import TreeNodeItem from './TreeNode.svelte';

  let treeData = $derived(eventsStore.tree);
  let loading = $derived(eventsStore.isLoading);
</script>

{#if loading && treeData.length === 0}
  <div class="tree-status">Загрузка дерева…</div>
{:else if treeData.length === 0}
  <div class="tree-status">Данные появятся автоматически</div>
{:else}
  <div class="tree">
    {#each treeData as node (node.event.id)}
      <TreeNodeItem {node} depth={0} />
    {/each}
  </div>
{/if}

<style>
  .tree {
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .tree-status {
    color: var(--text-secondary);
    font-size: 11px;
    text-align: center;
    padding: 20px 0;
  }
</style>
