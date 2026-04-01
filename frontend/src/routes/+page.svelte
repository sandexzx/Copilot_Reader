<script>
  import Sidebar from '$lib/components/Sidebar.svelte';
  import Header from '$lib/components/Header.svelte';
  import EventPanel from '$lib/components/EventPanel.svelte';
  import ResizeHandle from '$lib/components/ResizeHandle.svelte';
  import DetailPanel from '$lib/components/DetailPanel.svelte';
  import { sessionsStore } from '$lib/stores/sessions.svelte';
  import { eventsStore } from '$lib/stores/events.svelte';
  import { websocketStore } from '$lib/stores/websocket.svelte';

  let contentEl = $state(null);
  let eventPanelFlex = $state(6);
  let detailPanelFlex = $state(4);

  /** @type {ReturnType<typeof setInterval> | undefined} */
  let pollInterval;

  // Load sessions on mount + start polling
  $effect(() => {
    sessionsStore.loadSessions();
    pollInterval = setInterval(() => {
      sessionsStore.loadSessions(true);
    }, 10_000);
    return () => {
      clearInterval(pollInterval);
      websocketStore.disconnect();
    };
  });

  // Auto-select the most recent session on first load
  let initialAutoSelect = $state(true);
  $effect(() => {
    if (initialAutoSelect && sessionsStore.sessions.length > 0 && !sessionsStore.selectedSessionId) {
      initialAutoSelect = false;
      const latest = sessionsStore.sessions[0];
      handleSessionSelect(latest);
    }
  });

  // Derived state for header
  let selectedSession = $derived(
    sessionsStore.sessions.find(s => s.id === sessionsStore.selectedSessionId) ?? null
  );

  async function handleSessionSelect(session) {
    sessionsStore.selectSession(session.id);
    websocketStore.disconnect();
    await eventsStore.loadEvents(session.id);
    if (session.is_active) {
      websocketStore.connect(session.id);
    }
  }

  function handleResize(deltaY) {
    if (!contentEl) return;
    const totalHeight = contentEl.clientHeight;
    if (totalHeight === 0) return;

    const totalFlex = eventPanelFlex + detailPanelFlex;
    const flexPerPx = totalFlex / totalHeight;
    const deltaFlex = deltaY * flexPerPx;

    let newEventFlex = eventPanelFlex + deltaFlex;
    let newDetailFlex = detailPanelFlex - deltaFlex;

    // Clamp: min 1.5 flex for either panel (~15%)
    if (newEventFlex < 1.5) { newEventFlex = 1.5; newDetailFlex = totalFlex - 1.5; }
    if (newDetailFlex < 1.5) { newDetailFlex = 1.5; newEventFlex = totalFlex - 1.5; }

    eventPanelFlex = newEventFlex;
    detailPanelFlex = newDetailFlex;
  }
</script>

<Sidebar onselect={handleSessionSelect} />

<main class="main">
  <Header
    sessionId={selectedSession?.id ?? ''}
    isConnected={websocketStore.isConnected}
    isActive={selectedSession?.is_active ?? false}
  />

  <div class="content" bind:this={contentEl}>
    <div class="event-panel-wrapper" style="flex: {eventPanelFlex}">
      <EventPanel events={eventsStore.events} />
    </div>

    <ResizeHandle onresize={handleResize} />

    <div class="detail-panel-wrapper" style="flex: {detailPanelFlex}">
      <DetailPanel />
    </div>
  </div>
</main>

<style>
  .main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-width: 0;
  }

  .content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .event-panel-wrapper {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .detail-panel-wrapper {
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
</style>
