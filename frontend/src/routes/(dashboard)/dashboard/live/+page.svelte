<script lang="ts">
  import { env } from '$env/dynamic/public';
  import type { PageData } from './$types';
  import { untrack } from 'svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let noradId = $state<string>('all');
  let limit = $state<number>(10);
  let isLive = $state<boolean>(true);

  let frames = $state<any[]>([]);
  let loading = $state(false);

  async function fetchRecent() {
    loading = true;
    const apiUrl = env.PUBLIC_API_URL || 'http://127.0.0.1:8000';
    let url = `${apiUrl}/api/telemetry/recent?limit=${limit}`;
    if (noradId !== 'all') {
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
    noradId; limit;
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

<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
    <div class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Real-Time Ingress</p>
      <h1 class="text-4xl font-semibold tracking-tight text-ink">Live Watcher</h1>
      <p class="max-w-3xl text-base leading-7 text-ink-2">
        Monitor live packet decodes, golden feature extraction, and real-time anomaly scores.
      </p>
    </div>
    
    <button 
      onclick={() => isLive = !isLive}
      class="mt-2 flex items-center gap-2 rounded-full border px-4 py-2.5 text-sm font-semibold transition-all hover:scale-105 {isLive ? 'border-emerald-500/50 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]' : 'border-border bg-surface text-ink-3 hover:border-brand hover:text-brand'}"
    >
      <span class="relative flex h-2.5 w-2.5">
        {#if isLive}
          <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
        {/if}
        <span class="relative inline-flex h-2.5 w-2.5 rounded-full {isLive ? 'bg-emerald-500' : 'bg-ink-3'}"></span>
      </span>
      {isLive ? 'Live Sync Active' : 'Paused'}
    </button>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <div class="flex flex-wrap items-end gap-6 rounded-[1.5rem] border border-border bg-panel p-6 shadow-panel backdrop-blur">
      <div class="flex flex-col gap-2">
        <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Satellite Filter</label>
        <select bind:value={noradId} class="rounded-xl border border-border bg-surface px-4 py-2 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
          <option value="all">All Satellites</option>
          {#each satellites as sat}
            <option value={sat.norad_id.toString()}>{sat.name} ({sat.norad_id})</option>
          {/each}
        </select>
      </div>

      <div class="flex flex-col gap-2">
        <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Feed Size</label>
        <select bind:value={limit} class="rounded-xl border border-border bg-surface px-4 py-2 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
          <option value={10}>Last 10 Frames</option>
          <option value={25}>Last 25 Frames</option>
          <option value={50}>Last 50 Frames</option>
        </select>
      </div>
    </div>

    <!-- Feed -->
    <div class="space-y-4">
      {#if loading && frames.length === 0}
        <div class="flex h-40 items-center justify-center">
          <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
        </div>
      {:else if frames.length === 0}
        <div class="rounded-[1.5rem] border border-border border-dashed p-12 text-center text-ink-3">
          <p>No frames received yet for the selected filter.</p>
        </div>
      {:else}
        {#each frames as frame (frame.timestamp + frame.norad_id)}
          <article class="group relative flex flex-col gap-4 overflow-hidden rounded-[1.5rem] border border-border bg-panel p-6 shadow-panel backdrop-blur transition-all hover:-translate-y-1 hover:border-brand/30 hover:shadow-lg lg:flex-row lg:items-center lg:justify-between">
            {#if frame.model?.is_anomaly}
              <div class="absolute inset-y-0 left-0 w-1.5 bg-brand shadow-[0_0_8px_rgba(177,33,66,0.8)]"></div>
            {:else}
              <div class="absolute inset-y-0 left-0 w-1 bg-emerald-500/50"></div>
            {/if}

            <div class="flex items-center gap-5 pl-2">
              <div class="flex h-12 w-12 shrink-0 flex-col items-center justify-center rounded-full border border-border bg-surface text-center">
                <span class="text-[0.65rem] font-bold tracking-widest text-brand">ID</span>
                <span class="text-xs font-medium text-ink">{frame.norad_id}</span>
              </div>
              <div>
                <p class="font-medium tracking-tight text-ink">{new Date(frame.timestamp).toLocaleString()}</p>
                <div class="mt-1 flex items-center gap-3 text-xs text-ink-3">
                  <span>Source: {frame.source || 'MQTT'}</span>
                  {#if frame.quality?.frame_is_complete}
                    <span class="flex items-center gap-1 text-emerald-600 dark:text-emerald-400"><span class="h-1.5 w-1.5 rounded-full bg-emerald-500"></span> Complete</span>
                  {:else}
                    <span class="flex items-center gap-1 text-brand"><span class="h-1.5 w-1.5 rounded-full bg-brand"></span> Partial</span>
                  {/if}
                </div>
              </div>
            </div>

            <div class="flex flex-wrap items-center gap-6 rounded-xl bg-surface/50 p-4 lg:p-0 lg:bg-transparent lg:border-none lg:flex-nowrap">
              {#if frame.features}
                {@const fKeys = Object.keys(frame.features).slice(0, 3)}
                <div class="hidden gap-6 md:flex">
                  {#each fKeys as key}
                    <div class="flex flex-col">
                      <span class="text-[0.65rem] font-semibold uppercase tracking-wider text-ink-3">{key.replace(/_/g, ' ')}</span>
                      <span class="font-mono text-sm text-ink">{frame.features[key] !== null ? Number(frame.features[key]).toFixed(2) : '-'}</span>
                    </div>
                  {/each}
                </div>
              {/if}

              <div class="ml-auto flex items-center gap-4 border-l border-border pl-6">
                <div class="flex flex-col text-right">
                  <span class="text-[0.65rem] font-semibold uppercase tracking-wider text-ink-3">Anomaly Score</span>
                  <span class="text-xl font-bold tracking-tight {frame.model?.is_anomaly ? 'text-brand' : 'text-ink'}">{frame.model?.anomaly_score !== null ? frame.model.anomaly_score.toFixed(2) : 'N/A'}</span>
                </div>
                {#if frame.model?.threshold}
                  <div class="flex h-10 w-10 flex-col items-center justify-center rounded-lg border border-border bg-surface" title="Threshold: {frame.model.threshold.toFixed(2)}">
                    <span class="text-[0.6rem] font-bold text-ink-3">THR</span>
                    <span class="text-xs text-ink-2">{frame.model.threshold.toFixed(1)}</span>
                  </div>
                {/if}
              </div>
            </div>
          </article>
        {/each}
      {/if}
    </div>
  {/if}
</section>
