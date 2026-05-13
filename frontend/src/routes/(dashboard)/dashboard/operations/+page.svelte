<script lang="ts">
  import type { PageData } from './$types';
  import { env } from '$env/dynamic/public';

  import PassTimelinePlot from '$lib/components/charts/PassTimelinePlot.svelte';
  import GroundStationMap from '$lib/components/operations/GroundStationMap.svelte';

  type SatelliteSummary = {
    name: string;
    norad_id: number;
  };

  type StationLocation = {
    id?: string;
    label: string;
    lat: number;
    lon: number;
    elevationM: number;
  };

  type TrackPoint = {
    time?: string | Date;
    lat: number;
    lon: number;
    elevation?: number;
    azimuth?: number;
    range_km?: number;
  };

  type PassPrediction = {
    satellite: string;
    norad_id: number;
    aos: Date;
    los: Date;
    max_elevation: number;
    direction: string;
    track?: TrackPoint[];
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
    { id: 'cairo', label: 'GS-Alpha (Cairo, EG)', lat: 29.0661, lon: 31.0994, elevationM: 32 },
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

  let station = $state<StationLocation>({ ...stationPresets[0] });
  let selectedStationId = $state<string>('cairo');
  let selectedNoradId = $state<string>('all');
  let lookaheadHours = $state<number>(24);
  let minElevation = $state<number>(10);
  let loading = $state(false);
  let requestError = $state<string | null>(null);
  let passes = $state<PassPrediction[]>([]);
  let selectedPassIndex = $state(0);
  let lastRun = $state<LastRun | null>(null);

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

  function mapPass(rawPass: any): PassPrediction {
    return {
      ...rawPass,
      aos: new Date(rawPass.aos),
      los: new Date(rawPass.los),
      track: (rawPass.track ?? []).map((point: any) => ({
        ...point,
        time: point.time ? new Date(point.time) : undefined,
      })),
    };
  }

  async function fetchPassPredictions() {
    loading = true;
    requestError = null;
    selectedPassIndex = 0;

    const apiUrl =
      typeof window !== 'undefined' ? env.PUBLIC_API_URL || 'http://127.0.0.1:8000' : 'http://backend:8000';
    const params = new URLSearchParams({
      lookahead_hours: String(lookaheadHours),
      min_elevation: String(minElevation),
      include_tracks: 'true',
    });

    if (selectedNoradId !== 'all') {
      params.set('norad_id', selectedNoradId);
    }

    if (selectedStationId !== 'custom' && station.id) {
      params.set('ground_station', station.id);
    } else {
      params.set('lat', String(station.lat));
      params.set('lon', String(station.lon));
      params.set('elevation_m', String(station.elevationM));
      params.set('station_label', station.label || 'Custom Ground Station');
    }

    try {
      const res = await fetch(`${apiUrl}/api/operations/passes?${params.toString()}`);
      if (!res.ok) {
        const payload = await res.json().catch(() => null);
        throw new Error(payload?.detail || `Pass calculation failed with HTTP ${res.status}`);
      }

      const json = await res.json();
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

<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Operations Center</p>
    <h1 class="text-4xl font-semibold tracking-tight text-ink">Pass Planning Console</h1>
    <p class="max-w-3xl text-base leading-7 text-ink-2">
      Choose a ground station from the map, set the pass constraints, then run a Skyfield prediction on demand.
    </p>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <div class="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <section class="rounded-[1.5rem] border border-border bg-panel p-5 shadow-panel backdrop-blur lg:p-6">
        <div class="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Ground Station Map</h2>
            <p class="mt-2 text-sm leading-6 text-ink-2">
              Click the map for a custom station or choose an existing station marker.
            </p>
          </div>
          <span class="rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-ink-3">
            {selectedStationId === 'custom' ? 'Custom Coordinates' : 'Preset Station'}
          </span>
        </div>

        <GroundStationMap
          location={station}
          presets={stationPresets}
          selectedTrack={selectedPass?.track ?? []}
          onLocationChange={setStationFromMap}
        />

        <div class="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Label</span>
            <input
              value={station.label}
              class="rounded-xl border border-border bg-surface px-3 py-2 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('label', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Latitude</span>
            <input
              type="number"
              min="-90"
              max="90"
              step="0.0001"
              value={station.lat}
              class="rounded-xl border border-border bg-surface px-3 py-2 font-mono text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('lat', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Longitude</span>
            <input
              type="number"
              min="-180"
              max="180"
              step="0.0001"
              value={station.lon}
              class="rounded-xl border border-border bg-surface px-3 py-2 font-mono text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('lon', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Elevation (m)</span>
            <input
              type="number"
              min="-500"
              max="10000"
              step="1"
              value={station.elevationM}
              class="rounded-xl border border-border bg-surface px-3 py-2 font-mono text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              oninput={(event) => updateStationField('elevationM', (event.currentTarget as HTMLInputElement).value)}
            />
          </label>
        </div>
      </section>

      <aside class="rounded-[1.5rem] border border-border bg-panel p-5 shadow-panel backdrop-blur lg:p-6">
        <div class="space-y-4">
          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Preset</span>
            <select
              value={selectedStationId}
              class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
              onchange={(event) => selectStation((event.currentTarget as HTMLSelectElement).value)}
            >
              {#each stationPresets as preset}
                <option value={preset.id}>{preset.label}</option>
              {/each}
              <option value="custom">Custom Map Location</option>
            </select>
          </label>

          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Satellite</span>
            <select
              bind:value={selectedNoradId}
              class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
            >
              <option value="all">All Satellites</option>
              {#each satellites as satellite}
                <option value={String(satellite.norad_id)}>{satellite.name} ({satellite.norad_id})</option>
              {/each}
            </select>
          </label>

          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Lookahead Window</span>
            <select
              bind:value={lookaheadHours}
              class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
            >
              {#each lookaheadOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <label class="flex flex-col gap-2">
            <span class="text-xs font-semibold uppercase tracking-wider text-ink-3">Minimum Elevation</span>
            <select
              bind:value={minElevation}
              class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand"
            >
              {#each elevationOptions as option}
                <option value={option.value}>{option.label}</option>
              {/each}
            </select>
          </label>

          <button
            type="button"
            class="flex w-full items-center justify-center rounded-xl bg-brand px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-brand/20 transition hover:bg-brand/90 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={loading}
            onclick={fetchPassPredictions}
          >
            {loading ? 'Calculating...' : 'Calculate Passes'}
          </button>
        </div>
      </aside>
    </div>

    {#if requestError}
      <div class="rounded-xl border border-brand/50 bg-brand/10 p-5 text-sm text-brand">
        {requestError}
      </div>
    {/if}

    <section class="overflow-hidden rounded-[1.5rem] border border-border bg-panel shadow-panel backdrop-blur">
      <div class="border-b border-border bg-surface/35 p-5 lg:p-6">
        <div class="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Calculated Passes</h2>
            {#if lastRun}
              <p class="mt-2 text-sm text-ink-2">
                {lastRun.station.label} | {lastRun.satelliteLabel} | {lastRun.lookaheadHours} hr | {lastRun.minElevation} deg minimum
              </p>
            {:else}
              <p class="mt-2 text-sm text-ink-2">No calculation has been run for the current planning setup.</p>
            {/if}
          </div>
          {#if lastRun}
            <span class="rounded-full border border-border bg-panel px-3 py-1 text-xs font-medium text-ink-3">
              Updated {formatDateTime(lastRun.requestedAt)}
            </span>
          {/if}
        </div>
      </div>

      {#if loading}
        <div class="flex h-48 items-center justify-center">
          <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
        </div>
      {:else if !lastRun}
        <div class="p-10 text-center text-sm text-ink-3">
          Select a location and press Calculate Passes to generate the schedule.
        </div>
      {:else if passes.length === 0}
        <div class="p-10 text-center text-sm text-ink-3">
          No passes matched this station, satellite filter, time window, and elevation limit.
        </div>
      {:else}
        <div class="grid gap-0 border-b border-border md:grid-cols-4">
          <div class="border-b border-border p-5 md:border-b-0 md:border-r">
            <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Passes</p>
            <p class="mt-2 text-2xl font-semibold text-ink">{passes.length}</p>
          </div>
          <div class="border-b border-border p-5 md:border-b-0 md:border-r">
            <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Next AOS</p>
            <p class="mt-2 text-lg font-semibold text-ink">{formatDateTime(nextPass?.aos)}</p>
          </div>
          <div class="border-b border-border p-5 md:border-b-0 md:border-r">
            <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Best Elevation</p>
            <p class="mt-2 text-lg font-semibold text-ink">
              {bestPass ? `${bestPass.max_elevation} deg` : 'None'}
            </p>
          </div>
          <div class="p-5">
            <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Total Contact</p>
            <p class="mt-2 text-lg font-semibold text-ink">{formatMinutes(totalContactMinutes)}</p>
          </div>
        </div>

        <div class="border-b border-border bg-surface/20 p-5 lg:p-6">
          <PassTimelinePlot passes={passes} now={lastRun.requestedAt} endTime={lastRun.endTime} />
        </div>

        <div class="grid gap-3 p-5 lg:grid-cols-2 lg:p-6">
          {#each passes as pass, index}
            <button
              type="button"
              class="rounded-xl border p-4 text-left transition {index === selectedPassIndex ? 'border-brand bg-brand/10 text-ink' : 'border-border bg-surface/45 text-ink-2 hover:border-brand/50 hover:bg-surface'}"
              onclick={() => (selectedPassIndex = index)}
            >
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="font-semibold text-ink">{pass.satellite}</p>
                  <p class="mt-1 text-xs font-medium uppercase tracking-wider text-ink-3">
                    NORAD {pass.norad_id} | {pass.direction}
                  </p>
                </div>
                <span class="rounded-lg border border-border bg-panel px-2.5 py-1 font-mono text-xs text-ink">
                  {pass.max_elevation} deg
                </span>
              </div>
              <div class="mt-4 grid grid-cols-3 gap-3 text-sm">
                <div>
                  <p class="text-xs uppercase tracking-wider text-ink-3">AOS</p>
                  <p class="mt-1 font-medium text-ink">{formatDateTime(pass.aos)}</p>
                </div>
                <div>
                  <p class="text-xs uppercase tracking-wider text-ink-3">LOS</p>
                  <p class="mt-1 font-medium text-ink">{formatDateTime(pass.los)}</p>
                </div>
                <div>
                  <p class="text-xs uppercase tracking-wider text-ink-3">Duration</p>
                  <p class="mt-1 font-medium text-ink">{passDurationMinutes(pass)} min</p>
                </div>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</section>
