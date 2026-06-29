<script lang="ts">
  import type { PageData } from './$types';
  import { apiFetch } from '$lib/api';
  import { fly, fade } from 'svelte/transition';
  import type { StationLocation, PassPrediction, TrackPoint } from '$lib/types/api';
  import Select from '$lib/components/ui/Select.svelte';
  import { Search, Loader2, Map as MapIcon, RefreshCw, Satellite, Radio, Crosshair } from 'lucide-svelte';

  import PassTimelinePlot from '$lib/components/charts/PassTimelinePlot.svelte';
  import GroundStationMap from '$lib/components/operations/GroundStationMap.svelte';

  type SatelliteSummary = {
    name: string;
    norad_id: number;
  };

  type LastRun = {
    requestedAt: Date;
    endTime: Date;
    station: StationLocation;
    satelliteLabel: string;
    lookaheadHours: number;
    minElevation: number;
  };

  let { data }: { data: PageData } = $props();

  const stationPresets: StationLocation[] = [
    { id: 'beni_suef', label: 'Beni Suef, Egypt', lat: 29.0661, lon: 31.0994, elevationM: 32.0 },
    { id: 'cairo', label: 'GS-Alpha (Cairo, EG)', lat: 30.0444, lon: 31.2357, elevationM: 23 },
    { id: 'berlin', label: 'GS-Beta (Berlin, DE)', lat: 52.52, lon: 13.405, elevationM: 34 },
    { id: 'tokyo', label: 'GS-Gamma (Tokyo, JP)', lat: 35.6762, lon: 139.6503, elevationM: 40 },
  ];

  const lookaheadOptions = [
    { value: 12, label: 'Next 12 Hours' },
    { value: 24, label: 'Next 24 Hours' },
    { value: 48, label: 'Next 48 Hours' },
    { value: 168, label: 'Next 7 Days' },
  ];

  const elevationOptions = [
    { value: 0, label: '0 deg (Horizon)' },
    { value: 10, label: '10 deg' },
    { value: 20, label: '20 deg' },
    { value: 30, label: '30 deg (Good)' },
    { value: 45, label: '45 deg (Excellent)' },
  ];

  const dateTimeFormatter = new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  let satellites = $derived((data.satellites || []) as SatelliteSummary[]);
  let error = $derived(data.error);

  import { uiState } from '$lib/stores/ui-state.svelte';

  let selectedStationId = $state<string>(uiState.operations.selectedStationId);
  let station = $state<StationLocation>({ ...(stationPresets.find(s => s.id === uiState.operations.selectedStationId) || stationPresets[0]) });
  let selectedNoradId = $state<string>(uiState.operations.selectedNoradId);
  let lookaheadHours = $state<number>(uiState.operations.lookaheadHours);
  let minElevation = $state<number>(uiState.operations.minElevation);
  let loading = $state(false);
  let requestError = $state<string | null>(null);
  let passes = $state<PassPrediction[]>(uiState.operations.passes);
  let selectedPassIndex = $state(uiState.operations.selectedPassIndex);
  let lastRun = $state<LastRun | null>(uiState.operations.lastRun);

  $effect(() => {
    uiState.operations.selectedStationId = selectedStationId;
    uiState.operations.selectedNoradId = selectedNoradId;
    uiState.operations.lookaheadHours = lookaheadHours;
    uiState.operations.minElevation = minElevation;
    uiState.operations.selectedPassIndex = selectedPassIndex;
    uiState.operations.passes = passes;
    uiState.operations.lastRun = lastRun;
  });

  let selectedPass = $derived(passes[selectedPassIndex] ?? null);
  let nextPass = $derived(passes[0] ?? null);
  let bestPass = $derived(
    passes.reduce<PassPrediction | null>(
      (best, pass) => (best === null || pass.max_elevation > best.max_elevation ? pass : best),
      null,
    ),
  );
  let totalContactMinutes = $derived(
    passes.reduce((total, pass) => total + passDurationMinutes(pass), 0),
  );

  function cloneStation(nextStation: StationLocation): StationLocation {
    return {
      ...nextStation,
      elevationM: Number.isFinite(nextStation.elevationM) ? nextStation.elevationM : 0,
    };
  }

  function satelliteLabel(noradId: string) {
    if (noradId === 'all') return 'All Satellites';
    const satellite = satellites.find((candidate) => String(candidate.norad_id) === noradId);
    return satellite ? `${satellite.name} (${satellite.norad_id})` : `NORAD ${noradId}`;
  }

  function selectStation(stationId: string) {
    selectedStationId = stationId;
    const preset = stationPresets.find((candidate) => candidate.id === stationId);
    if (preset) {
      station = cloneStation(preset);
      return;
    }

    station = {
      ...station,
      id: 'custom',
      label: station.label || 'Custom Ground Station',
    };
  }

  function setStationFromMap(nextStation: StationLocation) {
    station = cloneStation(nextStation);
    selectedStationId = nextStation.id && nextStation.id !== 'custom' ? nextStation.id : 'custom';
  }

  function updateStationField(field: 'label' | 'lat' | 'lon' | 'elevationM', value: string | number) {
    const nextStation = {
      ...station,
      id: 'custom',
    };

    if (field === 'label') {
      nextStation.label = String(value);
    } else {
      nextStation[field] = Number(value);
      nextStation.label = station.label || 'Custom Ground Station';
    }

    station = nextStation;
    selectedStationId = 'custom';
  }

  function passDurationMinutes(pass: PassPrediction) {
    return Math.max(0, Math.round((pass.los.getTime() - pass.aos.getTime()) / 60000));
  }

  function formatDateTime(value: Date | undefined) {
    if (!value || Number.isNaN(value.getTime())) return 'Pending';
    return dateTimeFormatter.format(value);
  }

  function formatMinutes(minutes: number) {
    if (minutes < 60) return `${minutes} min`;
    const hours = Math.floor(minutes / 60);
    const remainder = minutes % 60;
    return remainder === 0 ? `${hours} hr` : `${hours} hr ${remainder} min`;
  }

  function mapPass(rawPass: Record<string, unknown>): PassPrediction {
    return {
      satellite: rawPass.satellite as string,
      norad_id: rawPass.norad_id as number,
      max_elevation: rawPass.max_elevation as number,
      direction: rawPass.direction as string,
      aos: new Date(rawPass.aos as string),
      los: new Date(rawPass.los as string),
      track: ((rawPass.track as Record<string, unknown>[]) ?? []).map((point) => ({
        ...point,
        time: point.time ? new Date(point.time as string) : undefined,
      })) as TrackPoint[],
    };
  }

  async function fetchPassPredictions() {
    loading = true;
    requestError = null;
    selectedPassIndex = 0;

    const params = new URLSearchParams({
      lat: String(station.lat),
      lon: String(station.lon),
      elevation_m: String(station.elevationM),
      station_label: station.label || 'Custom Ground Station',
      lookahead_hours: String(lookaheadHours),
      min_elevation: String(minElevation),
      include_tracks: 'true',
    });

    if (selectedNoradId !== 'all') {
      params.set('norad_id', selectedNoradId);
    }

    try {
      const json = await apiFetch<{ passes: Record<string, unknown>[] }>(
        `/api/operations/passes?${params.toString()}`
      );
      passes = (json.passes ?? []).map(mapPass);
      lastRun = {
        requestedAt: new Date(),
        endTime: new Date(Date.now() + lookaheadHours * 60 * 60 * 1000),
        station: cloneStation(station),
        satelliteLabel: satelliteLabel(selectedNoradId),
        lookaheadHours,
        minElevation,
      };
    } catch (err) {
      requestError = err instanceof Error ? err.message : 'Pass calculation failed.';
      passes = [];
    } finally {
      loading = false;
    }
  }
