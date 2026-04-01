<script lang="ts">
  import type { Event } from '$lib/types';
  import EventRow from './EventRow.svelte';

  let { events = [] as Event[] } = $props();

  const HIDDEN_TYPES = new Set(['assistant.turn_start', 'assistant.turn_end']);
  const HIDDEN_TOOLS = new Set(['read_agent']);
  let visibleEvents = $derived(events.filter(e => {
    if (HIDDEN_TYPES.has(e.type)) return false;
    const toolName = (e.data?.toolName ?? e.data?.tool_name ?? e.tool_name ?? '') as string;
    if (HIDDEN_TOOLS.has(toolName)) return false;
    return true;
  }));

  let scrollContainer: HTMLDivElement | undefined = $state(undefined);
  let autoScroll = $state(true);
  let hasNewEvents = $state(false);
  let prevEventCount = $state(0);
  let prevFirstEventId = $state<string | null>(null);

  function handleScroll() {
    if (!scrollContainer) return;
    const { scrollTop, clientHeight, scrollHeight } = scrollContainer;
    const atBottom = scrollTop + clientHeight >= scrollHeight - 50;
    autoScroll = atBottom;
    if (atBottom) hasNewEvents = false;
  }

  function scrollToBottom() {
    if (!scrollContainer) return;
    scrollContainer.scrollTo({ top: scrollContainer.scrollHeight, behavior: 'smooth' });
    autoScroll = true;
    hasNewEvents = false;
  }

  function pauseAutoScroll() {
    autoScroll = false;
  }

  $effect(() => {
    const count = visibleEvents.length;
    const firstId = visibleEvents.length > 0 ? visibleEvents[0].id : null;
    const isNewSession = firstId !== prevFirstEventId && firstId !== null;

    if (isNewSession) {
      // New session loaded — scroll to bottom
      autoScroll = true;
      hasNewEvents = false;
      requestAnimationFrame(() => {
        scrollContainer?.scrollTo({ top: scrollContainer.scrollHeight });
      });
    } else if (count > prevEventCount && prevEventCount > 0) {
      if (autoScroll && scrollContainer) {
        requestAnimationFrame(() => {
          scrollContainer?.scrollTo({ top: scrollContainer.scrollHeight });
        });
      } else if (!autoScroll) {
        hasNewEvents = true;
      }
    }
    prevEventCount = count;
    prevFirstEventId = firstId;
  });
</script>

<div class="event-panel">
  <div class="event-panel-header">
    <span class="title">Event Stream</span>
    <span class="event-count">{visibleEvents.length}</span>
    <span class="auto-scroll-indicator">
      {autoScroll ? 'Auto-scroll ✓' : 'Auto-scroll paused'}
    </span>
  </div>
  <div
    class="event-stream"
    bind:this={scrollContainer}
    onscroll={handleScroll}
  >
    {#if visibleEvents.length === 0}
      <div class="event-stream-empty">
        Ожидаем первые события… Данные появятся автоматически.
      </div>
    {:else}
      {#each visibleEvents as event (event.id)}
        <EventRow {event} onexpand={pauseAutoScroll} />
      {/each}
    {/if}
  </div>
  {#if hasNewEvents && !autoScroll}
    <button class="scroll-to-bottom" onclick={scrollToBottom}>
      ↓ New events
    </button>
  {/if}
</div>

<style>
  .event-panel {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    border-bottom: 1px solid var(--border);
    position: relative;
  }

  .event-panel-header {
    height: 28px;
    min-height: 28px;
    background: var(--bg-panel);
    border-bottom: 1px solid var(--border);
    display: flex;
    align-items: center;
    padding: 0 12px;
    font-size: 11px;
    color: var(--text-secondary);
    gap: 8px;
  }

  .event-panel-header .title {
    font-weight: 600;
    color: var(--text-primary);
  }

  .event-count {
    background: var(--bg-input);
    padding: 1px 6px;
    border-radius: 8px;
    font-size: 10px;
  }

  .auto-scroll-indicator {
    margin-left: auto;
    font-size: 10px;
  }

  .event-stream {
    flex: 1;
    overflow-y: auto;
    font-family: var(--font-mono);
    font-size: 12px;
  }

  .event-stream-empty {
    padding: 20px 12px;
    color: var(--text-secondary);
    font-size: 11px;
    text-align: center;
    font-family: var(--font-sans);
  }

  .scroll-to-bottom {
    position: absolute;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--border-active);
    color: var(--text-bright);
    border: none;
    border-radius: 12px;
    padding: 4px 14px;
    font-size: 11px;
    font-family: var(--font-sans);
    cursor: pointer;
    box-shadow: var(--shadow-md);
    z-index: 10;
    transition: opacity 0.2s;
  }

  .scroll-to-bottom:hover {
    opacity: 0.9;
  }
</style>
