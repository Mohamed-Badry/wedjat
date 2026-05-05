<script lang="ts">
  const cards = [
    {
      title: 'Live telemetry stream',
      detail: 'MQTT ingress, decoded golden features, and the current pass timeline.'
    },
    {
      title: 'Anomaly queue',
      detail: 'Persisted scores, threshold crossings, and structured explanations per frame.'
    },
    {
      title: 'Replay controls',
      detail: 'Historical simulator runs routed through the same broker and backend path.'
    },
    {
      title: 'Model health',
      detail: 'Artifact version, inference mode, and runtime state transitions.'
    }
  ];
</script>

<section class="space-y-8">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-muted)]">Dashboard shell</p>
    <h1 class="text-4xl font-semibold tracking-tight text-slate-950">Operational monitoring surface</h1>
    <p class="max-w-3xl text-base leading-7 text-slate-700">
      This route is scaffolded and ready for the live WebSocket and REST plumbing. The layout matches the intended operator view without pretending the backend features are already implemented.
    </p>
  </div>

  <div class="grid gap-4 md:grid-cols-2">
    {#each cards as card}
      <article class="rounded-[1.75rem] border border-[var(--color-border)] bg-[var(--color-panel)] p-6 shadow-[var(--shadow-panel)] backdrop-blur">
        <p class="text-sm font-semibold text-[var(--color-brand)]">{card.title}</p>
        <p class="mt-3 text-sm leading-7 text-slate-700">{card.detail}</p>
      </article>
    {/each}
  </div>
</section>
