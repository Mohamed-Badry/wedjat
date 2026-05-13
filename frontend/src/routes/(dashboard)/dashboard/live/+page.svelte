<script lang="ts">
  import { env } from "$env/dynamic/public";
  import type { PageData } from "./$types";
  import { untrack } from "svelte";

  import AnomalyTimelinePlot from "$lib/components/charts/AnomalyTimelinePlot.svelte";

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let noradId = $state<string>("all");
  let limit = $state<number>(25);
  let isLive = $state<boolean>(true);

  let frames = $state<any[]>([]);
  let loading = $state(false);

  async function fetchRecent() {
    loading = true;
    const apiUrl =
      typeof window !== "undefined"
        ? env.PUBLIC_API_URL || "http://127.0.0.1:8000"
        : "http://backend:8000";
    let url = `${apiUrl}/api/telemetry/recent?limit=${limit}`;
    if (noradId !== "all") {
      url += `&norad_id=${noradId}`;
    }
    try {
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        frames = data.frames || [];
      }
    } catch (e) {
      console.error("Failed to fetch recent telemetry", e);
    } finally {
      loading = false;
    }
  }

  // Effect to re-fetch when parameters change
  $effect(() => {
    // Track parameters
    noradId;
    limit;
    untrack(() => fetchRecent());
  });

  // Effect to handle live polling
  $effect(() => {
    if (!isLive) return;
    const interval = setInterval(() => {
      untrack(() => fetchRecent());
    }, 5000);
    return () => clearInterval(interval);
  });
</script>

<section
  class="flex flex-col h-full min-h-0 gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out"
