<script lang="ts">
  import { page } from "$app/stores";
  import AntennaBackground from "$lib/components/AntennaBackground.svelte";
  import ScrollIndicator from "$lib/components/ScrollIndicator.svelte";
  import { themeState, toggleTheme } from "$lib/theme.svelte";
  import { Sun, Moon } from "lucide-svelte";
  import { fly } from "svelte/transition";
  import { backOut } from "svelte/easing";

  let { children } = $props();

  const nav = [
    { href: "/", label: "Overview" },
    { href: "/dashboard", label: "Dashboard" },
    { href: "/team", label: "Team" },
  ];

  // ── Antenna Theme Configuration ───────────────────────────────────────────
  let antennaColorOff = $derived(themeState.isLight ? "#a0b0c0" : "#1c2a3e");
  let antennaColorOn = $derived(themeState.isLight ? "#3a5068" : "#7eb8da");
  let antennaBeamColor = $derived(themeState.isLight ? "#7c3aed" : "#8b5cf6");
  let antennaMaxDist = $derived(themeState.isLight ? 350 : 400);
  let antennaSignalFadeScale = $derived(themeState.isLight ? 1.3 : 1.7);
  let antennaBaseFadeScale = $derived(themeState.isLight ? 1.0 : 1.5);

  // Keep spatial geometry identical across themes to prevent density shifts
  // const antennaMaxDist = 350;
  const antennaBeamWidth = 130;
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

<ScrollIndicator />

<div class="min-h-screen">
  <div class="flex min-h-screen w-full flex-col">
    <div class="mx-auto w-full max-w-[1800px] px-4 pt-4 sm:px-8 sm:pt-6 lg:px-10">
      <header in:fly={{ y: -20, duration: 800, delay: 200, easing: backOut }} class="mb-10 rounded-[2rem] border border-border bg-panel px-5 py-4 shadow-panel backdrop-blur sm:px-6">
      <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <a class="flex items-center gap-3 text-xl font-semibold tracking-[0.18em] text-muted uppercase hover:text-brand transition-colors" href="/">
            <img src="/favicon.svg" alt="Project Wedjat Logo" class="size-8" />
            Project Wedjat
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
    </div>

    <main class="flex-1 w-full flex flex-col">
      {@render children()}
    </main>
  </div>
</div>
