<script lang="ts">
  import { env } from '$env/dynamic/public';
  import type { PageData } from './$types';
  import ThroughputVolumePlot from '$lib/components/charts/ThroughputVolumePlot.svelte';
  import PassDurationScatterPlot from '$lib/components/charts/PassDurationScatterPlot.svelte';
  import LinkQualityPlot from '$lib/components/charts/LinkQualityPlot.svelte';
  import MissingFieldsBarChart from '$lib/components/charts/MissingFieldsBarChart.svelte';
  import MacroVoltageTrendPlot from '$lib/components/charts/MacroVoltageTrendPlot.svelte';
  import OrbitalDriftPlot from '$lib/components/charts/OrbitalDriftPlot.svelte';
  import SparklinePlot from '$lib/components/charts/SparklinePlot.svelte';
  import { SERIES_CURRENT as BLUE, SERIES_AMBER as AMBER } from '$lib/chart-theme';
  import { fly, fade } from 'svelte/transition';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import Select from '$lib/components/ui/Select.svelte';
  import { 
    ShieldCheck, Cpu, TrendingUp, Activity, Database, Clock, BarChart2
  } from "lucide-svelte";

  let { data }: { data: PageData } = $props();

  let error = $derived(data.error);
  let analytics = $derived(data.analytics);
  let satellites = $derived(data.satellites || []);

  import { uiState } from '$lib/stores/ui-state.svelte';

  // State Management for active Tab (Preserved through query parameter or URL)
  let activeTab = $state<'throughput' | 'quality' | 'health'>(uiState.analytics.activeTab);
  
  $effect(() => {
    uiState.analytics.activeTab = activeTab;
    const tabParam = $page.url.searchParams.get('tab');
    if (tabParam === 'throughput' || tabParam === 'quality' || tabParam === 'health') {
      activeTab = tabParam;
    }
  });

  function setTab(tab: 'throughput' | 'quality' | 'health') {
    activeTab = tab;
    const newUrl = new URL($page.url);
    newUrl.searchParams.set('tab', tab);
    goto(newUrl.toString(), { replaceState: true, noScroll: true });
  }

  let currentNorad = $derived($page.url.searchParams.get('norad_id') || '43880');
  
  function handleSatelliteChange(newNorad: string) {
    const newUrl = new URL($page.url);
    newUrl.searchParams.set('norad_id', newNorad);
    // Preserve the active tab in the URL when changing the satellite Target Profile
    newUrl.searchParams.set('tab', activeTab);
    goto(newUrl.toString());
  }

  // Real Calculated Metrics
  let totalFrames = $derived(analytics ? (analytics.quality.complete_frames + analytics.quality.partial_frames) : 0);
  let parsedDataMB = $derived(analytics ? ((totalFrames * 256) / (1024 * 1024)).toFixed(2) : '0.00');

  // Calculate real average pass duration
  let avgPassDuration = $derived(() => {
    if (!analytics || !analytics.pass_metrics || analytics.pass_metrics.length === 0) return '0.0';
    const sum = analytics.pass_metrics.reduce((acc: number, p: any) => acc + p.duration_sec, 0);
    return (sum / analytics.pass_metrics.length).toFixed(1);
  });

  // Calculate real peak daily influx
  let maxDailyFrames = $derived(() => {
    if (!analytics || !analytics.throughput_30d || analytics.throughput_30d.length === 0) return 0;
    return Math.max(...analytics.throughput_30d.map((d: any) => d.frame_count));
  });

  // Calculate real parser success rate
  let successRate = $derived(() => {
    if (totalFrames === 0) return '100.0';
    return ((analytics.quality.complete_frames / totalFrames) * 100).toFixed(1);
  });

  // Calculate real mean battery voltage over 180 days
  let avgVoltage = $derived(() => {
    if (!analytics || !analytics.macro_health || analytics.macro_health.length === 0) return '0.00';
    const valid = analytics.macro_health.filter((d: any) => d.batt_voltage_mean != null);
    if (valid.length === 0) return '0.00';
    const sum = valid.reduce((acc: number, d: any) => acc + d.batt_voltage_mean, 0);
    return (sum / valid.length).toFixed(2);
  });

  // Calculate real mean solar panel temperature over 180 days
  let avgTemp = $derived(() => {
    if (!analytics || !analytics.macro_health || analytics.macro_health.length === 0) return '0.0';
    const valid = analytics.macro_health.filter((d: any) => d.temp_panel_z_mean != null);
    if (valid.length === 0) return '0.0';
    const sum = valid.reduce((acc: number, d: any) => acc + d.temp_panel_z_mean, 0);
    return (sum / valid.length).toFixed(1);
  });

  const formatLabel = (k: string) => k
    .replace('temp_obc', 'OBC Temp')
    .replace('temp_batt_a', 'Battery A Temp')
    .replace('temp_batt_b', 'Battery B Temp')
    .replace('temp_panel_z', 'Panel Z Temp')
    .replace('batt_voltage', 'Battery Voltage')
    .replace('batt_current', 'Battery Current')
    .replace('power_consumption', 'Power Consumption')
    .replace('temp_', '')
    .replace('batt_', '')
    .replace('_', ' ')
    .replace(/\b\w/g, (c: string) => c.toUpperCase());

  // Safe getter for field integrity dictionary
  let fieldIntegrity = $derived((analytics?.quality?.field_integrity || {}) as Record<string, number>);

  // Safe getter for macro health correlation matrix
  let correlationMatrix = $derived((analytics?.macro_health_correlation || {}) as Record<string, Record<string, number>>);

  // Dynamic SNR calculation
  let avgSnr = $derived(analytics?.quality?.avg_snr != null ? analytics.quality.avg_snr.toFixed(1) : 'N/A');

  // Dynamic battery & thermal status based on recent telemetry values
  let recentHealth = $derived(analytics?.macro_health && analytics.macro_health.length > 0 ? analytics.macro_health[analytics.macro_health.length - 1] : null);
  
  let batteryStatus = $derived(() => {
    if (!recentHealth || recentHealth.batt_voltage_mean == null) return { text: 'Unknown', color: 'text-ink-3' };
    const v = recentHealth.batt_voltage_mean;
    if (v < 3.5) return { text: 'Low Voltage', color: 'text-red-500' };
    if (v < 3.7) return { text: 'Degraded', color: 'text-warning' };
    return { text: 'Optimal', color: 'text-emerald-500' };
  });

  let thermalStatus = $derived(() => {
    if (!recentHealth || recentHealth.temp_panel_z_mean == null) return { text: 'Unknown', color: 'text-ink-3' };
    const t = recentHealth.temp_panel_z_mean;
    if (t > 45.0 || t < -10.0) return { text: 'Critical', color: 'text-red-500' };
    if (t > 30.0 || t < 0.0) return { text: 'Warning', color: 'text-warning' };
    return { text: 'Nominal', color: 'text-emerald-500' };
  });
