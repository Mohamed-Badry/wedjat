<script lang="ts">
  import type { PageData } from './$types';
  import { apiFetch } from '$lib/api';
  import { fly, fade } from 'svelte/transition';
  import type { TelemetryFrame } from '$lib/types/api';
  import Select from '$lib/components/ui/Select.svelte';

  import EclipseScatterPlot from '$lib/components/charts/EclipseScatterPlot.svelte';
  import CorrelationHeatmap from '$lib/components/charts/CorrelationHeatmap.svelte';
  import TimeGapHistogram from '$lib/components/charts/TimeGapHistogram.svelte';
  import InterPassGapHistogram from '$lib/components/charts/InterPassGapHistogram.svelte';
  import MacroHealthPlot from '$lib/components/charts/MacroHealthPlot.svelte';
  import FeatureDistributionGrid from '$lib/components/charts/FeatureDistributionGrid.svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  import { uiState } from '$lib/stores/ui-state.svelte';

  let noradId = $state<string>(uiState.eda.noradId);
  let dataLimit = $state<number>(uiState.eda.dataLimit);
  let loading = $state(false);
  let telemetryFrames = $state<TelemetryFrame[]>(uiState.eda.telemetryFrames);

  $effect(() => {
    uiState.eda.noradId = noradId;
    uiState.eda.dataLimit = dataLimit;
    uiState.eda.telemetryFrames = telemetryFrames;
  });

  import { normalizeFeatures } from '$lib/data/transforms';
  import type { FeatureMap, NormalizedFeatures } from '$lib/data/transforms';

  async function fetchTelemetry() {
    loading = true;
    let path = `/api/telemetry/recent?limit=${dataLimit}`;
    if (noradId !== 'all') {
      path += `&norad_id=${noradId}`;
    }
    try {
      const json = await apiFetch<any>(path);
      telemetryFrames = Array.isArray(json) ? json : (json.frames || []);
    } catch (e) {
      console.error(e);
      telemetryFrames = [];
    } finally {
      loading = false;
    }
  }

  // Derive feature arrays from frames
  let featureFrames = $derived(
    telemetryFrames
      .filter((f): f is TelemetryFrame & { features: FeatureMap } => !!f.features && typeof f.features === 'object')
      .map((f) => normalizeFeatures(f.features as FeatureMap))
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
      .filter((f) => !!f.timestamp && !!f.features && typeof f.features === 'object')
      .map((f) => {
        const norm = normalizeFeatures(f.features as FeatureMap);
        return {
          timestamp: f.timestamp,
          batt_voltage: norm.batt_voltage,
          temp_batt_a: norm.temp_batt_a,
          temp_panel_z: norm.temp_panel_z,
        };
      })
  );

  let timestamps = $derived(
    telemetryFrames
      .filter((f) => f.timestamp)
      .map((f) => f.timestamp)
  );
</script>

<svelte:head>
  <title>EDA Report — Watchdog</title>
</svelte:head>

