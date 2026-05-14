<script lang="ts">
  import { page } from "$app/stores";
  import AntennaBackground from "$lib/components/AntennaBackground.svelte";
  import { themeState, toggleTheme } from "$lib/theme.svelte";
  import { Sun, Moon } from "lucide-svelte";

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

  // Keep spatial geometry identical across themes to prevent density shifts
  const antennaMaxDist = 350;
  const antennaBeamWidth = 130;
  const antennaSignalFadeScale = 1.5;
  const antennaBaseFadeScale = 1.2;
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
            class="ml-2 flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface text-ink-3 shadow-sm transition-all hover:scale-105 hover:border-brand hover:text-brand"
            title="Toggle theme"
            aria-label="Toggle theme"
          >
            {#if themeState.isLight}
              <Moon class="size-4" />
            {:else}
              <Sun class="size-4" />
            {/if}
          </button>
        </nav>
      </div>
    </header>

    <main class="flex-1">
      {@render children()}
    </main>
  </div>
</div>