</script>

<style>
  .dashboard-columns {
    display: grid;
    grid-template-columns: repeat(1, minmax(0, 1fr));
    gap: 1.25rem;
    align-items: start;
  }
  @media (min-width: 1024px) {
    .grid-2col-split {
      grid-template-columns: 2fr 1fr;
    }
    .grid-quality-split {
      grid-template-columns: 1fr 2fr;
    }
  }

  .kpi-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1rem;
  }
  @media (min-width: 768px) {
    .kpi-row {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
  }

  .kpi-card {
    background: var(--panel-bg, rgba(30, 30, 38, 0.45));
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.05));
    border-radius: 0.75rem;
    padding: 0.75rem 1rem;
    display: flex;
    flex-direction: column;
    justify-content: center;
    transition: border-color 0.2s ease;
  }

  :global(.light) .kpi-card {
    background: rgba(255, 255, 255, 0.65);
    border-color: rgba(0, 0, 0, 0.05);
  }

  .kpi-card:hover {
    border-color: rgba(139, 92, 246, 0.25);
  }

  .panel-card {
    background: var(--panel-bg, rgba(30, 30, 38, 0.45));
    border: 1px solid var(--border-color, rgba(255, 255, 255, 0.05));
    border-radius: 0.75rem;
    padding: 1rem;
    display: flex;
    flex-direction: column;
  }
  :global(.light) .panel-card {
    background: rgba(255, 255, 255, 0.65);
    border-color: rgba(0, 0, 0, 0.05);
  }

  .correlation-cell {
    transition: all 0.2s ease;
  }
  .correlation-cell:hover {
    transform: scale(1.05);
    z-index: 10;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
  }
</style>