<div class="mx-auto w-full max-w-7xl pb-24">
  <header class="space-y-4 mb-12 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Analysis Report</p>
    <h1 class="text-4xl font-bold tracking-tight text-ink sm:text-5xl">Exploratory Data Analysis</h1>
    <p class="text-lg leading-8 text-ink-2 max-w-4xl">
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
    <div in:fly={{ y: -10, duration: 400, delay: 100 }} class="relative z-20 mb-16 flex flex-wrap items-center gap-4 rounded-2xl border border-border bg-surface/50 p-4 transition-all duration-300 hover:shadow-sm">
      <div class="flex items-center gap-3">
        <label for="sat-select" class="text-xs font-semibold uppercase tracking-wider text-ink-3">Target Profile</label>
        <Select
          id="sat-select"
          bind:value={noradId}
          options={[{ value: 'all', label: 'All Satellites (Global View)' }, ...satellites.map(s => ({ value: s.norad_id.toString(), label: `${s.name} (${s.norad_id})` }))]}
          class="rounded-xl sm:rounded-lg border border-border bg-panel px-3 py-3 sm:py-1.5 min-w-[220px] outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>
      
      <div class="flex items-center gap-3 ml-0 sm:ml-4 border-l-0 sm:border-l border-border pl-0 sm:pl-4">
        <label for="data-limit" class="text-xs font-semibold uppercase tracking-wider text-ink-3">Dataset Size</label>
        <Select
          id="data-limit"
          bind:value={dataLimit}
          options={[{ value: 1000, label: '1,000 frames' }, { value: 5000, label: '5,000 frames' }, { value: 10000, label: '10,000 frames (Full Macro)' }]}
          class="rounded-xl sm:rounded-lg border border-border bg-panel px-3 py-3 sm:py-1.5 min-w-[220px] outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <div class="ml-0 sm:ml-4 border-l-0 sm:border-l border-border pl-0 sm:pl-4">
        <button 
          onclick={fetchTelemetry}
          disabled={loading}
          class="flex items-center justify-center rounded-lg bg-brand px-4 py-1.5 text-sm font-semibold text-white shadow-md shadow-brand/20 transition hover:bg-brand/90 disabled:opacity-50"
        >
          {loading ? 'Fetching...' : 'Fetch Data'}
        </button>
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
      
      <div class="space-y-32">
        
        <!-- SECTION 1: Pipeline Audit & Distributions -->
        <section in:fly={{ y: 20, duration: 500, delay: 200 }} class="grid gap-12 xl:grid-cols-[1fr_2fr] items-start">
          <div class="prose max-w-none xl:sticky xl:top-24">
            <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">1. Data Engineering & Sanity Checks</h2>
            <p>
              Before looking for anomalies, we must make sure the data pipeline works correctly. The backend connects to the <a href="#glossary-mqtt" class="text-brand hover:underline">MQTT broker</a>, stores the data, and converts units to standard formats. We remove impossible data points early (like a battery showing 8V) because they mean there was a communication error, not a real hardware problem.
            </p>
            <div class="my-6 rounded-xl border border-border bg-surface/50 p-5 hover:border-brand/30 transition-colors">
              <h4 class="mt-0 mb-2 text-sm font-semibold uppercase tracking-wider text-ink-3">Unit Conversion</h4>
              <ul class="m-0 space-y-2 text-sm">
                <li class="m-0"><code class="bg-panel px-1 py-0.5 rounded text-xs border border-border">batt_voltage</code>: mV to V (divided by 1000.0)</li>
                <li class="m-0"><code class="bg-panel px-1 py-0.5 rounded text-xs border border-border">batt_current</code>: mA to A (divided by 1000.0)</li>
                <li class="m-0"><code class="bg-panel px-1 py-0.5 rounded text-xs border border-border">temp_panel_z</code>: °C (no change)</li>
              </ul>
            </div>
            <p>
              <strong>Observation:</strong> Clean bell curves or two distinct peaks on the right show that our data parsers are working correctly. Big spikes exactly at 0.0 or extreme outliers usually mean the parser made a mistake.
            </p>
          </div>
          <div class="flex flex-col gap-6">
            <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm hover:shadow-lg transition-shadow duration-300">
              <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                Feature Distributions
              </h3>
              <FeatureDistributionGrid frames={featureFrames} />
            </div>
          </div>
        </section>

        <!-- SECTION 2: Macro Trends & Eclipse Cycle -->
        <section in:fly={{ y: 20, duration: 500, delay: 300 }} class="grid gap-12 xl:grid-cols-[1fr_2fr] items-start">
          <div class="prose max-w-none xl:sticky xl:top-24">
            <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">2. Deep-Dive Exploratory Data Analysis</h2>
            
            <h3>Long-Term Macro Trends</h3>
            <p>
              Over long datasets (e.g., spanning 7+ months), we observe extreme seasonality in satellite thermodynamics and charge cycles. The baselines shift massively over the year due to Beta angle drift and solar proximity.
            </p>

            <h3>The Bimodality Challenge (Day vs. Eclipse)</h3>
            <p>
              The most prominent and predictable cycle for any Low Earth Orbit (LEO) satellite is the <strong>Day/Night (Eclipse) cycle</strong>. 
              By plotting the temperature of the outward-facing solar panels against the battery charging current, we see a strict bimodal distribution representing the two physical states:
            </p>
            <ul>
              <li><strong>Sunlight (Day):</strong> High panel temperatures. Positive battery current (charging).</li>
              <li><strong>Eclipse (Night):</strong> Low panel temperatures. Negative battery current (discharging to run payloads).</li>
            </ul>
            <div class="mt-6 rounded-lg bg-surface/60 p-4 border border-border/50">
              <p class="m-0 text-sm leading-relaxed text-ink-2">
                <strong class="text-ink">Non-Linear Warning:</strong> The transition into eclipse structurally uncouples features. A static threshold logic gate would either trigger 1,000 false positives every orbit, or be so loose that it misses catastrophic component failures. This necessitates non-linear anomaly models.
              </p>
            </div>
          </div>
          <div class="flex flex-col gap-8">
            <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
              <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                Macro-Scale Health (Voltage & Temp)
              </h3>
              <MacroHealthPlot frames={macroFrames} />
            </div>

            <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
              <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                Solar Panel Temp vs. Battery Current
              </h3>
              <div>
                <EclipseScatterPlot frames={eclipseFrames} />
              </div>
              <p class="mt-4 mb-0 text-xs leading-relaxed text-ink-3 border-t border-border/50 pt-4">
                <strong>Diagnostic Heuristic:</strong> Data points falling into the top-left quadrant (positive charging current while panels are freezing cold) violate orbital physics and immediately flag a sensor fault, a decoding alignment error, or an EPS anomaly.
              </p>
            </div>
          </div>
        </section>

        <section class="grid gap-12 xl:grid-cols-2 items-start">
          <div class="prose max-w-none xl:sticky xl:top-24">
            <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">3. Multivariate Feature Correlation</h2>
            <p>
              To build a robust Autoencoder, we must map how the golden features interact across different subsystems. 
              Highly correlated features (e.g., Battery A Voltage and Battery B Voltage) compress efficiently into a lower-dimensional latent space. Conversely, uncorrelated features require independent, weighted representation in the neural network architecture.
            </p>
            <p>
              The heatmap visualizes the Pearson correlation coefficients across the parsed continuous variables. 
              Darker red intersections indicate a strong positive linear relationship, while dark blue indicates inverse relationships.
            </p>
            <div class="mt-6 rounded-lg bg-surface/60 p-4 border border-border/50">
              <p class="m-0 text-sm leading-relaxed text-ink-2">
                <strong class="text-ink">Model Implication:</strong> The Autoencoder exploits these known physical correlations. If a live telemetry frame breaks an established correlation (e.g., Voltage drops but Current stays flat), the reconstruction error spikes, generating an anomaly score.
              </p>
            </div>
          </div>
          <div class="flex flex-col gap-6">
            <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
              <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                Pearson Correlation Matrix
              </h3>
              <div>
                <CorrelationHeatmap frames={featureFrames} />
              </div>
            </div>
          </div>
        </section>

        <!-- SECTION 4: Edge Discontinuity -->
        <section class="grid gap-12 xl:grid-cols-[1fr_2fr] items-start">
          <div class="prose max-w-none xl:sticky xl:top-24">
            <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">4. The Edge Discontinuity</h2>
            <p>
              Unlike normal servers, satellite data is strictly limited by Line-Of-Sight passes over ground stations. The data is entirely disconnected.
            </p>
            <p>
              The histogram to the right strictly visualizes <strong>Intra-Pass</strong> gaps (delays occurring <em>while</em> the satellite is actively overhead). It intentionally filters out the massive ~10-hour blackout periods between orbits. 
            </p>
            <ul>
              <li><strong>The Mode (Peak Frequency):</strong> The vast majority of frames arrive within 0-10 seconds of each other during a solid connection.</li>
              <li><strong>The Median:</strong> Because of secondary clusters of dropped packets or brief physical obstructions, the mathematical median is pushed much higher (often ~40-50s), as indicated by the red dashed line.</li>
            </ul>
            <div class="mt-6 rounded-lg bg-brand/5 p-4 border border-brand/20">
              <p class="m-0 text-sm leading-relaxed text-ink-2">
                <strong class="text-brand">Why LSTMs / Transformers fail here:</strong> Rolling history expires between passes. Attempting to use the data from "10 hours ago" breaks physics predictions. We require <strong>Stateless Ensembles</strong> (evaluating each frame on its own).
              </p>
            </div>
          </div>
          <div class="flex flex-col gap-6">
            <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
              <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
                Intra-Pass Time Gaps
              </h3>
              <div>
                 <TimeGapHistogram {timestamps} />
              </div>
            </div>

            <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
              <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
                <span class="inline-block h-3 w-1 rounded-sm" style="background: #94a3b8"></span>
                Inter-Pass Time Gaps
              </h3>
              <div>
                 <InterPassGapHistogram {timestamps} />
              </div>
            </div>
          </div>
        </section>

        <!-- SECTION 5: Glossary -->
        <section class="border-t border-border pt-12">
          <h2 class="text-xl font-bold tracking-tight text-ink mb-6">Glossary & Abbreviations</h2>
          <dl class="space-y-4 text-sm text-ink-2">
            <div id="glossary-mqtt" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
              <dt class="font-semibold text-ink">MQTT</dt>
              <dd>Message Queuing Telemetry Transport. A lightweight messaging protocol used for connecting remote devices.</dd>
            </div>
            <div id="glossary-leo" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
              <dt class="font-semibold text-ink">LEO</dt>
              <dd>Low Earth Orbit. An orbit relatively close to Earth's surface, typically below 2,000 km.</dd>
            </div>
            <div id="glossary-eclipse" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
              <dt class="font-semibold text-ink">Eclipse Cycle</dt>
              <dd>The period when the satellite passes through the Earth's shadow, meaning it relies on battery power instead of solar panels.</dd>
            </div>
            <div id="glossary-autoencoder" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
              <dt class="font-semibold text-ink">Autoencoder</dt>
              <dd>A machine learning model that learns normal patterns by compressing and recreating data. Used here for anomaly detection.</dd>
            </div>
          </dl>
        </section>

      </div>

    {/if}
  {/if}
</div>
