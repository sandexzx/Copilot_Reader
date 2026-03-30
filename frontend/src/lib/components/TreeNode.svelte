<script lang="ts">
  import type { TreeNode } from '$lib/types';
  import TreeNodeItem from './TreeNode.svelte';

  let { node, depth = 0 }: { node: TreeNode; depth?: number } = $props();

  // svelte-ignore state_referenced_locally — depth is fixed per instance
  let expanded = $state(depth <= 2);

  const hasChildren = $derived(node.children.length > 0);

  function toggle() {
    if (hasChildren) expanded = !expanded;
  }

  function getString(data: Record<string, unknown>, ...keys: string[]): string | null {
    for (const key of keys) {
      const value = data[key];
      if (typeof value === 'string' && value.trim()) {
        return value.trim();
      }
    }
    return null;
  }

  function getIcon(treeNode: TreeNode): string {
    if (treeNode.status === 'failed') return '❌';
    if (treeNode.status === 'completed') return '✅';

    if (treeNode.semantic_kind === 'session') return '📁';
    if (treeNode.semantic_kind === 'turn') return '🔷';
    if (treeNode.semantic_kind === 'user') return '💬';
    if (treeNode.semantic_kind === 'assistant') return '🤖';
    if (treeNode.semantic_kind === 'tool') return '🔧';
    if (treeNode.semantic_kind === 'subagent') return '🔧';
    return '📄';
  }

  function getAccentText(treeNode: TreeNode): string | null {
    if (treeNode.semantic_kind === 'tool') {
      return treeNode.event.tool_name ?? getString(treeNode.event.data, 'toolName', 'tool_name');
    }

    if (treeNode.semantic_kind === 'subagent') {
      return treeNode.agent_name ?? getString(treeNode.event.data, 'agentName', 'agent_name', 'agentDisplayName');
    }

    return null;
  }

  function getAccentClass(treeNode: TreeNode): string {
    if (treeNode.semantic_kind === 'tool') return 'tool';
    if (treeNode.semantic_kind === 'subagent') return 'subagent';
    return '';
  }

  function getMetadata(treeNode: TreeNode): string {
    const parts: string[] = [];

    if (treeNode.event_count > 1) {
      parts.push(`${treeNode.event_count} events`);
    }

    if (treeNode.duration_ms != null) {
      parts.push(formatDuration(treeNode.duration_ms));
    }

    if (treeNode.semantic_kind === 'subagent' && treeNode.status) {
      parts.push(treeNode.status);
    }

    if (treeNode.brief_description) {
      parts.push(treeNode.brief_description);
    }

    return parts.join(' | ');
  }

  function formatDuration(ms: number): string {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    const min = Math.floor(ms / 60000);
    const sec = Math.floor((ms % 60000) / 1000);
    return `${min}m ${sec}s`;
  }
</script>

<div class="tree-node">
  <div class="tree-row">
    {#if hasChildren}
      <button
        type="button"
        class="tree-toggle tree-toggle-button"
        aria-label={expanded ? 'Collapse node' : 'Expand node'}
        onclick={toggle}
      >
        {expanded ? '▼' : '▶'}
      </button>
    {:else}
      <span class="tree-toggle tree-toggle-spacer"></span>
    {/if}

    <span class="tree-icon">{getIcon(node)}</span>

    <div class="tree-main">
      <span class="tree-type">{node.event.type}</span>
      {#if getAccentText(node)}
        <span class={`tree-accent ${getAccentClass(node)}`}>
          {getAccentText(node)}
        </span>
      {/if}
    </div>

    {#if getMetadata(node)}
      <span class="tree-meta">
        {getMetadata(node)}
      </span>
    {/if}
  </div>

  {#if hasChildren}
    <div class="tree-children" class:collapsed={!expanded}>
      {#each node.children as child (child.event.id)}
        <TreeNodeItem node={child} depth={depth + 1} />
      {/each}
    </div>
  {/if}
</div>

<style>
  .tree-node {
    padding: 2px 0;
  }

  .tree-row {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    border-radius: 3px;
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .tree-row:hover {
    background: var(--bg-hover);
  }

  .tree-toggle {
    width: 16px;
    color: var(--text-secondary);
    font-size: 10px;
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    user-select: none;
  }

  .tree-toggle-button {
    border: none;
    background: transparent;
    padding: 0;
    cursor: pointer;
    font: inherit;
    color: inherit;
  }

  .tree-toggle-spacer {
    min-height: 16px;
  }

  .tree-icon {
    flex-shrink: 0;
    font-size: 11px;
  }

  .tree-main {
    display: flex;
    align-items: center;
    gap: 4px;
    min-width: 0;
  }

  .tree-type {
    color: var(--text-primary);
  }

  .tree-accent.tool {
    color: var(--orange);
  }

  .tree-accent.subagent {
    color: var(--cyan);
  }

  .tree-meta {
    color: var(--text-secondary);
    margin-left: auto;
    font-size: 10px;
    white-space: nowrap;
  }

  .tree-children {
    padding-left: 16px;
  }

  .tree-children.collapsed {
    display: none;
  }
</style>