<section in:fly={{ y: 15, duration: 400, delay: 50 }} class="flex flex-col gap-4 w-full tall-lg:flex-1 tall-lg:min-h-0 tall-lg:max-h-[92vh] tall-lg:overflow-hidden">
  
  <!-- Header row (Very compact) -->
  <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 shrink-0">
    <div class="space-y-0.5">
      <p class="text-[10px] font-bold uppercase tracking-[0.2em] text-muted">Deep Dive</p>
      <h1 class="text-2xl font-bold tracking-tight text-ink">Analytics</h1>
    </div>
    
    <div class="flex items-center gap-3">
      <label for="sat-select" class="text-[10px] font-bold uppercase tracking-wider text-ink-3">Target Profile</label>
      <Select
        id="sat-select"
        value={currentNorad}
        onchange={(val) => handleSatelliteChange(val.toString())}
        options={[{ value: 'all', label: 'All Satellites (Global View)' }, ...satellites.map(s => ({ value: s.norad_id.toString(), label: `${s.name} (${s.norad_id})` }))]}
        class="rounded-lg border border-border bg-panel px-3 py-1.5 min-w-[200px] outline-none transition hover:border-brand text-xs"
        labelClass="text-xs text-ink font-medium"
      />
    </div>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-4 text-xs text-brand shrink-0">
      {error}
    </div>
  {:else if !analytics}
    <div class="flex items-center justify-center p-20 grow">
      <div class="h-8 w-8 animate-spin rounded-full border-2 border-surface border-t-brand"></div>
    </div>
  {:else}
    <!-- Tab Selectors (Compact) -->
    <div class="flex items-center gap-2 border-b border-border shrink-0">
      <button 
        class="px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center gap-1.5 -mb-[2px] {activeTab === 'throughput' ? 'border-brand text-brand font-bold' : 'border-transparent text-ink-3 hover:text-ink hover:border-border'}"
        onclick={() => setTab('throughput')}
      >
        <TrendingUp class="size-3.5" />
        Network Throughput
      </button>
      <button 
        class="px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center gap-1.5 -mb-[2px] {activeTab === 'quality' ? 'border-brand text-brand font-bold' : 'border-transparent text-ink-3 hover:text-ink hover:border-border'}"
        onclick={() => setTab('quality')}
      >
        <ShieldCheck class="size-3.5" />
        Data Quality
      </button>
      <button 
        class="px-4 py-2.5 text-xs font-semibold transition-all border-b-2 flex items-center gap-1.5 -mb-[2px] {activeTab === 'health' ? 'border-brand text-brand font-bold' : 'border-transparent text-ink-3 hover:text-ink hover:border-border'}"
        onclick={() => setTab('health')}
      >
        <Activity class="size-3.5" />
        Hardware Health
      </button>
    </div>

    <!-- Active Tab Panel -->
    <div class="grow flex flex-col justify-start overflow-hidden">
      
      {#if activeTab === 'throughput'}
        <div in:fade={{ duration: 150 }} class="flex flex-col gap-3 w-full">
          
          <!-- KPI Row -->
          <div class="kpi-row shrink-0">
            <div class="kpi-card flex flex-row items-center justify-between gap-4">
              <div class="flex flex-col">
                <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Total Frames</span>
                <p class="text-xl font-bold text-ink mt-0.5">{totalFrames.toLocaleString()}</p>
              </div>
              {#if analytics.throughput_30d}
                <div class="w-16 shrink-0 opacity-80">
                  <SparklinePlot data={analytics.throughput_30d.slice(-7)} height={32} />
                </div>
              {/if}
            </div>
            <div class="kpi-card flex flex-row items-center justify-between gap-4">
              <div class="flex flex-col">
                <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Data Ingress</span>
                <p class="text-xl font-bold text-ink mt-0.5">{parsedDataMB} MB</p>
              </div>
              {#if analytics.throughput_30d}
                <div class="w-16 shrink-0 opacity-80">
                  <SparklinePlot data={analytics.throughput_30d.slice(-7)} height={32} />
                </div>
              {/if}
            </div>
            <div class="kpi-card flex flex-row items-center justify-between gap-4">
              <div class="flex flex-col">
                <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Avg Pass Duration</span>
                <p class="text-xl font-bold text-ink mt-0.5">{avgPassDuration()}s</p>
              </div>
              {#if analytics.pass_metrics}
                <div class="w-16 shrink-0 opacity-80">
                  <SparklinePlot data={analytics.pass_metrics.slice(-7).map((p: any) => ({ frame_count: p.duration_sec, anomaly_count: 0 }))} height={32} />
                </div>
              {/if}
            </div>
            <div class="kpi-card flex flex-row items-center justify-between gap-4">
              <div class="flex flex-col">
                <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Peak Influx</span>
                <p class="text-xl font-bold text-ink mt-0.5">{maxDailyFrames().toLocaleString()} f/d</p>
              </div>
              {#if analytics.throughput_30d}
                <div class="w-16 shrink-0 opacity-80">
                  <SparklinePlot data={analytics.throughput_30d.slice(-7)} height={32} />
                </div>
              {/if}
            </div>
          </div>

          <!-- Main Layout: 2-Column Split -->
          <div class="dashboard-columns grid-2col-split w-full shrink-0">
            <!-- Left Column: Volume plot + Passes Table -->
            <div class="flex flex-col gap-3">
              <!-- Wide Line Chart -->
              <div class="panel-card">
                <h3 class="mt-0 mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                  30-Day Frame Volume
                </h3>
                <div class="w-full">
                  <ThroughputVolumePlot data={analytics.throughput_30d || []} height={280} />
                </div>
              </div>

              <!-- Passes table to fill space scientifically -->
              <div class="panel-card">
                <h3 class="mt-0 mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                  Recent Observation Passes
                </h3>
                <div class="overflow-x-auto">
                  <table class="w-full text-left text-[11px] border-collapse">
                    <thead>
                      <tr class="border-b border-border/40 text-ink-3 font-semibold">
                        <th class="py-1.5 px-2">Pass ID</th>
                        <th class="py-1.5 px-2">Acquisition Time (UTC)</th>
                        <th class="py-1.5 px-2 text-right">Duration</th>
                        <th class="py-1.5 px-2 text-right">Decoded Frames</th>
                        <th class="py-1.5 px-2 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-border/20 font-medium">
                      {#if analytics.pass_metrics && analytics.pass_metrics.length > 0}
                        {#each analytics.pass_metrics.slice(-8).reverse() as p}
                          {@const isNominal = p.frame_count >= 5 && p.duration_sec > 0}
                          {@const isDegraded = p.frame_count > 0 && p.frame_count < 5 && p.duration_sec > 0}
                          <tr>
                            <td class="py-1.5 px-2 text-ink">#{p.pass_id}</td>
                            <td class="py-1.5 px-2 text-ink-3">{new Date(p.timestamp).toLocaleString()}</td>
                            <td class="py-1.5 px-2 text-ink text-right">{p.duration_sec.toFixed(0)}s</td>
                            <td class="py-1.5 px-2 text-right text-brand">{p.frame_count}</td>
                            <td class="py-1.5 px-2 text-right">
                              <span class="text-[9px] px-1.5 py-0.5 rounded font-bold {isNominal ? 'bg-emerald-500/10 text-emerald-500' : isDegraded ? 'bg-warning/10 text-warning' : 'bg-red-500/10 text-red-500'}">
                                {isNominal ? 'Nominal' : isDegraded ? 'Degraded' : 'Incomplete'}
                              </span>
                            </td>
                          </tr>
                        {/each}
                      {:else}
                        <tr>
                          <td colspan="5" class="py-3 text-center text-ink-3">No tracking pass instances recorded.</td>
                        </tr>
                      {/if}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Right Column: Scatter Plot & Link Quality Plot stacked -->
            <div class="flex flex-col gap-3">
              <div class="panel-card">
                <h3 class="mt-0 mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm" style="background: {BLUE}"></span>
                  Pass Duration vs Yield
                </h3>
                <div class="w-full">
                  <PassDurationScatterPlot data={analytics.pass_metrics} height={220} />
                </div>
              </div>

              <div class="panel-card">
                <h3 class="mt-0 mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm" style="background: {AMBER}"></span>
                  Link Quality Degradation
                </h3>
                <div class="w-full">
                  <LinkQualityPlot data={analytics.throughput_30d || []} height={220} />
                </div>
              </div>
            </div>
          </div>
        </div>

      {:else if activeTab === 'quality'}
        <div in:fade={{ duration: 150 }} class="flex flex-col gap-3 w-full">
          
          <!-- KPI Row -->
          <div class="kpi-row shrink-0">
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Complete Frames</span>
              <p class="text-xl font-bold text-emerald-500 mt-0.5">{analytics.quality.complete_frames.toLocaleString()}</p>
            </div>
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Partial Frames</span>
              <p class="text-xl font-bold {analytics.quality.partial_frames > 0 ? 'text-warning' : 'text-ink-3'} mt-0.5">{analytics.quality.partial_frames.toLocaleString()}</p>
            </div>
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Success Rate</span>
              <p class="text-xl font-bold text-ink mt-0.5">{successRate()}%</p>
            </div>
          </div>

          <!-- Bottom Grid -->
          <div class="dashboard-columns grid-quality-split w-full tall-lg:flex-1 tall-lg:min-h-0 !items-stretch">
            <!-- Left Info Panel & Field Success rates -->
            <div class="flex flex-col gap-3 h-full">
              <div class="panel-card flex-none">
                <h3 class="mt-0 mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                  Decoder Performance Summary
                </h3>
                <div class="grid grid-cols-2 gap-3 text-[11px] leading-relaxed text-ink-2 mt-1">
                  <div class="flex flex-col bg-panel/30 border border-border/25 p-2 rounded-lg">
                    <span class="text-ink-3 text-[9px] uppercase tracking-wider font-bold">Total Packets Parsed</span>
                    <span class="text-sm font-semibold text-ink mt-0.5">{totalFrames.toLocaleString()}</span>
                  </div>
                  <div class="flex flex-col bg-panel/30 border border-border/25 p-2 rounded-lg">
                    <span class="text-ink-3 text-[9px] uppercase tracking-wider font-bold">Frame Parse Errors</span>
                    <span class="text-sm font-semibold text-ink mt-0.5">{analytics.quality.partial_frames.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <!-- Real Dynamic Field Success Table -->
              <div class="panel-card flex-1 min-h-0 flex flex-col">
                <h3 class="mt-0 mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                  Field Extraction success
                </h3>
                <div class="overflow-x-auto flex-1 min-h-0">
                  <table class="w-full text-left text-[11px] border-collapse">
                    <thead>
                      <tr class="border-b border-border/40 text-ink-3 font-semibold">
                        <th class="py-1.5 px-1">Telemetry Field</th>
                        <th class="py-1.5 px-1 text-right">Integrity</th>
                        <th class="py-1.5 px-1 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody class="divide-y divide-border/20 font-medium">
                      {#each Object.entries(fieldIntegrity) as [field, rate]}
                        {@const pct = (rate * 100).toFixed(1)}
                        <tr>
                          <td class="py-2 px-1 text-ink">{formatLabel(field)}</td>
                          <td class="py-2 px-1 text-right text-ink-2">
                            <div>{pct}%</div>
                            <div class="w-16 h-1 bg-panel border border-border/10 rounded-full ml-auto overflow-hidden mt-1">
                              <div class="h-full bg-emerald-500 rounded-full" style="width: {pct}%"></div>
                            </div>
                          </td>
                          <td class="py-2 px-1 text-right">
                            <span class="text-[9px] px-1.5 py-0.5 rounded font-bold {rate > 0.95 ? 'bg-emerald-500/10 text-emerald-500' : rate > 0.0 ? 'bg-warning/10 text-warning' : 'bg-red-500/10 text-red-500'}">
                              {rate > 0.95 ? 'Optimal' : rate > 0.0 ? 'Degraded' : 'Missing'}
                            </span>
                          </td>
                        </tr>
                      {/each}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            <!-- Right Panel: Missing fields bar chart -->
            <div class="panel-card">
              <h3 class="mt-0 mb-3 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm bg-warning"></span>
                Top Missing Fields
              </h3>
              
              {#if analytics.quality.missing_fields.length > 0}
                <div class="w-full flex-1 h-full min-h-[420px]">
                  <MissingFieldsBarChart data={analytics.quality.missing_fields} height={420} />
                </div>
              {:else}
                <div class="w-full flex-1 h-full min-h-[420px] flex flex-col items-center justify-center text-emerald-500 border border-dashed border-emerald-500/20 bg-emerald-500/5 rounded-xl p-6">
                  <span class="text-sm font-semibold mb-1">100% Data Integrity</span>
                  <span class="text-[10px] opacity-75">No missing fields recorded. All packets parsed perfectly.</span>
                </div>
              {/if}
            </div>
          </div>
        </div>

      {:else if activeTab === 'health'}
        <div in:fade={{ duration: 150 }} class="flex flex-col gap-3 w-full">
          
          <!-- KPI Row -->
          <div class="kpi-row shrink-0">
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">180-Day Mean Voltage</span>
              <p class="text-xl font-bold text-ink mt-0.5">{avgVoltage()} V</p>
            </div>
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">180-Day Mean Temp</span>
              <p class="text-xl font-bold text-ink mt-0.5">{avgTemp()} °C</p>
            </div>
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Battery Status</span>
              <p class="text-xl font-bold {batteryStatus().color} mt-0.5">{batteryStatus().text}</p>
            </div>
            <div class="kpi-card">
              <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Thermal State</span>
              <p class="text-xl font-bold {thermalStatus().color} mt-0.5">{thermalStatus().text}</p>
            </div>
          </div>

          <!-- Bottom Grid: Left charts, Right correlation matrix heatmap -->
          <div class="dashboard-columns grid-2col-split w-full shrink-0">
            <!-- Left Column: Two health trends stacked -->
            <div class="flex flex-col gap-3">
              <div class="panel-card">
                <h3 class="mt-0 mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                  Macro Battery Voltage (180 Days)
                </h3>
                <div class="w-full">
                  <MacroVoltageTrendPlot data={analytics.macro_health || []} height={280} />
                </div>
              </div>

              <div class="panel-card">
                <h3 class="mt-0 mb-1 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3">
                  <span class="inline-block h-3 w-1 rounded-sm" style="background: {AMBER}"></span>
                  Thermodynamic Z Drift (180 Days)
                </h3>
                <div class="w-full">
                  <OrbitalDriftPlot data={analytics.macro_health || []} height={280} />
                </div>
              </div>
            </div>

            <!-- Right Column: Real Pearson correlation heatmap -->
            <div class="panel-card h-full justify-between flex flex-col">
              <div class="flex flex-col h-full flex-1">
                <h3 class="mt-0 mb-2 flex items-center gap-2 text-xs font-semibold uppercase tracking-widest text-ink-3 shrink-0">
                  <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                  Telemetry Pearson Correlation
                </h3>
                <p class="text-[10px] leading-relaxed text-ink-3 mb-4 shrink-0">
                  Dynamic correlation coefficients (r) computed dynamically from all dataset rows.
                </p>
                
                {#if Object.keys(correlationMatrix).length > 0}
                  <div class="overflow-x-auto mt-2 flex-1 flex flex-col">
                    <table class="w-full h-full text-center border-collapse text-xs">
                      <thead>
                        <tr>
                          <th class="p-3 text-left text-ink-3 font-semibold uppercase tracking-wider">Field</th>
                          {#each Object.keys(correlationMatrix) as key}
                            <th class="p-3 text-ink-3 font-semibold uppercase tracking-wider">{formatLabel(key)}</th>
                          {/each}
                        </tr>
                      </thead>
                      <tbody>
                        {#each Object.entries(correlationMatrix) as [rowKey, cols]}
                          <tr class="border-t border-border/20">
                            <td class="p-3 py-4 text-left font-bold text-ink-2">{formatLabel(rowKey)}</td>
                            {#each Object.entries(cols) as [colKey, val]}
                              {@const isSelf = rowKey === colKey}
                              {@const absVal = Math.abs(val)}
                              <td 
                                class="p-3 py-4 text-sm font-bold correlation-cell" 
                                style="background: {isSelf ? 'rgba(139, 92, 246, 0.15)' : val > 0 ? `rgba(16, 185, 129, ${absVal * 0.25})` : `rgba(245, 158, 11, ${absVal * 0.25})`}; 
                                       color: {isSelf ? '#8B5CF6' : val > 0 ? '#10B981' : '#F59E0B'};
                                       border: 3px solid transparent; background-clip: padding-box;"
                              >
                                {val > 0 && !isSelf ? '+' : ''}{val.toFixed(2)}
                              </td>
                            {/each}
                          </tr>
                        {/each}
                      </tbody>
                    </table>
                  </div>
                {:else}
                  <div class="text-center text-ink-3 py-6 text-xs">
                    Insufficient variables for correlation matrix.
                  </div>
                {/if}
              </div>
              <div class="text-[9px] text-ink-3 border-t border-border/40 mt-4 pt-2">
                * Positive (green) vs Negative (orange) coupling trends.
              </div>
            </div>
          </div>
        </div>
      {/if}

    </div>
  {/if}
</section>