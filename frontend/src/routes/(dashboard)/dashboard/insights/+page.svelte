<script lang="ts">
  import { env } from '$env/dynamic/public';
  import type { PageData } from './$types';
  import { untrack } from 'svelte';

  import EclipseScatterPlot from '$lib/components/charts/EclipseScatterPlot.svelte';
  import FeatureDistributionGrid from '$lib/components/charts/FeatureDistributionGrid.svelte';
  import CorrelationHeatmap from '$lib/components/charts/CorrelationHeatmap.svelte';
  import TimeGapHistogram from '$lib/components/charts/TimeGapHistogram.svelte';
  import MacroHealthPlot from '$lib/components/charts/MacroHealthPlot.svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let noradId = $state<string>('all');
  let dataLimit = $state<number>(1000);

  let loading = $state(false);
  let telemetryFrames = $state<any[]>([]);

  type FeatureMap = Record<string, unknown>;
  type NormalizedFeatures = Record<string, number | null> & {
    batt_voltage: number | null;
    batt_current: number | null;
    batt_a_voltage: number | null;
    batt_b_voltage: number | null;
    temp_batt_a: number | null;
    temp_batt_b: number | null;
    temp_panel_z: number | null;
  };

  function toFiniteNumber(value: unknown): number | null {
    if (typeof value === 'number') return Number.isFinite(value) ? value : null;
    if (typeof value === 'string' && value.trim() !== '') {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : null;
    }
    return null;
  }

  function featureNumber(features: FeatureMap, keys: string[]): number | null {
    for (const key of keys) {
      const value = toFiniteNumber(features[key]);
      if (value !== null) return value;
    }
    return null;
  }

  function batteryVoltage(features: FeatureMap): number | null {
    const combined = toFiniteNumber(features.batt_voltage);
    if (combined !== null) return combined;

    const batteryA = toFiniteNumber(features.batt_a_voltage);
    const batteryB = toFiniteNumber(features.batt_b_voltage);
    if (batteryA !== null && batteryB !== null) return (batteryA + batteryB) / 2;
    return batteryA ?? batteryB;
  }

  function normalizeFeatures(features: FeatureMap): NormalizedFeatures {
    return {
      batt_voltage: batteryVoltage(features),
      batt_current: featureNumber(features, ['batt_current']),
      batt_a_voltage: featureNumber(features, ['batt_a_voltage']),
      batt_b_voltage: featureNumber(features, ['batt_b_voltage']),
      temp_batt_a: featureNumber(features, ['temp_batt_a']),
      temp_batt_b: featureNumber(features, ['temp_batt_b']),
      temp_panel_z: featureNumber(features, ['temp_panel_z']),
    };
  }

  async function fetchTelemetry() {
    loading = true;
    const apiUrl = typeof window !== 'undefined' ? (env.PUBLIC_API_URL || 'http://127.0.0.1:8000') : 'http://backend:8000';
    let url = `${apiUrl}/api/telemetry/recent?limit=${dataLimit}`;
    if (noradId !== 'all') {
      url += `&norad_id=${noradId}`;
    }
    try {
      const res = await fetch(url);
      if (res.ok) {
        const json = await res.json();
        telemetryFrames = json.frames || [];
      } else {
        console.error(`Failed to fetch telemetry: ${res.status}`);
        telemetryFrames = [];
      }
    } catch (e) {
      console.error(e);
      telemetryFrames = [];
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    const _n = noradId;
    const _l = dataLimit;
    untrack(() => fetchTelemetry());
  });

  // Derive feature arrays from frames
  let featureFrames = $derived(
    telemetryFrames
      .filter((f: any): f is { features: FeatureMap } => !!f.features && typeof f.features === 'object')
      .map((f: { features: FeatureMap }) => normalizeFeatures(f.features))
  );

  let eclipseFrames = $derived(
    featureFrames
      .filter(
        (f: NormalizedFeatures): f is NormalizedFeatures & {
          temp_panel_z: number;
          batt_current: number;
          batt_voltage: number;
        } => f.temp_panel_z !== null && f.batt_current !== null && f.batt_voltage !== null
      )
      .map((f) => ({
        temp_panel_z: f.temp_panel_z,
        batt_current: f.batt_current,
        batt_voltage: f.batt_voltage,
      }))
  );

  let macroFrames = $derived(
    telemetryFrames
      .filter((f: any): f is { timestamp: string; features: FeatureMap } => !!f.timestamp && !!f.features && typeof f.features === 'object')
      .map((f: any) => ({
        timestamp: f.timestamp,
        batt_voltage: batteryVoltage(f.features),
        temp_batt_a: featureNumber(f.features, ['temp_batt_a']),
        temp_panel_z: featureNumber(f.features, ['temp_panel_z']),
      }))
  );

  let timestamps = $derived(
    telemetryFrames
      .filter((f: any) => f.timestamp)
      .map((f: any) => f.timestamp)
  );
