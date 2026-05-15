<script lang="ts">
  import { env } from '$env/dynamic/public';
  import type { PageData } from './$types';
  import { untrack } from 'svelte';

  import EclipseScatterPlot from '$lib/components/charts/EclipseScatterPlot.svelte';
  import CorrelationHeatmap from '$lib/components/charts/CorrelationHeatmap.svelte';

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
</script>

<div class="mx-auto max-w-4xl pb-24">
  <header class="space-y-4 mb-12 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Analysis Report</p>
    <h1 class="text-4xl font-bold tracking-tight text-ink sm:text-5xl">Exploratory Data Analysis</h1>
    <p class="text-lg leading-8 text-ink-2">
      Physics-driven validation of raw telemetry data. This notebook-style report breaks down
      the fundamental orbital mechanics and multivariate correlations used to engineer the 
      golden features for our autoencoder models.
    </p>
  </header>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <!-- Controls (Minimal, inline) -->
    <div class="mb-12 flex flex-wrap items-center gap-4 rounded-2xl border border-border bg-surface/50 p-4">
      <div class="flex items-center gap-3">
        <label for="sat-select" class="text-xs font-semibold uppercase tracking-wider text-ink-3">Target Profile</label>
        <select id="sat-select" bind:value={noradId} class="rounded-lg border border-border bg-panel px-3 py-1.5 text-sm text-ink outline-none transition hover:border-brand">
          <option value="all">All Satellites (Global View)</option>
          {#each satellites as sat}
            <option value={sat.norad_id.toString()}>{sat.name} ({sat.norad_id})</option>
          {/each}
        </select>
      </div>
      {#if loading}
        <div class="h-4 w-4 animate-spin rounded-full border-2 border-surface border-t-brand ml-auto"></div>
      {:else if telemetryFrames.length > 0}
        <div class="ml-auto text-xs text-ink-3">
          Analyzing <span class="font-mono font-medium text-ink">{telemetryFrames.length.toLocaleString()}</span> frames
        </div>
      {/if}
    </div>

    {#if !loading && telemetryFrames.length === 0}
      <div class="rounded-2xl border border-border border-dashed py-16 text-center text-ink-3">
        No telemetry data found for this profile.
      </div>
    {:else if telemetryFrames.length > 0}
      
      <article class="prose prose-slate dark:prose-invert max-w-none space-y-12">
        
        <!-- SECTION 1: Physics Validation -->
        <section>
          <h2>Physics Verification: The Eclipse Cycle</h2>
          <p>
            Before feeding raw digital signals into an unsupervised machine learning model, we must verify that the 
            decoded features accurately represent the physical reality of the satellite in orbit. The most prominent 
            and predictable cycle for any Low Earth Orbit (LEO) satellite is the <strong>Day/Night (Eclipse) cycle</strong>.
          </p>
          <p>
            By plotting the temperature of the outward-facing solar panels against the battery charging current, 
            we expect to see a strict bimodal distribution representing the two physical states:
          </p>
          <ul>
            <li><strong>Sunlight (Day):</strong> High panel temperatures. Positive battery current (charging).</li>
            <li><strong>Eclipse (Night):</strong> Low panel temperatures. Negative battery current (discharging to run payloads).</li>
          </ul>

          <div class="my-8 rounded-2xl border border-border bg-panel p-6 shadow-sm">
            <h3 class="mt-0 mb-6 text-sm font-semibold uppercase tracking-widest text-ink-3">Solar Panel Temp vs. Battery Current</h3>
            <div class="h-[400px]">
              <EclipseScatterPlot frames={eclipseFrames} />
            </div>
            <p class="mt-4 mb-0 text-xs leading-relaxed text-ink-3 border-t border-border/50 pt-4">
              <strong>Diagnostic Heuristic:</strong> Data points falling into the top-left quadrant (positive charging current while panels are freezing cold) violate orbital physics and immediately flag a sensor fault, a decoding alignment error, or an EPS anomaly.
            </p>
          </div>
        </section>

        <!-- SECTION 2: Feature Correlation -->
        <section>
          <h2>Multivariate Feature Correlation</h2>
          <p>
            To build a robust Autoencoder, we need to understand how the golden features interact across different subsystems. 
            Highly correlated features (e.g., Battery A Voltage and Battery B Voltage) can be compressed efficiently in the 
            latent space. Conversely, uncorrelated features (e.g., Antenna Deployment Status and Radio Temperature) require 
            independent representation.
          </p>
          <p>
            The heatmap below visualizes the Pearson correlation coefficients across the parsed continuous variables. 
            Darker intersections indicate a strong positive or negative linear relationship.
          </p>

          <div class="my-8 rounded-2xl border border-border bg-panel p-6 shadow-sm">
            <h3 class="mt-0 mb-6 text-sm font-semibold uppercase tracking-widest text-ink-3">Pearson Correlation Matrix</h3>
            <div class="h-[500px]">
              <CorrelationHeatmap frames={featureFrames} />
            </div>
          </div>
        </section>

      </article>

    {/if}
  {/if}
</div>
