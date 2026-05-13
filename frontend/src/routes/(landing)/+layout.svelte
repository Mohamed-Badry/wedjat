<script lang="ts">
  import { page } from "$app/stores";
  import AntennaBackground from "$lib/components/AntennaBackground.svelte";
  import { themeState, toggleTheme } from "$lib/theme.svelte";

  let { children } = $props();

  const nav = [
    { href: "/", label: "Overview" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/team", label: "Team" },
  ];

  // ── Antenna Theme Configuration ───────────────────────────────────────────
  let antennaColorOff = $derived(themeState.isLight ? "#a0b0c0" : "#1c2a3e");
  let antennaColorOn = $derived(themeState.isLight ? "#3a5068" : "#7eb8da");
  let antennaBeamColor = $derived(themeState.isLight ? "#8a1833" : "#B12142");

  let antennaMaxDist = $derived(themeState.isLight ? 375 : 300);
  let antennaBeamWidth = $derived(themeState.isLight ? 125 : 150);
  let antennaSignalFadeScale = $derived(themeState.isLight ? 2.0 : 1.0);
  let antennaBaseFadeScale = $derived(themeState.isLight ? 1.8 : 1.0);
</script>

<AntennaBackground
  lightMode={themeState.isLight}
  colorOff={antennaColorOff}
  colorOn={antennaColorOn}
  beamColor={antennaBeamColor}
  maxDist={antennaMaxDist}
  beamWidth={antennaBeamWidth}
  signalFadeScale={antennaSignalFadeScale}
  antennaFadeScale={antennaBaseFadeScale}
/>

<div class="min-h-screen">
  <div class="mx-auto flex min-h-screen w-full max-w-[1800px] flex-col px-6 py-6 sm:px-8 lg:px-10">
    <header class="mb-10 rounded-[2rem] border border-border bg-panel px-5 py-4 shadow-panel backdrop-blur sm:px-6">
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <a class="text-lg font-semibold tracking-[0.18em] text-muted uppercase" href="/">
            Project Watchdog
          </a>
          <p class="mt-1 max-w-xl text-sm text-ink-3">
            A low-latency operator shell for live telemetry, anomaly scoring,
            and replay-driven validation.
          </p>
        </div>

        <nav class="flex flex-wrap items-center gap-2 text-sm font-medium">
          {#each nav as item}
            <a
              class="rounded-full border border-border px-4 py-2 text-ink-2 transition hover:border-brand hover:bg-surface hover:text-brand"
              href={item.href}
            >
              {item.label}
            </a>
          {/each}

          <button
            onclick={toggleTheme}
            class="ml-1 rounded-full border border-border px-3 py-2 text-xs text-ink-3 transition hover:border-brand hover:text-brand"
            title="Toggle light / dark mode"
          >
            {themeState.isLight ? "☽" : "☀"}
          </button>
        </nav>
      </div>
    </header>

    <main class="flex-1">
      {@render children()}
    </main>
  </div>
</div>
