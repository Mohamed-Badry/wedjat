<section class="grid gap-10 lg:grid-cols-[1.4fr_0.9fr] lg:items-start">
  <div class="space-y-6">
    <div class="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-white/75 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand)] shadow-sm">
      Edge Telemetry Monitoring
    </div>

    <div class="space-y-5">
      <h1 class="max-w-3xl text-5xl font-semibold tracking-tight text-slate-950 sm:text-6xl">
        Real-time satellite health, built on the same core used for the offline lab.
      </h1>
      <p class="max-w-2xl text-lg leading-8 text-slate-700">
        This SvelteKit shell is wired for Bun, Tailwind, and the Docker stack behind Project Watchdog.
        It is ready to host live pass telemetry, replay-driven simulator output, and anomaly events from the FastAPI runtime.
      </p>
    </div>

    <div class="flex flex-wrap gap-3">
      <a
        class="rounded-full bg-[var(--color-brand)] px-5 py-3 text-sm font-semibold text-white shadow-lg shadow-[color:rgba(177,33,66,0.22)] transition hover:-translate-y-0.5"
        href="/dashboard"
      >
        Enter dashboard
      </a>
      <a
        class="rounded-full border border-[var(--color-border)] bg-white/80 px-5 py-3 text-sm font-semibold text-slate-800 transition hover:border-[var(--color-brand)] hover:text-[var(--color-brand)]"
        href="/team"
      >
        Meet the team
      </a>
    </div>
  </div>

  <aside class="grid gap-4">
    <div class="rounded-[2rem] border border-[var(--color-border)] bg-[var(--color-panel)] p-6 shadow-[var(--shadow-panel)] backdrop-blur">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-muted)]">Service topology</p>
      <ul class="mt-4 space-y-3 text-sm text-slate-700">
        <li class="flex items-center justify-between rounded-2xl bg-white/80 px-4 py-3">
          <span>MQTT broker</span>
          <span class="font-semibold text-emerald-600">Pinned</span>
        </li>
        <li class="flex items-center justify-between rounded-2xl bg-white/80 px-4 py-3">
          <span>FastAPI runtime</span>
          <span class="font-semibold text-emerald-600">Pinned</span>
        </li>
        <li class="flex items-center justify-between rounded-2xl bg-white/80 px-4 py-3">
          <span>SvelteKit frontend</span>
          <span class="font-semibold text-emerald-600">Bun + Tailwind</span>
        </li>
      </ul>
    </div>

    <div class="rounded-[2rem] border border-[var(--color-border)] bg-slate-950 p-6 text-slate-100 shadow-[var(--shadow-panel)]">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Why this matters</p>
      <p class="mt-4 text-sm leading-7 text-slate-300">
        The container layers now keep heavy installs stable. Torch is pinned to the same CPU build already locked in Pixi, and the frontend dependency mount no longer wipes out installed packages at runtime.
      </p>
    </div>
  </aside>
</section>
