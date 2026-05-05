<script lang="ts">
  import '../app.css';

  let { children } = $props();

  const nav = [
    { href: '/', label: 'Overview' },
    { href: '/dashboard', label: 'Dashboard' },
    { href: '/team', label: 'Team' }
  ];
</script>

<svelte:head>
  <title>Project Watchdog</title>
  <meta
    name="description"
    content="Project Watchdog is a Bun-powered SvelteKit interface for real-time amateur satellite telemetry monitoring."
  />
</svelte:head>

<div class="min-h-screen">
  <div class="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-6 sm:px-8 lg:px-10">
    <header class="mb-10 rounded-[2rem] border border-[var(--color-border)] bg-[var(--color-panel)] px-5 py-4 shadow-[var(--shadow-panel)] backdrop-blur sm:px-6">
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <a class="text-lg font-semibold tracking-[0.18em] text-[var(--color-muted)] uppercase" href="/">
            Project Watchdog
          </a>
          <p class="mt-1 max-w-xl text-sm text-slate-600">
            A low-latency operator shell for live telemetry, anomaly scoring, and replay-driven validation.
          </p>
        </div>

        <nav class="flex flex-wrap gap-2 text-sm font-medium">
          {#each nav as item}
            <a
              class="rounded-full border border-[var(--color-border)] px-4 py-2 text-slate-700 transition hover:border-[var(--color-brand)] hover:bg-white/80 hover:text-[var(--color-brand)]"
              href={item.href}
            >
              {item.label}
            </a>
          {/each}
        </nav>
      </div>
    </header>

    <main class="flex-1">
      {@render children()}
    </main>
  </div>
</div>
