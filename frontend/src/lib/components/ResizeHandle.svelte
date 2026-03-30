<script>
  let { onresize = () => {} } = $props();

  let dragging = $state(false);
  let startY = 0;

  function onMouseDown(e) {
    dragging = true;
    startY = e.clientY;
    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    document.body.style.cursor = 'ns-resize';
    document.body.style.userSelect = 'none';
  }

  function onMouseMove(e) {
    if (!dragging) return;
    const deltaY = e.clientY - startY;
    startY = e.clientY;
    onresize(deltaY);
  }

  function onMouseUp() {
    dragging = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="resize-handle"
  class:active={dragging}
  onmousedown={onMouseDown}
></div>

<style>
  .resize-handle {
    height: 3px;
    background: transparent;
    cursor: ns-resize;
    position: relative;
    flex-shrink: 0;
  }

  .resize-handle:hover,
  .resize-handle.active {
    background: var(--border-active);
  }
</style>
