<script lang="ts">
  import { env } from '$env/dynamic/public';
  import type { PageData } from './$types';
  import { untrack } from 'svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let noradId = $state<string>('all');
  let bucket = $state<'hour' | 'day'>('day');
  let limit = $state<number>(14);

  let loading = $state(false);
  let chartData = $state<any>(null);

  async function fetchThroughput() {
    loading = true;
    const apiUrl = env.PUBLIC_API_URL || 'http://127.0.0.1:8000';
    let url = `${apiUrl}/api/telemetry/throughput?bucket=${bucket}&limit=${limit}`;
    if (noradId !== 'all') {
      url += `&norad_id=${noradId}`;
    }
    try {
      const res = await fetch(url);
      if (res.ok) {
        chartData = await res.json();
      } else {
        console.error("Failed to fetch throughput");
      }
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  // Use an effect to auto-fetch when dependencies change
  $effect(() => {
    // Read reactive parameters synchronously
    const _b = bucket;
    
    // Auto-correct bounds based on bucket
    if (bucket === 'hour' && ![12, 24, 48, 72].includes(limit)) {
      limit = 24;
    } else if (bucket === 'day' && ![7, 14, 30, 60].includes(limit)) {
      limit = 14;
    }
    
    const _l = limit;
    const _n = noradId;
    
    // Untrack fetch so it doesn't loop if it reads reactive state inside
    untrack(() => {
      fetchThroughput();
      fetchScatter();
    });
  });

  let scatterData = $state<any>(null);
  let loadingScatter = $state(false);

  async function fetchScatter() {
    loadingScatter = true;
    const apiUrl = env.PUBLIC_API_URL || 'http://127.0.0.1:8000';
    let url = `${apiUrl}/api/telemetry/recent?limit=250`;
    if (noradId !== 'all') {
      url += `&norad_id=${noradId}`;
    }
    try {
      const res = await fetch(url);
      if (res.ok) {
        scatterData = await res.json();
      } else {
        console.error("Failed to fetch scatter data");
      }
    } catch (e) {
      console.error(e);
    } finally {
      loadingScatter = false;
    }
  }

  // Calculate maximum total frames for chart scaling
  let maxFrames = $derived(chartData?.buckets?.length ? Math.max(...chartData.buckets.map((b: any) => b.frame_count)) : 0);
</script>

<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Analytics</p>
    <h1 class="text-4xl font-semibold tracking-tight text-ink">EDA & Insights</h1>
    <p class="max-w-3xl text-base leading-7 text-ink-2">
      Interactive telemetry explorer. Analyze throughput, missing frame density, and anomaly clusters over time.
    </p>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <div class="rounded-[1.75rem] border border-border bg-panel p-6 shadow-panel backdrop-blur lg:p-8">
      <!-- Controls -->
      <div class="mb-8 flex flex-wrap items-end gap-6 border-b border-border pb-6">
        <div class="flex flex-col gap-2">
          <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Satellite</label>
          <select bind:value={noradId} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
            <option value="all">All Satellites</option>
            {#each satellites as sat}
              <option value={sat.norad_id.toString()}>{sat.name} ({sat.norad_id})</option>
            {/each}
          </select>
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Resolution</label>
          <select bind:value={bucket} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
            <option value="day">Daily</option>
            <option value="hour">Hourly</option>
          </select>
        </div>

        <div class="flex flex-col gap-2">
          <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Lookback Period</label>
          <select bind:value={limit} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
            {#if bucket === 'day'}
              <option value={7}>7 Days</option>
              <option value={14}>14 Days</option>
              <option value={30}>30 Days</option>
              <option value={60}>60 Days</option>
            {:else}
              <option value={12}>12 Hours</option>
              <option value={24}>24 Hours</option>
              <option value={48}>48 Hours</option>
              <option value={72}>72 Hours</option>
            {/if}
          </select>
        </div>
      </div>

      <!-- Chart Area -->
      <div class="relative h-[400px] w-full">
        {#if loading && !chartData}
          <div class="absolute inset-0 flex items-center justify-center">
            <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
          </div>
        {:else if chartData?.buckets?.length === 0}
          <div class="absolute inset-0 flex flex-col items-center justify-center text-ink-3">
             <p>No telemetry data found for the selected parameters.</p>
          </div>
        {:else if chartData && maxFrames > 0}
          <div class="flex h-full w-full items-end gap-1">
            {#each chartData.buckets as b}
              <!-- svelte-ignore a11y_interactive_supports_focus -->
              <div 
                class="group relative flex h-full flex-1 flex-col justify-end"
                role="group"
              >
                <!-- Anomaly Stack (Top) -->
                {#if b.anomaly_count > 0}
                   <div 
                     class="w-full bg-brand rounded-t-sm opacity-90 transition-all group-hover:opacity-100" 
                     style="height: {(b.anomaly_count / maxFrames) * 100}%"
                   ></div>
                {/if}
                <!-- Normal Stack (Bottom) -->
                {#if (b.frame_count - b.anomaly_count) > 0}
                  <div 
                    class="w-full bg-ink-3 {b.anomaly_count === 0 ? 'rounded-t-sm' : ''} opacity-40 transition-all group-hover:bg-brand group-hover:opacity-50" 
                    style="height: {((b.frame_count - b.anomaly_count) / maxFrames) * 100}%"
                  ></div>
                {/if}
                
                <!-- Tooltip -->
                <div class="pointer-events-none absolute bottom-full left-1/2 mb-2 w-max -translate-x-1/2 rounded-xl border border-border bg-panel px-4 py-3 text-sm opacity-0 shadow-xl transition-all group-hover:-translate-y-2 group-hover:opacity-100 z-10 backdrop-blur">
                   <p class="font-medium text-ink">{new Date(b.timestamp).toLocaleString(undefined, { 
                     month: 'short', day: 'numeric', 
                     ...(bucket === 'hour' ? {hour: '2-digit', minute: '2-digit'} : {}) 
                   })}</p>
                   <div class="mt-2 space-y-1">
                     <p class="text-ink-2 flex justify-between gap-4"><span>Frames:</span> <span class="font-medium text-ink">{b.frame_count}</span></p>
                     <p class="text-brand flex justify-between gap-4"><span>Anomalies:</span> <span class="font-medium">{b.anomaly_count}</span></p>
                   </div>
                </div>
              </div>
            {/each}
          </div>
        {/if}
      </div>
      
      <div class="mt-6 flex items-center justify-between border-t border-border pt-4 text-xs font-medium text-ink-3">
        <span class="w-24 text-left">{chartData?.buckets?.length > 0 ? new Date(chartData.buckets[0].timestamp).toLocaleDateString() : ''}</span>
        <div class="flex gap-6">
           <span class="flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full bg-ink-3 opacity-40"></span> Nominal</span>
           <span class="flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full bg-brand opacity-90"></span> Anomalous</span>
        </div>
        <span class="w-24 text-right">{chartData?.buckets?.length > 0 ? new Date(chartData.buckets[chartData.buckets.length - 1].timestamp).toLocaleDateString() : ''}</span>
      </div>
    </div>

    <!-- Eclipse Scatter & Distributions -->
    <div class="grid gap-8 lg:grid-cols-2">
      <!-- Scatter Plot -->
      <div class="rounded-[1.75rem] border border-border bg-panel p-6 shadow-panel backdrop-blur lg:p-8">
        <p class="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-6">Eclipse Scatter (Bimodality)</p>
        {#if loadingScatter && !scatterData}
            <div class="flex h-64 items-center justify-center">
              <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
            </div>
        {:else if scatterData && scatterData.frames.length > 0}
          {@const points = scatterData.frames.map((f: any) => ({ x: f.features.temp_panel_z, y: f.features.batt_current, a: f.model?.is_anomaly })).filter((p: any) => p.x != null && p.y != null)}
          {@const minX = Math.min(...points.map((p: any) => p.x)) - 5}
          {@const maxX = Math.max(...points.map((p: any) => p.x)) + 5}
          {@const minY = Math.min(...points.map((p: any) => p.y)) - 0.2}
          {@const maxY = Math.max(...points.map((p: any) => p.y)) + 0.2}
          
          <div class="relative h-64 w-full border-l-2 border-b-2 border-border mt-4 ml-6 mb-8">
              <svg class="absolute inset-0 h-full w-full overflow-visible" viewBox="0 0 100 100" preserveAspectRatio="none">
                {#each points as p}
                  <circle 
                    cx={((p.x - minX) / (maxX - minX)) * 100} 
                    cy={100 - ((p.y - minY) / (maxY - minY)) * 100} 
                    r="1.5" 
                    fill={p.a ? 'var(--color-brand)' : 'var(--color-ink-3)'}
                    opacity={p.a ? "0.8" : "0.3"}
                    class={p.a ? "drop-shadow-[0_0_4px_rgba(177,33,66,0.8)]" : ""}
                  />
                {/each}
              </svg>
              <div class="absolute -left-12 top-1/2 -translate-y-1/2 -rotate-90 text-[0.6rem] font-medium tracking-wider text-ink-3 uppercase whitespace-nowrap">Batt Current (A)</div>
              <div class="absolute -bottom-8 left-1/2 -translate-x-1/2 text-[0.6rem] font-medium tracking-wider text-ink-3 uppercase whitespace-nowrap">Panel Temp Z (°C)</div>
          </div>
          
          <div class="mt-8 flex items-center justify-center gap-6 text-[0.65rem] uppercase tracking-wider text-ink-3">
            <span class="flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-ink-3 opacity-30"></span> Nominal (Eclipse / Sun)</span>
            <span class="flex items-center gap-2"><span class="h-2 w-2 rounded-full bg-brand opacity-80"></span> Anomalous</span>
          </div>
        {:else}
            <div class="flex h-64 flex-col items-center justify-center text-ink-3">
              <p>No valid scatter data found.</p>
            </div>
        {/if}
      </div>

      <!-- Histogram -->
      <div class="rounded-[1.75rem] border border-border bg-panel p-6 shadow-panel backdrop-blur lg:p-8">
        <p class="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-6">Feature Distribution (Temp OBC)</p>
        {#if loadingScatter && !scatterData}
            <div class="flex h-64 items-center justify-center">
              <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
            </div>
        {:else if scatterData && scatterData.frames.length > 0}
          <!-- Histogram approximation for temp_obc -->
          {@const obcTemps = scatterData.frames.map((f: any) => f.features.temp_obc).filter((v: any) => v != null)}
          {@const minT = Math.min(...obcTemps)}
          {@const maxT = Math.max(...obcTemps)}
          {@const binCount = 20}
          {@const bins = Array(binCount).fill(0)}
          {@const binSize = (maxT - minT) / binCount || 1}
          <div class="hidden">
            {obcTemps.forEach((t: number) => {
                const idx = Math.min(Math.floor((t - minT) / binSize), binCount - 1);
                bins[idx]++;
            })}
          </div>
          {@const maxBin = Math.max(...bins)}
          
          <div class="relative h-64 w-full border-b-2 border-border mt-4 ml-6 mb-8 flex items-end gap-[2px]">
              {#each bins as count}
                <div class="flex-1 bg-ink-3 opacity-40 hover:opacity-70 hover:bg-brand transition-all rounded-t-sm" style="height: {(count / (maxBin || 1)) * 100}%" title="Frequency: {count}"></div>
              {/each}
              <div class="absolute -left-10 top-1/2 -translate-y-1/2 -rotate-90 text-[0.6rem] font-medium tracking-wider text-ink-3 uppercase whitespace-nowrap">Frequency</div>
              <div class="absolute -bottom-8 left-1/2 -translate-x-1/2 text-[0.6rem] font-medium tracking-wider text-ink-3 uppercase whitespace-nowrap">OBC Temp (°C)</div>
          </div>
          <div class="mt-8 flex justify-between ml-6 text-[0.65rem] font-medium text-ink-3 uppercase">
            <span>{minT.toFixed(1)}°C</span>
            <span>{maxT.toFixed(1)}°C</span>
          </div>
        {:else}
            <div class="flex h-64 flex-col items-center justify-center text-ink-3">
              <p>No valid distribution data found.</p>
            </div>
        {/if}
      </div>
    </div>
  {/if}
</section>
