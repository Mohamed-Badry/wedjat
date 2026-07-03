<script lang="ts">
  import type { PageData } from "./$types";
  import { untrack } from "svelte";
  import { fly } from "svelte/transition";
  import { flip } from "svelte/animate";
  import { apiFetch, getWsUrl } from "$lib/api";
  import type { TelemetryFrame } from "$lib/types/api";

  import AnomalyTimelinePlot from "$lib/components/charts/AnomalyTimelinePlot.svelte";
  import Select from "$lib/components/ui/Select.svelte";

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  import { uiState } from '$lib/stores/ui-state.svelte';

  let noradId = $state<string>(uiState.live.noradId);
  let limit = $state<number>(uiState.live.limit);
  let isLive = $state<boolean>(uiState.live.isLive);

  let frames = $state<TelemetryFrame[]>(uiState.live.frames);

  $effect(() => {
    uiState.live.noradId = noradId;
    uiState.live.limit = limit;
    uiState.live.isLive = isLive;
    uiState.live.frames = frames;
  });
  let loading = $state(false);
  let selectedTimestamp = $state<string | null>(null);

  async function fetchRecent() {
    loading = true;
    let path = `/api/telemetry/recent?limit=${limit}`;
    if (noradId !== "all") {
      path += `&norad_id=${noradId}`;
    }
    try {
      const data = await apiFetch<any>(path);
      // Deduplicate frames to prevent Svelte each_key_duplicate crash
      const seen = new Set();
      const framesList = Array.isArray(data) ? data : (data.frames || []);
      const uniqueFrames = framesList.filter((f: any) => {
        const k = f.timestamp + '_' + f.norad_id;
        if (seen.has(k)) return false;
        seen.add(k);
        return true;
      });
      frames = uniqueFrames;
    } catch (e) {
      console.error("Failed to fetch recent telemetry", e);
    } finally {
      loading = false;
    }
  }

  // Effect to re-fetch when parameters change
  $effect(() => {
    // Initial data fetch when filters change
    noradId;
    limit;
    untrack(() => fetchRecent());
  });

  // Effect to manage WebSocket connection
  $effect(() => {
    if (!isLive) return;

    // Read synchronously so Svelte tracks dependencies
    const currentNoradId = noradId;

    const wsUrl = `${getWsUrl()}/api/ws/dashboard`;
    let ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      // Send initial subscription
      const payload = {
        action: "subscribe",
        norad_id: currentNoradId === "all" ? null : parseInt(currentNoradId)
      };
      ws.send(JSON.stringify(payload));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "push_telemetry") {
          // Check for duplicate before prepending
          const isDuplicate = frames.some(f => f.timestamp === data.frame.timestamp && f.norad_id === data.frame.norad_id);
          if (!isDuplicate) {
            frames = [data.frame, ...frames].slice(0, limit);
          }
        } else if (data.type === "push_anomaly_alert") {
          // If we receive an anomaly alert, we find the existing frame and update it
          // Or if it's a new frame, prepend it
          const existingIdx = frames.findIndex(f => f.timestamp === data.alert.timestamp && f.norad_id === data.alert.norad_id);
          if (existingIdx !== -1) {
            // Update existing frame's model metadata
            frames[existingIdx] = {
              ...frames[existingIdx],
              model: {
                ...frames[existingIdx].model,
                anomaly_score: data.alert.score,
                is_anomaly: true
              }
            };
          } else {
            // Insert it as a new frame if we don't have the telemetry base
            frames = [data.alert, ...frames].slice(0, limit);
          }
        }
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  });
</script>

<svelte:head>
  <title>Live Watcher — Watchdog</title>
</svelte:head>