>
  <div class="flex-none flex flex-wrap items-center justify-between gap-4">
    <div class="space-y-1">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
        Real-Time Ingress
      </p>
      <h1 class="text-3xl font-semibold tracking-tight text-ink">
        Live Watcher
      </h1>
    </div>

    <div class="flex items-center gap-4">
      <div class="flex items-center gap-2">
        <label
          for="live-sat-select"
          class="text-xs font-semibold uppercase tracking-wider text-ink-3"
          >Sat Filter</label
        >
        <select
          id="live-sat-select"
          bind:value={noradId}
          class="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand"
        >
          <option value="all">All</option>
          {#each satellites as sat}
            <option value={sat.norad_id.toString()}>{sat.norad_id}</option>
          {/each}
        </select>
      </div>

      <div class="flex items-center gap-2">
        <label
          for="live-feed-size"
          class="text-xs font-semibold uppercase tracking-wider text-ink-3"
          >Limit</label
        >
        <select
          id="live-feed-size"
          bind:value={limit}
          class="rounded-lg border border-border bg-surface px-3 py-1.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand"
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
        </select>
      </div>

      <button
        onclick={() => (isLive = !isLive)}
        class="flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all {isLive
          ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-sm shadow-emerald-500/10'
          : 'border-border bg-surface text-ink-3 hover:border-brand hover:text-brand'}"
      >
        <span class="relative flex h-1.5 w-1.5">
          {#if isLive}
            <span
              class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"
            ></span>
          {/if}
          <span
            class="relative inline-flex h-1.5 w-1.5 rounded-full {isLive
              ? 'bg-emerald-500'
              : 'bg-ink-3'}"
          ></span>
        </span>
        {isLive ? "Sync Active" : "Paused"}
      </button>
    </div>
  </div>

  {#if error}
    <div
      class="flex-none rounded-xl border border-brand/50 bg-brand/10 p-4 text-sm text-brand"
    >
      {error}
    </div>
    <!-- Bottom: Anomaly Score Timeline -->
  {:else}
    {#if frames.length > 0}
      {@const timelineFrames = frames
        .filter((f: any) => f.model?.anomaly_score != null)
        .map((f: any) => ({
          timestamp: f.timestamp,
          anomaly_score: f.model.anomaly_score,
          is_anomaly: f.model.is_anomaly,
        }))}
      {#if timelineFrames.length > 0}
        <div class="flex-none chart-card">
          <p class="chart-card-title text-[11px] mb-2">
            Anomaly Score Timeline
          </p>
          <div class="h-48 pb-2">
            <AnomalyTimelinePlot
              frames={timelineFrames}
              threshold={frames[0]?.model?.threshold ?? 0.3}
            />
          </div>
        </div>
      {/if}
    {/if}
    <!-- Top: Feed (Scrollable) -->
    <div
      class="flex flex-col flex-1 min-h-0 rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur"
    >
      <div class="bg-surface/35 p-3 shrink-0 border-b border-border">
        <h2
          class="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-3"
        >
          Telemetry Feed
        </h2>
      </div>

      <div class="flex-1 min-h-0 overflow-y-auto p-4 space-y-3">
        {#if loading && frames.length === 0}
          <div class="flex h-full items-center justify-center">
            <div
              class="h-6 w-6 animate-spin rounded-full border-2 border-surface border-t-brand"
            ></div>
          </div>
        {:else if frames.length === 0}
          <div
            class="rounded-lg border border-border border-dashed p-6 text-center text-xs text-ink-3"
          >
            No frames received yet.
          </div>
        {:else}
          <div class="grid grid-cols-1 xl:grid-cols-2 gap-5">
            {#each frames as frame (frame.timestamp + frame.norad_id)}
              <article
                class="relative flex flex-col gap-2 overflow-hidden rounded-lg border border-border bg-surface/50 p-3 transition-all hover:border-brand/30"
              >
                {#if frame.model?.is_anomaly}
                  <div
                    class="absolute inset-y-0 left-0 w-1 bg-brand shadow-[0_0_8px_rgba(177,33,66,0.8)]"
                  ></div>
                {:else}
                  <div
                    class="absolute inset-y-0 left-0 w-1 bg-emerald-500/50"
                  ></div>
                {/if}

                <div class="flex items-start justify-between gap-3 pl-2">
                  <div>
                    <div class="flex items-center gap-2">
                      <span
                        class="rounded bg-panel px-2 py-1 font-mono text-xs font-bold text-ink-3 border border-border"
                        >NORAD {frame.norad_id}</span
                      >
                      {#if frame.quality?.frame_is_complete}
                        <span class="text-xs text-emerald-500 font-medium"
                          >Complete</span
                        >
                      {:else}
                        <span class="text-xs text-brand font-medium"
                          >Partial</span
                        >
                      {/if}
                    </div>
                    <p class="mt-2 font-medium text-base text-ink">
                      {new Date(frame.timestamp).toLocaleTimeString()}
                    </p>
                  </div>

                  <div class="flex flex-col text-right">
                    <span
                      class="text-xs font-semibold uppercase tracking-wider text-ink-3"
                      >Score</span
                    >
                    <span
                      class="text-2xl font-bold tracking-tight {frame.model
                        ?.is_anomaly
                        ? 'text-brand'
                        : 'text-ink'}"
                    >
                      {frame.model?.anomaly_score !== null
                        ? frame.model.anomaly_score.toFixed(2)
                        : "-"}
                    </span>
                  </div>
                </div>

                {#if frame.features}
                  {@const fKeys = Object.keys(frame.features).slice(0, 4)}
                  <div
                    class="grid grid-cols-4 gap-3 pl-2 border-t border-border/50 pt-3 mt-2"
                  >
                    {#each fKeys as key}
                      <div class="flex flex-col">
                        <span
                          class="text-xs font-semibold uppercase tracking-wider text-ink-3 truncate"
                          title={key}>{key.replace(/_/g, " ")}</span
                        >
                        <span class="font-mono text-base text-ink"
                          >{frame.features[key] !== null
                            ? Number(frame.features[key]).toFixed(2)
                            : "-"}</span
                        >
                      </div>
                    {/each}
                  </div>
                {/if}
              </article>
            {/each}
          </div>
        {/if}
      </div>
    </div>
  {/if}
</section>
