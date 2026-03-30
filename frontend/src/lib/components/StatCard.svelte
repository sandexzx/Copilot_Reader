<script lang="ts">
  interface Props {
    label: string;
    value: string | number;
    color?: 'accent' | 'green' | 'default';
    accentColor?: string;
    animate?: boolean;
  }

  let {
    label,
    value,
    color,
    accentColor,
    animate,
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

  let valueClass = $derived(
    color === 'accent' ? 'stat-value accent' :
    color === 'green' ? 'stat-value green' :
    'stat-value'
  );
</script>

<div
  class="stat-card"
  class:mounted
  style="--accent-line: {accentColor ?? 'var(--border-active)'}; --value-accent: {accentColor ?? 'var(--text-accent)'}"
>
  <div class="stat-label">{label}</div>
  <div class={valueClass}>{formattedValue}</div>
</div>

<style>
  .stat-card {
    position: relative;
    overflow: hidden;
    background:
      linear-gradient(180deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0) 100%),
      linear-gradient(135deg, rgba(86, 156, 214, 0.08) 0%, rgba(45, 45, 45, 0.96) 48%, rgba(30, 30, 30, 1) 100%);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px 14px 12px 16px;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
    opacity: 0;
    transform: translateY(6px);
    transition: opacity 0.3s ease, transform 0.3s ease;
  }

  .stat-card::before {
    content: '';
    position: absolute;
    inset: 0 auto 0 0;
    width: 2px;
    background: var(--accent-line, var(--border-active));
  }

  .stat-card.mounted {
    opacity: 1;
    transform: translateY(0);
  }

  .stat-label {
    font-size: 10px;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: var(--text-secondary);
    margin-bottom: 4px;
  }

  .stat-value {
    font-size: 20px;
    font-weight: 600;
    line-height: 1.2;
    font-family: var(--font-mono);
    color: var(--text-primary);
  }

  .stat-value.accent {
    color: var(--value-accent);
  }

  .stat-value.green {
    color: var(--green-bright);
  }
</style>