<section class="flex lg:h-full lg:min-h-0 flex-col gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <!-- 1. HEADER: Title & Global Controls -->
  <header class="flex flex-none flex-wrap items-center justify-between gap-4">
    <div class="space-y-1">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Real-Time Ingress</p>
      <h1 class="text-3xl font-semibold tracking-tight text-ink">Live Watcher</h1>
    </div>

    <div class="relative z-20 flex flex-wrap items-center gap-4">
      <!-- Satellite Filter -->
      <div class="flex items-center gap-2">
        <label for="live-sat-select" class="text-xs font-semibold uppercase tracking-wider text-ink-3">Sat Filter</label>
        <Select
          id="live-sat-select"
          bind:value={noradId}
          options={[{ value: 'all', label: 'All' }, ...satellites.map(s => ({ value: s.norad_id.toString(), label: s.norad_id.toString() }))]}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-1.5 min-w-[100px] outline-none transition hover:border-brand focus:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <!-- Feed Limit -->
      <div class="flex items-center gap-2">
        <label for="live-feed-size" class="text-xs font-semibold uppercase tracking-wider text-ink-3">Limit</label>
        <Select
          id="live-feed-size"
          bind:value={limit}
          options={[{ value: 25, label: '25' }, { value: 50, label: '50' }, { value: 100, label: '100' }, { value: 250, label: '250' }, { value: 500, label: '500' }, { value: 1000, label: '1000' }]}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-1.5 min-w-[80px] outline-none transition hover:border-brand focus:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <!-- Live Sync Toggle -->
      <button
        onclick={() => (isLive = !isLive)}
        class="flex items-center gap-2 rounded-lg border px-4 py-2 text-sm font-semibold transition-all hover:scale-105 {isLive
          ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-sm shadow-emerald-500/10'
          : 'border-border bg-surface text-ink-3 hover:border-brand hover:text-brand'}"
      >
        <span class="relative flex h-2 w-2">
          {#if isLive}
            <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
          {/if}
          <span class="relative inline-flex h-2 w-2 rounded-full {isLive ? 'bg-emerald-500' : 'bg-ink-3'}"></span>
        </span>
        {isLive ? "Sync Active" : "Paused"}
      </button>
    </div>
  </header>

  <!-- 2. MAIN CONTENT: Error, Feed, or Placeholder -->
  {#if error}
    <div class="flex-none rounded-xl border border-brand/50 bg-brand/10 p-4 text-sm text-brand">
      {error}
    </div>
  {:else}
    <!-- TELEMETRY FEED (Scrollable Area) -->
    <div class="flex lg:min-h-0 lg:flex-1 flex-col rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur">
      <div class="shrink-0 border-b border-border bg-surface/35 p-3">
        <h2 class="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-3">Telemetry Feed</h2>
      </div>

      <div class="lg:flex-1 lg:min-h-0 overflow-y-auto max-h-[400px] lg:max-h-none p-4">
        {#if loading && frames.length === 0}
          <div class="flex h-full items-center justify-center py-12">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-surface border-t-brand"></div>
          </div>
        {:else if frames.length === 0}
          <div class="rounded-lg border border-border border-dashed p-12 text-center text-sm text-ink-3">
            No telemetry packets received for the current filter.
          </div>
        {:else}
          <div class="grid grid-cols-1 gap-5 xl:grid-cols-2">
            {#each frames as frame, i (frame.timestamp + String(frame.norad_id))}
              <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_noninteractive_element_interactions -->
              <article 
                animate:flip={{ duration: 400 }}
                in:fly={{ y: -10, opacity: 0, duration: 400, delay: Math.min(i * 50, 400) }}
                class="group relative flex flex-col gap-2 overflow-hidden rounded-xl border p-4 transition-all hover:border-brand/40 hover:bg-surface/80 cursor-pointer {selectedTimestamp === frame.timestamp ? 'border-brand bg-brand/15 ring-2 ring-brand/50 shadow-[0_0_20px_rgba(139,92,246,0.2)]' : 'border-border bg-surface/40 hover:shadow-sm'}"
                onclick={(e) => {
                  e.stopPropagation();
                  e.preventDefault();
                  if (selectedTimestamp === frame.timestamp) {
                    selectedTimestamp = null;
                  } else {
                    selectedTimestamp = frame.timestamp;
                  }
                }}
              >
                <!-- Status Indicator Bar -->
                <div class="absolute inset-y-0 left-0 w-1 transition-all duration-300 {frame.model?.is_anomaly ? 'bg-critical shadow-[0_0_12px_rgba(244,63,94,1)]' : 'bg-emerald-500/40 group-hover:bg-emerald-500/80'}"></div>

                <!-- Card Header: NORAD, Quality, Timestamp, Score -->
                <div class="flex items-start justify-between gap-3 pl-2">
                  <div class="space-y-1.5">
                    <div class="flex items-center gap-2">
                      <span class="rounded border border-border bg-panel px-2 py-1 font-mono text-xs font-bold text-ink-3 shadow-sm">NORAD {frame.norad_id}</span>
                      <span class="text-[11px] font-bold tracking-wide uppercase {frame.quality?.frame_is_complete ? 'text-emerald-500/80' : 'text-warning/90'}">
                        {frame.quality?.frame_is_complete ? "Complete" : "Partial"}
                      </span>
                    </div>
                    <p class="font-medium text-sm text-ink-2 group-hover:text-ink transition-colors">{new Date(frame.timestamp).toLocaleTimeString()}</p>
                  </div>

                  <div class="text-right">
                    <p class="text-[10px] font-bold uppercase tracking-widest text-ink-3/70 mb-0.5">Anomaly Score</p>
                    <p class="text-2xl font-black tracking-tighter {frame.model?.is_anomaly ? 'text-critical drop-shadow-[0_0_8px_rgba(244,63,94,0.4)]' : 'text-ink'}">
                      {frame.model?.anomaly_score != null ? frame.model.anomaly_score.toFixed(2) : "-"}
                    </p>
                  </div>
                </div>

                <!-- Feature Grid (Top 4) -->
                {#if frame.features}
                  {@const fKeys = Object.keys(frame.features).slice(0, 4)}
                  <div class="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3 border-t border-border/40 pl-2 pt-3">
                    {#each fKeys as key}
                      <div class="flex flex-col min-w-0">
                        <span class="truncate text-[9px] font-bold uppercase tracking-widest text-ink-3/60" title={key}>{key.replace(/_/g, " ")}</span>
                        <span class="font-mono text-sm font-medium text-ink/80 group-hover:text-ink transition-colors">
                          {frame.features[key] !== null ? Number(frame.features[key]).toFixed(2) : "-"}
                        </span>
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

    <!-- ANOMALY TIMELINE (Pinned to Bottom) -->
    {#if frames.length > 0}
      {@const timelineFrames = frames
        .filter((f) => f.model?.anomaly_score != null)
        .map((f) => ({
          timestamp: f.timestamp,
          anomaly_score: f.model.anomaly_score!,
          is_anomaly: f.model.is_anomaly,
        }))}
      
      {#if timelineFrames.length > 0}
        <div class="flex-none chart-card overflow-hidden">
          <p class="chart-card-title text-[11px] mb-2">Anomaly Score History</p>
          <div class="h-48 pb-2">
            <AnomalyTimelinePlot
              frames={timelineFrames}
              threshold={frames[0]?.model?.threshold ?? 0.3}
              {selectedTimestamp}
            />
          </div>
        </div>
      {/if}
    {/if}
  {/if}
</section>