</script>

<svelte:head>
  <title>Operations — Watchdog</title>
</svelte:head>

<section class="flex flex-col lg:h-full lg:min-h-0 gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="flex-none space-y-1">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Operations Center</p>
    <h1 class="text-3xl font-semibold tracking-tight text-ink">Pass Planning Console</h1>
  </div>

  {#if error}
    <div class="flex-none rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <!-- HORIZONTAL CONTROL BAR -->
    <div in:fly={{ y: -20, duration: 400, delay: 100 }} class="relative z-20 flex-none flex flex-wrap items-end gap-4 rounded-[1.25rem] border border-border bg-panel p-4 shadow-panel backdrop-blur transition-shadow hover:shadow-lg duration-300">
      <div class="flex flex-col gap-1.5 flex-1 min-w-0 sm:min-w-[200px]">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Preset Station</span>
        <Select
          id="ops-station-select"
          value={selectedStationId}
          options={[...stationPresets.map(p => ({ value: p.id || '', label: p.label })), { value: 'custom', label: 'Custom Map Location' }]}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 min-w-full outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
          onchange={(val) => selectStation(String(val))}
        />
        <!-- Listen to bind:value updates manually using a deeply reactive $effect or just bind it -->
      </div>

      <div class="flex flex-col gap-1.5 flex-1 min-w-0 sm:min-w-[200px]">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Satellite</span>
        <Select
          id="ops-sat-select"
          bind:value={selectedNoradId}
          options={[{ value: 'all', label: 'All Satellites' }, ...satellites.map(s => ({ value: String(s.norad_id), label: `${s.name} (${s.norad_id})` }))]}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 min-w-full outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <div class="flex flex-col gap-1.5 w-full sm:w-40">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Lookahead</span>
        <Select
          id="ops-lookahead"
          bind:value={lookaheadHours}
          options={lookaheadOptions}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 min-w-full outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <div class="flex flex-col gap-1.5 w-full sm:w-40">
        <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Min Elevation</span>
        <Select
          id="ops-min-elev"
          bind:value={minElevation}
          options={elevationOptions}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 min-w-full outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <button
        type="button"
        class="flex items-center justify-center w-full sm:w-auto rounded-lg bg-brand px-5 py-3.5 text-sm font-semibold text-white shadow-md shadow-brand/20 transition hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-60 mt-2 sm:mt-0"
        disabled={loading}
        onclick={fetchPassPredictions}
      >
        {loading ? 'Calculating...' : 'Calculate Passes'}
      </button>
    </div>

    {#if requestError}
      <div class="flex-none rounded-xl border border-brand/50 bg-brand/10 p-4 text-sm text-brand">
        {requestError}
      </div>
    {/if}

    <!-- MAIN GRID (Fills remaining height) -->
    <div class="lg:flex-1 lg:min-h-0 grid gap-5 lg:grid-cols-[400px_minmax(0,1fr)] xl:grid-cols-[450px_minmax(0,1fr)]">
      
      <!-- LEFT COLUMN: Map & Coordinates -->
      <section in:fly={{ x: -20, duration: 400, delay: 200 }} class="flex flex-col min-h-[300px] rounded-[1.5rem] border border-border bg-panel p-5 shadow-panel backdrop-blur overflow-hidden hover:shadow-lg transition-shadow duration-300">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Station Map</h2>
          <span class="rounded-full border border-border bg-surface px-2 py-0.5 text-[10px] font-medium text-ink-3">
            {selectedStationId === 'custom' ? 'Custom' : 'Preset'}
          </span>
        </div>

        <GroundStationMap
          location={station}
          presets={stationPresets}
          selectedTrack={selectedPass?.track ?? []}
          onLocationChange={setStationFromMap}
        />

        <div class="mt-5 grid gap-3 sm:grid-cols-2">
          <label class="flex flex-col gap-1.5 sm:col-span-2">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Label</span>
            <input
              value={station.label}
              class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 text-base sm:text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('label', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
          <label class="flex flex-col gap-1.5">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Latitude</span>
            <input
              type="number" min="-90" max="90" step="0.0001"
              value={station.lat}
              class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 font-mono text-base sm:text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('lat', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
          <label class="flex flex-col gap-1.5">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Longitude</span>
            <input
              type="number" min="-180" max="180" step="0.0001"
              value={station.lon}
              class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 font-mono text-base sm:text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('lon', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
          <label class="flex flex-col gap-1.5 sm:col-span-2">
            <span class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Elevation (m)</span>
            <input
              type="number" min="-500" max="10000" step="1"
              value={station.elevationM}
              class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 font-mono text-base sm:text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('elevationM', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
        </div>
      </section>

      <!-- RIGHT COLUMN: Pass Results (Timeline & List) -->
      <section in:fly={{ y: 20, duration: 400, delay: 300 }} class="flex flex-col lg:flex-1 min-h-[200px] overflow-hidden rounded-[1.5rem] border border-border bg-panel shadow-panel backdrop-blur hover:shadow-lg transition-shadow duration-300">
        {#if loading}
          <div class="flex flex-1 items-center justify-center">
            <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
          </div>
        {:else if lastRun}
          <!-- Results Header & Stats -->
          <div class="flex-none border-b border-border bg-surface/35">
            <div class="p-4 flex flex-wrap items-start justify-between gap-4 border-b border-border">
              <div>
                <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Calculated Passes</h2>
                <p class="mt-1.5 text-xs text-ink-2">
                  {lastRun.satelliteLabel} | {lastRun.lookaheadHours}hr window
                </p>
              </div>
              <span class="rounded-full border border-border bg-panel px-2.5 py-1 text-[10px] font-medium text-ink-3">
                Updated {formatDateTime(lastRun.requestedAt)}
              </span>
            </div>

            {#if passes.length > 0}
              <div class="grid grid-cols-2 sm:grid-cols-4 divide-x divide-border">
                <div class="p-3 text-center">
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Passes</p>
                  <p class="mt-1 text-lg font-semibold text-ink">{passes.length}</p>
                </div>
                <div class="p-3 text-center">
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Next AOS</p>
                  <p class="mt-1 text-sm font-semibold text-ink">{formatDateTime(nextPass?.aos)}</p>
                </div>
                <div class="p-3 text-center">
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Best Elev</p>
                  <p class="mt-1 text-sm font-semibold text-ink">{bestPass ? `${bestPass.max_elevation}°` : '-'}</p>
                </div>
                <div class="p-3 text-center">
                  <p class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Total Contact</p>
                  <p class="mt-1 text-sm font-semibold text-ink">{formatMinutes(totalContactMinutes)}</p>
                </div>
              </div>
            {/if}
          </div>

          {#if passes.length === 0}
            <div class="flex-1 flex items-center justify-center p-10 text-center text-sm text-ink-3">
              No passes matched this configuration.
            </div>
          {:else}
            <!-- Timeline (Fixed Height) -->
            <div class="flex-none border-b border-border bg-surface/20 p-4">
              <PassTimelinePlot passes={passes} now={lastRun.requestedAt} endTime={lastRun.endTime} />
            </div>

            <!-- Scrollable Pass List -->
            <div class="lg:flex-1 lg:min-h-0 overflow-y-auto max-h-[400px] lg:max-h-none p-4">
              <div class="grid gap-3 xl:grid-cols-2">
                {#each passes as pass, index}
                  <button
                    type="button"
                    in:fly={{ x: -20, duration: 400, delay: Math.min(index * 50, 600) }}
                    class="rounded-xl border p-4 text-left transition-all duration-300 {index === selectedPassIndex ? 'border-brand bg-brand/10 text-ink scale-[1.02] shadow-[0_0_15px_rgba(139,92,246,0.2)]' : 'border-border bg-surface/45 text-ink-2 hover:border-brand/50 hover:bg-surface hover:-translate-y-1 hover:shadow-lg'}"
                    onclick={() => (selectedPassIndex = index)}
                  >
                    <div class="flex items-start justify-between gap-2">
                      <div>
                        <p class="font-semibold text-ink truncate">{pass.satellite}</p>
                        <p class="mt-1 text-[10px] font-medium uppercase tracking-wider text-ink-3">
                          NORAD {pass.norad_id} | {pass.direction}
                        </p>
                      </div>
                      <span class="shrink-0 rounded-lg border border-border bg-panel px-2 py-1 font-mono text-[10px] text-ink">
                        {pass.max_elevation}°
                      </span>
                    </div>
                    <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-ink-3">AOS</p>
                        <p class="mt-0.5 font-medium text-ink">{formatDateTime(pass.aos)}</p>
                      </div>
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-ink-3">LOS</p>
                        <p class="mt-0.5 font-medium text-ink">{formatDateTime(pass.los)}</p>
                      </div>
                      <div>
                        <p class="text-[10px] uppercase tracking-wider text-ink-3">Duration</p>
                        <p class="mt-0.5 font-medium text-ink">{passDurationMinutes(pass)} min</p>
                      </div>
                    </div>
                  </button>
                {/each}
              </div>
            </div>
          {/if}
        {:else}
          <div class="flex-1 flex items-center justify-center p-10 text-center text-sm text-ink-3">
            Set your constraints and calculate passes to view the schedule.
          </div>
        {/if}
      </section>
    </div>
  {/if}
</section>
