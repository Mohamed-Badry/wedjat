<script lang="ts">
  const roles = [
    'Telemetry ingestion and decoder integration',
    'Model training, thresholding, and artifact management',
    'Frontend operations dashboard and service integration'
  ];
</script>

<section class="space-y-8">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-muted)]">About the project</p>
    <h1 class="text-4xl font-semibold tracking-tight text-slate-950">A compact academic project shell</h1>
    <p class="max-w-3xl text-base leading-7 text-slate-700">
      This page is intentionally lightweight. It gives the web app a real route structure now, while leaving room for final team bios, faculty credits, and institutional branding later.
    </p>
  </div>

  <div class="rounded-[2rem] border border-[var(--color-border)] bg-[var(--color-panel)] p-6 shadow-[var(--shadow-panel)] backdrop-blur">
    <p class="text-sm font-semibold text-[var(--color-brand)]">Current workstreams</p>
    <ul class="mt-4 space-y-3 text-sm leading-7 text-slate-700">
      {#each roles as role}
        <li class="rounded-2xl bg-white/80 px-4 py-3">{role}</li>
      {/each}
    </ul>
  </div>
</section>