</script>

<section class="space-y-10 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Exploratory Data Analysis</p>
    <h1 class="text-4xl font-semibold tracking-tight text-ink">EDA & Insights</h1>
    <p class="max-w-3xl text-base leading-7 text-ink-2">
      Physics-driven telemetry analysis. Feature distributions, orbital bimodality, multivariate correlations, and data quality diagnostics.
    </p>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <!-- Satellite Filter -->
    <div class="chart-card">
      <div class="flex flex-wrap items-end gap-6">
        <div class="flex flex-col gap-2">
          <label for="sat-select" class="text-xs font-semibold uppercase tracking-wider text-ink-3">Satellite Profile</label>
          <select id="sat-select" bind:value={noradId} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
            <option value="all">All Satellites</option>
            {#each satellites as sat}
              <option value={sat.norad_id.toString()}>{sat.name} ({sat.norad_id})</option>
            {/each}
          </select>
        </div>
        {#if telemetryFrames.length > 0}
          <div class="ml-auto text-right">
            <p class="text-2xl font-semibold tracking-tight text-ink">{telemetryFrames.length.toLocaleString()}</p>
            <p class="text-xs text-ink-3">frames loaded</p>
          </div>
        {/if}
      </div>
    </div>

    {#if loading && telemetryFrames.length === 0}
      <div class="flex h-60 items-center justify-center">
        <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
      </div>
    {:else if telemetryFrames.length === 0}
      <div class="chart-card">
        <p class="py-12 text-center text-ink-3">No telemetry data found. Ensure the backend is running and has processed data.</p>
      </div>
    {:else}
      <!-- Restructured Grid Layout for Charts -->
      <div class="grid gap-6 xl:grid-cols-3 items-start">
        
        <!-- Left/Main Column -->
        <div class="flex flex-col gap-6 xl:col-span-2">
          <!-- Macro Health -->
          <div class="chart-card">
            <p class="chart-card-title">Macro-Scale Health — Daily Averages</p>
            <MacroHealthPlot frames={macroFrames} />
          </div>

          <!-- Feature Distributions -->
          <div class="chart-card">
            <div class="flex items-baseline justify-between mb-4">
              <h2 class="text-sm font-medium tracking-tight text-ink">Feature Distributions</h2>
              <span class="text-[10px] uppercase tracking-wider text-ink-3">{featureFrames.length.toLocaleString()} frames</span>
            </div>
            <FeatureDistributionGrid frames={featureFrames} />
          </div>
        </div>

        <!-- Right/Sidebar Column -->
        <div class="flex flex-col gap-6">
          <!-- Eclipse Scatter -->
          <div class="chart-card">
            <p class="chart-card-title">Physics Verification (Day/Night)</p>
            <p class="mb-3 text-[10px] leading-4 text-ink-3">
              Solar panel temp exposes orbital phase. Positive current during low temp signals an anomaly.
            </p>
            <EclipseScatterPlot frames={eclipseFrames} />
          </div>

          <!-- Correlation Heatmap -->
          <div class="chart-card">
            <p class="chart-card-title">Feature Correlation</p>
            <CorrelationHeatmap frames={featureFrames} />
          </div>

          <!-- Time Gap Histogram -->
          <div class="chart-card">
            <p class="chart-card-title">Intra-Pass Time Gaps</p>
            <p class="mb-3 text-[10px] leading-4 text-ink-3">
              Large gaps indicate dropped packets or geometry constraints.
            </p>
            <TimeGapHistogram {timestamps} />
          </div>
        </div>
      </div>
    {/if}
  {/if}
</section>
