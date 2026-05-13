<script lang="ts">
  import type { PageData } from './$types';
  import { onMount, onDestroy } from 'svelte';
  import { env } from '$env/dynamic/public';
  import SparklinePlot from '$lib/components/charts/SparklinePlot.svelte';
  
  let { data }: { data: PageData } = $props();
  
  let summary = $state(data.summary);
  let error = $state(data.error);

  $effect(() => {
    summary = data.summary;
    error = data.error;
  });

  let ws: WebSocket;

  onMount(() => {
    const apiUrl = typeof window !== 'undefined' ? (env.PUBLIC_API_URL || 'http://127.0.0.1:8000') : 'http://backend:8000';
    const wsUrl = apiUrl.replace(/^http/, 'ws') + '/api/ws/dashboard';
    
    ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      try {
        summary = JSON.parse(event.data);
        error = undefined;
      } catch (e: any) {
        console.error("Failed to parse websocket message", e);
      }
    };

    ws.onerror = (e) => {
      console.error("Dashboard websocket error", e);
    };
  });

  onDestroy(() => {
    if (ws) ws.close();
  });
</script>

{#if error}
  <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
    <h2 class="text-lg font-semibold">Connection Error</h2>
    <p class="mt-2 text-sm">{error}</p>
  </div>
{:else if summary}
  <section class="flex flex-col h-full min-h-0 gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
    <div class="flex-none space-y-1">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">System Overview</p>
      <h1 class="text-3xl font-semibold tracking-tight text-ink">Dashboard Home</h1>
    </div>

    <!-- Totals -->
    <div class="flex-none grid gap-4 md:grid-cols-4">
      {#each [
        { label: 'Active Satellites', value: summary.totals.satellite_count, icon: '🛰' },
        { label: 'Total Frames', value: summary.totals.frame_count.toLocaleString(), icon: '📡' },
        { label: 'Anomalies Detected', value: summary.totals.anomaly_count.toLocaleString(), icon: '⚠' },
        { label: 'Total Passes', value: summary.totals.pass_count.toLocaleString(), icon: '🌍' }
      ] as stat}
        <article class="group relative overflow-hidden rounded-[1.25rem] border border-border bg-panel p-4 shadow-panel backdrop-blur transition-all duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-md">
          <div class="absolute -right-2 -top-2 text-3xl opacity-[0.06] transition-opacity group-hover:opacity-[0.12]">{stat.icon}</div>
          <p class="text-xs font-medium text-ink-3">{stat.label}</p>
          <p class="mt-1 text-2xl font-semibold text-brand tracking-tight">{stat.value}</p>
        </article>
      {/each}
    </div>

    <!-- Main Grid Layout -->
    <div class="flex-1 min-h-0 grid gap-5 lg:grid-cols-[1fr_1.5fr] xl:grid-cols-[1.5fr_2fr]">

      <!-- Left Col (Component Health & Recent Anomalies) -->
      <div class="flex flex-col gap-5 min-h-0">
        <!-- Service Status -->
        <div class="flex flex-col rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur flex-none">
          <div class="bg-surface/35 p-4 border-b border-border shrink-0">
            <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Component Health</h2>
          </div>
          <div class="flex flex-col gap-px bg-border p-4 shrink-0">
            {#each summary.service_status as component}
              <div class="group flex items-center justify-between bg-surface p-3.5 transition-colors hover:bg-surface/80 rounded-lg">
                <div>
                  <p class="text-sm font-medium capitalize text-ink transition-colors group-hover:text-brand">{component.name.replace('_', ' ')}</p>
                  <p class="text-xs text-ink-3">{component.detail}</p>
                </div>
                <div class="flex h-2.5 w-2.5 shrink-0 rounded-full transition-all duration-300 {component.status === 'online' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]' : 'bg-brand shadow-[0_0_8px_rgba(177,33,66,0.6)]'}"></div>
              </div>
            {/each}
          </div>
        </div>

        <!-- Recent Anomalies -->
        <div class="flex flex-col flex-1 min-h-0 rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur overflow-hidden">
          <div class="bg-surface/35 p-4 border-b border-border shrink-0">
            <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Recent Anomalies</h2>
          </div>
          <div class="flex-1 min-h-0 overflow-y-auto p-4 flex flex-col gap-4">
            {#each summary.recent_anomalies as anomaly}
              <div class="relative overflow-hidden shrink-0 rounded-xl border border-brand/30 bg-brand/5 p-5 transition-all duration-300 hover:border-brand/50">
                <div class="flex items-center justify-between">
                  <span class="rounded-md bg-brand/20 px-2.5 py-1 text-[11px] font-semibold tracking-widest text-brand">NORAD {anomaly.norad_id}</span>
                  <span class="text-xs font-medium text-ink-3">{new Date(anomaly.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="mt-4 flex items-baseline gap-2">
                  <span class="text-3xl font-bold tracking-tight text-ink">{anomaly.score?.toFixed(2) || 'N/A'}</span>
                  <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">score</span>
                </div>
              </div>
            {/each}
            {#if summary.recent_anomalies.length === 0}
              <div class="p-6 text-center text-sm text-ink-3">
                No recent anomalies detected.
              </div>
            {/if}
          </div>
        </div>      </div>

      <!-- Center/Right Col -->
      <div class="flex flex-col gap-5 min-h-0">        
        <!-- Throughput Sparkline -->
        {#if summary.throughput_buckets && summary.throughput_buckets.length > 0}
          <div class="flex-none chart-card">
            <div class="flex items-center justify-between mb-2">
              <p class="chart-card-title">Throughput (24h)</p>
              <div class="text-right">
                <span class="text-xl font-semibold tracking-tight text-ink">
                  {summary.throughput_buckets.reduce((s: number, b: any) => s + b.frame_count, 0).toLocaleString()}
                </span>
                <span class="text-[10px] uppercase tracking-wider text-ink-3 ml-1">total frames</span>
              </div>
            </div>
            <div class="h-16 w-full">
              <SparklinePlot data={summary.throughput_buckets} width={900} height={60} />
            </div>
          </div>
        {/if}

        <!-- Active Profiles Table -->
        <div class="flex flex-col flex-1 min-h-0 rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur">
          <div class="bg-surface/35 p-4 border-b border-border shrink-0">
            <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Active Profiles</h2>
          </div>
          <div class="flex-1 min-h-0 overflow-y-auto relative">
            <table class="w-full text-left text-xs">
              <thead class="sticky top-0 bg-surface/90 backdrop-blur text-ink-3 shadow-sm z-10">
                <tr>
                  <th class="px-4 py-3 font-medium uppercase tracking-wider">Satellite</th>
                  <th class="px-4 py-3 font-medium uppercase tracking-wider">Decoder</th>
                  <th class="px-4 py-3 font-medium uppercase tracking-wider">Frames</th>
                  <th class="px-4 py-3 font-medium uppercase tracking-wider">Model Status</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border">
                {#each summary.active_satellites as sat}
                  <tr class="transition-colors hover:bg-surface/80">
                    <td class="px-4 py-3">
                      <span class="font-semibold text-ink">{sat.name}</span>
                      <span class="ml-2 rounded border border-border bg-surface px-1 py-0.5 text-[9px] text-ink-3">NORAD {sat.norad_id}</span>
                    </td>
                    <td class="px-4 py-3 text-ink-2">{sat.decoder || 'Generic'}</td>
                    <td class="px-4 py-3 font-mono text-ink-2">{sat.dataset.row_count.toLocaleString()}</td>
                    <td class="px-4 py-3">
                      <span class="inline-flex items-center gap-1 rounded bg-panel border border-border px-1.5 py-0.5 text-[10px] font-medium {sat.model.status === 'ready' ? 'text-emerald-500' : 'text-brand'}">
                        <span class="h-1.5 w-1.5 rounded-full {sat.model.status === 'ready' ? 'bg-emerald-500' : 'bg-brand'}"></span>
                        {sat.model.status}
                      </span>
                    </td>
                  </tr>
                {/each}
                {#if summary.active_satellites.length === 0}
                  <tr>
                    <td colspan="4" class="px-4 py-8 text-center text-ink-3">No satellites active.</td>
                  </tr>
                {/if}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </section>
{:else}
  <div class="flex h-full items-center justify-center">
    <div class="relative flex h-12 w-12 items-center justify-center">
      <div class="absolute inset-0 rounded-full border-4 border-surface border-t-brand animate-spin"></div>
      <div class="h-2 w-2 rounded-full bg-brand"></div>
    </div>
  </div>
{/if}