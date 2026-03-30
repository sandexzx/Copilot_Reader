<script lang="ts">
  import type { TreeNode } from '$lib/types';
  import { fetchSessionTree } from '$lib/api';
  import TreeNodeItem from './TreeNode.svelte';

  let { sessionId = null }: { sessionId?: string | null } = $props();

  let treeData = $state<TreeNode[]>([]);
  let loading = $state(false);
  let error = $state<string | null>(null);

  $effect(() => {
    if (!sessionId) {
      treeData = [];
      error = null;
      loading = false;
      return;
    }
    const id = sessionId;
    let aborted = false;
    loading = true;
    error = null;
    fetchSessionTree(id)
      .then((data) => {
        if (!aborted) {
          treeData = data;
          loading = false;
        }
      })
      .catch((e) => {
        if (!aborted) {
          error = e instanceof Error ? e.message : 'Failed to load tree';
          loading = false;
        }
      });
    return () => {
      aborted = true;
    };
  });
</script>

{#if loading}
  <div class="tree-status">Loading tree…</div>
{:else if error}
  <div class="tree-status tree-error">{error}</div>
{:else if treeData.length === 0}
  <div class="tree-status">No session data to display</div>
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

  .tree-error {
    color: var(--color-error);
  }
</style>
