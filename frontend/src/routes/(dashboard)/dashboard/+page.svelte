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
  <section class="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
    <div class="space-y-3">
      <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">System Overview</p>
      <h1 class="text-4xl font-semibold tracking-tight text-ink">Dashboard Home</h1>
      <p class="max-w-3xl text-base leading-7 text-ink-2">
        Live operations overview, telemetry throughput, and recent system anomalies.
      </p>
    </div>

    <!-- Totals -->
    <div class="grid gap-4 md:grid-cols-4">
      {#each [
        { label: 'Active Satellites', value: summary.totals.satellite_count, icon: '🛰' },
        { label: 'Total Frames', value: summary.totals.frame_count.toLocaleString(), icon: '📡' },
        { label: 'Anomalies Detected', value: summary.totals.anomaly_count.toLocaleString(), icon: '⚠' },
        { label: 'Total Passes', value: summary.totals.pass_count.toLocaleString(), icon: '🌍' }
      ] as stat}
        <article class="group relative overflow-hidden rounded-[1.75rem] border border-border bg-panel p-6 shadow-panel backdrop-blur transition-all duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-md">
          <div class="absolute -right-4 -top-4 text-4xl opacity-[0.06] transition-opacity group-hover:opacity-[0.12]">{stat.icon}</div>
          <p class="text-sm font-medium text-ink-3">{stat.label}</p>
          <p class="mt-3 text-3xl font-semibold text-brand tracking-tight">{stat.value}</p>
        </article>
      {/each}
    </div>

    <!-- Throughput Sparkline -->
    {#if summary.throughput_buckets && summary.throughput_buckets.length > 0}
      <div class="chart-card">
        <p class="chart-card-title">Throughput (24h)</p>
        <div class="flex items-end gap-6">
          <div class="flex-1">
            <SparklinePlot data={summary.throughput_buckets} width={600} height={56} />
          </div>
          <div class="flex flex-col items-end gap-1 shrink-0 text-right">
            <span class="text-2xl font-semibold tracking-tight text-ink">
              {summary.throughput_buckets.reduce((s: number, b: any) => s + b.frame_count, 0).toLocaleString()}
            </span>
            <span class="text-xs text-ink-3">total frames</span>
          </div>
        </div>
      </div>
    {/if}

    <div class="grid gap-8 lg:grid-cols-3">
      <!-- Service Status -->
      <div class="space-y-4">
        <h2 class="text-lg font-medium tracking-tight text-ink">Component Health</h2>
        <div class="flex flex-col gap-3">
          {#each summary.service_status as component}
            <div class="group flex items-center justify-between rounded-[1.25rem] border border-border bg-surface p-4 transition-colors hover:border-brand/30">
              <div>
                <p class="text-sm font-medium capitalize text-ink transition-colors group-hover:text-brand">{component.name.replace('_', ' ')}</p>
                <p class="mt-1 text-xs text-ink-3">{component.detail}</p>
              </div>
              <div class="flex h-3 w-3 shrink-0 rounded-full transition-all duration-300 {component.status === 'online' ? 'bg-emerald-500 shadow-[0_0_12px_rgba(16,185,129,0.6)]' : 'bg-brand shadow-[0_0_12px_rgba(177,33,66,0.6)]'}"></div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Active Satellites -->
      <div class="space-y-4 lg:col-span-2">
        <h2 class="text-lg font-medium tracking-tight text-ink">Active Profiles</h2>
        <div class="overflow-hidden rounded-[1.5rem] border border-border bg-panel shadow-panel backdrop-blur">
          <table class="w-full text-left text-sm">
            <thead class="border-b border-border bg-surface/50 text-ink-3">
              <tr>
                <th class="px-6 py-4 font-medium">Satellite</th>
                <th class="px-6 py-4 font-medium">Decoder</th>
                <th class="px-6 py-4 font-medium">Frames</th>
                <th class="px-6 py-4 font-medium">Model Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              {#each summary.active_satellites as sat}
                <tr class="transition-colors hover:bg-surface/80">
                  <td class="px-6 py-4">
                    <span class="font-medium text-ink">{sat.name}</span>
                    <span class="ml-2 rounded-md bg-surface px-1.5 py-0.5 text-xs text-ink-3">NORAD {sat.norad_id}</span>
                  </td>
                  <td class="px-6 py-4 text-ink-2">{sat.decoder || 'Generic'}</td>
                  <td class="px-6 py-4 font-mono text-xs text-ink-2">{sat.dataset.row_count.toLocaleString()}</td>
                  <td class="px-6 py-4">
                    <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium {sat.model.status === 'ready' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-brand/10 text-brand'}">
                      {sat.model.status}
                    </span>
                  </td>
                </tr>
              {/each}
              {#if summary.active_satellites.length === 0}
                <tr>
                  <td colspan="4" class="px-6 py-8 text-center text-ink-3">No satellites active.</td>
                </tr>
              {/if}
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Recent Anomalies -->
    <div class="space-y-4">
      <h2 class="text-lg font-medium tracking-tight text-ink">Recent Anomalies</h2>
      <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {#each summary.recent_anomalies as anomaly}
          <div class="group relative overflow-hidden rounded-[1.5rem] border border-brand/20 bg-brand/5 p-6 transition-all duration-300 hover:-translate-y-1 hover:border-brand/40 hover:bg-brand/10 hover:shadow-lg">
            <!-- Subtle glow accent -->
            <div class="absolute -right-8 -top-8 h-24 w-24 rounded-full bg-brand/10 blur-2xl transition-opacity group-hover:bg-brand/20"></div>
            <div class="relative">
              <div class="flex items-center justify-between">
                <span class="rounded-md bg-brand/20 px-2 py-1 text-xs font-semibold tracking-widest text-brand">NORAD {anomaly.norad_id}</span>
                <span class="text-xs text-ink-3">{new Date(anomaly.timestamp).toLocaleString()}</span>
              </div>
              <div class="mt-5 flex items-baseline gap-2">
                <span class="text-3xl font-bold tracking-tight text-ink transition-colors group-hover:text-brand">{anomaly.score?.toFixed(2) || 'N/A'}</span>
                <span class="text-sm font-medium text-ink-3">score</span>
              </div>
              <p class="mt-2 text-xs font-medium text-ink-2">Threshold: {anomaly.threshold?.toFixed(2) || 'N/A'}</p>
            </div>
          </div>
        {/each}
        {#if summary.recent_anomalies.length === 0}
          <div class="col-span-full rounded-[1.5rem] border border-border border-dashed p-10 text-center text-ink-3">
            <p>No recent anomalies detected.</p>
          </div>
        {/if}
      </div>
    </div>
  </section>
{:else}
  <div class="flex h-[60vh] items-center justify-center">
    <div class="relative flex h-12 w-12 items-center justify-center">
      <div class="absolute inset-0 rounded-full border-4 border-surface border-t-brand animate-spin"></div>
      <div class="h-2 w-2 rounded-full bg-brand"></div>
    </div>
  </div>
{/if}
