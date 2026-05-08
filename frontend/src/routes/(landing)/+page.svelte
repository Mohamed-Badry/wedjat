<section class="grid gap-10 lg:grid-cols-[1.4fr_0.9fr] lg:items-start">
  <div class="space-y-6">
    <div class="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-brand shadow-sm">
      Edge Telemetry Monitoring
    </div>

    <div class="space-y-5">
      <h1 class="max-w-3xl text-5xl font-semibold tracking-tight text-ink sm:text-6xl">
        Real-time satellite health, built on the same core used for the offline lab.
      </h1>
      <p class="max-w-2xl text-lg leading-8 text-ink-2">
        This SvelteKit shell is wired for Bun, Tailwind, and the Docker stack behind Project Watchdog.
        It is ready to host live pass telemetry, replay-driven simulator output, and anomaly events from the FastAPI runtime.
      </p>
    </div>

    <div class="flex flex-wrap gap-3">
      <a
        class="rounded-full bg-brand px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-brand/22 transition hover:-translate-y-0.5"
        href="/dashboard"
      >
        Enter dashboard
      </a>
      <a
        class="rounded-full border border-border bg-surface px-5 py-3 text-sm font-semibold text-ink transition hover:border-brand hover:text-brand"
        href="/team"
      >
        Meet the team
      </a>
    </div>
  </div>

  <aside class="grid gap-4">
    <div class="rounded-[2rem] border border-border bg-panel p-6 shadow-panel backdrop-blur">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Service topology</p>
      <ul class="mt-4 space-y-3 text-sm text-ink-2">
        <li class="flex items-center justify-between rounded-2xl bg-surface px-4 py-3">
          <span>MQTT broker</span>
          <span class="font-semibold text-ok">Pinned</span>
        </li>
        <li class="flex items-center justify-between rounded-2xl bg-surface px-4 py-3">
          <span>FastAPI runtime</span>
          <span class="font-semibold text-ok">Pinned</span>
        </li>
        <li class="flex items-center justify-between rounded-2xl bg-surface px-4 py-3">
          <span>SvelteKit frontend</span>
          <span class="font-semibold text-ok">Bun + Tailwind</span>
        </li>
      </ul>
    </div>

    <div class="rounded-[2rem] border border-border bg-accent-bg p-6 text-accent-ink shadow-panel">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-accent-ink-2">Why this matters</p>
      <p class="mt-4 text-sm leading-7 text-accent-ink">
        The container layers now keep heavy installs stable. Torch is pinned to the same CPU build already locked in Pixi, and the frontend dependency mount no longer wipes out installed packages at runtime.
      </p>
    </div>
  </aside>
</section>
