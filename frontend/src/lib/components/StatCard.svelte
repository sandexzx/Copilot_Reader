<script lang="ts">
  interface Props {
    label: string;
    value: string | number;
    color?: 'accent' | 'green' | 'default';
    accentColor?: string;
    animate?: boolean;
    index?: number;
    hint?: string;
  }

  let {
    label,
    value,
    color,
    accentColor,
    animate,
    index = 0,
    hint,
  }: Props = $props();

  let displayValue = $state<string | number>(0);
  let mounted = $state(false);

  $effect(() => {
    mounted = true;
    const val = value;
    const shouldAnimate = animate ?? true;

    if (typeof val !== 'number' || !shouldAnimate) {
      displayValue = val;
      return;
    }

    const target = val;
    if (target === 0) {
      displayValue = 0;
      return;
    }

    const duration = 1200;
    const startTime = performance.now();
    let frame = 0;

    displayValue = 0;

    function easeOutCubic(t: number): number {
      return 1 - Math.pow(1 - t, 3);
    }

    function tick(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = easeOutCubic(progress);
      displayValue = Math.round(eased * target);
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    }

    frame = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(frame);
    };
  });

  let formattedValue = $derived(
    typeof displayValue === 'number'
      ? displayValue.toLocaleString()
      : displayValue
  );

  let showHint = $derived(hint && value === 0);

  let valueClass = $derived(
    color === 'accent' ? 'stat-value accent' :
    color === 'green' ? 'stat-value green' :
    'stat-value'
  );
</script>

<div
  class="stat-card"
  class:mounted
  style="--accent-line: {accentColor ?? 'var(--border-active)'}; --value-accent: {accentColor ?? 'var(--text-accent)'}; --gradient-tint: {`color-mix(in srgb, ${accentColor ?? 'var(--border-active)'} 8%, transparent)`}; --stagger: {index}"
>
  <div class="stat-label">{label}</div>
  <div class={valueClass}>{formattedValue}</div>
  {#if showHint}
    <div class="stat-hint">ℹ {hint}</div>
  {/if}
</div>

<style>
  .stat-card {
    position: relative;
    overflow: hidden;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0) 100%),
      linear-gradient(135deg, var(--gradient-tint, rgba(86, 156, 214, 0.08)) 0%, rgba(45, 45, 45, 0.96) 48%, rgba(30, 30, 30, 1) 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 14px 14px 14px 16px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04);
    opacity: 0;
    transform: translateY(6px);
    transition: opacity 0.35s ease-out, transform 0.35s ease-out, border-color 0.15s ease, box-shadow 0.15s ease;
    transition-delay: calc(var(--stagger, 0) * 60ms);
  }

  .stat-card::before {
    content: '';
    position: absolute;
    top: 6px;
    bottom: 6px;
    left: 0;
    width: 3px;
    border-radius: 0 2px 2px 0;
    background: var(--accent-line, var(--border-active));
  }

  .stat-card:hover {
    border-color: var(--border-light);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05), 0 2px 8px rgba(0, 0, 0, 0.15);
  }

  .stat-card.mounted {
    opacity: 1;
    transform: translateY(0);
  }

  .stat-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: var(--text-secondary);
    margin-bottom: 6px;
  }

  .stat-value {
    font-size: 22px;
    font-weight: 700;
    line-height: 1.1;
    font-family: var(--font-mono);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.02em;
    color: var(--text-primary);
  }

  .stat-value.accent {
    color: var(--value-accent);
  }

  .stat-value.green {
    color: var(--green-bright);
  }

  .stat-hint {
    font-size: 9px;
    color: var(--text-secondary);
    margin-top: 4px;
    line-height: 1.3;
    opacity: 0.7;
  }

  @media (prefers-reduced-motion: reduce) {
    .stat-card {
      transition-duration: 0.01ms;
      transition-delay: 0ms;
    }
  }
</style>
