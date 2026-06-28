<script module lang="ts">
  const TRACKER_CACHE_TTL_MS = 5 * 1000; // 5 seconds cache matches backend snapshot TTL
  const trackerCache = new Map<string, { snapshot: any; conjunctions: any; updatedAt: number; expiresAt: number }>();

  function readTrackerCache(noradId: string) {
    const cached = trackerCache.get(noradId);
    if (!cached || cached.expiresAt < Date.now()) {
      if (cached) trackerCache.delete(noradId);
      return null;
    }
    return cached;
  }

  function writeTrackerCache(noradId: string, snapshot: any, conjunctions: any) {
    const updatedAt = Date.now();
    trackerCache.set(noradId, {
      snapshot,
      conjunctions,
      updatedAt,
      expiresAt: updatedAt + TRACKER_CACHE_TTL_MS
    });
    return updatedAt;
  }
</script>

<script lang="ts">
  import { untrack, onDestroy } from "svelte";
  import { fade } from "svelte/transition";
  import { apiFetch } from "$lib/api";
  import Select from "$lib/components/ui/Select.svelte";
  import { 
    Crosshair, AlertTriangle, Map as MapIcon, 
    Activity, Orbit, Target, ShieldAlert, Cpu, Network, LineChart
  } from "lucide-svelte";
  import * as Plot from "@observablehq/plot";
  
  import type { TrackerSnapshot, ConjunctionEvent } from "$lib/types/api";
  
  import GroundStationMap from "$lib/components/operations/GroundStationMap.svelte";
  import ResponsivePlot from "$lib/components/charts/ResponsivePlot.svelte";
  import OrbitalPhaseWidget from "$lib/components/tracker/OrbitalPhaseWidget.svelte";
  import ConjunctionBanner from "$lib/components/tracker/ConjunctionBanner.svelte";
  import TelemetryMatrix from "$lib/components/tracker/TelemetryMatrix.svelte";

  let noradId = $state<string>("43880");
  let activeTab = $state<"mission" | "orbital" | "forecast" | "conjunctions">("mission");

  let snapshotData = $state<TrackerSnapshot | null>(null);
  let conjunctionData = $state<ConjunctionEvent[]>([]);
  let snapshotLoading = $state<boolean>(false);
  let snapshotError = $state<string | null>(null);

  // Fetch logic
  async function fetchTrackerData(isSilentRefresh = false) {
    if (!noradId || noradId === "all") return;
    
    if (!isSilentRefresh) {
      const cached = readTrackerCache(noradId);
      if (cached) {
        snapshotData = cached.snapshot;
        conjunctionData = cached.conjunctions;
        snapshotError = null;
        snapshotLoading = false;
        return;
      }
      snapshotLoading = true;
      snapshotError = null;
    }
    
    try {
      const [snap, conj] = await Promise.all([
        apiFetch<TrackerSnapshot>(`/api/tracker/state?norad_id=${noradId}`),
        apiFetch<{ events: ConjunctionEvent[] }>(`/api/tracker/conjunctions?norad_id=${noradId}`)
      ]);
      snapshotData = snap;
      conjunctionData = conj.events;
      writeTrackerCache(noradId, snap, conj.events);
    } catch (e: any) {
      if (!isSilentRefresh) {
        snapshotError = e.message || "Failed to load tracker data";
      }
    } finally {
      if (!isSilentRefresh) {
        snapshotLoading = false;
      }
    }
  }

  // Auto-refresh when on Mission tab
  let refreshTimer: ReturnType<typeof setInterval>;
  
  $effect(() => {
    // Re-fetch when noradId changes
    noradId;
    untrack(() => fetchTrackerData());
  });
  
  $effect(() => {
    // Manage interval based on active tab
    if (activeTab === "mission") {
      refreshTimer = setInterval(() => {
        untrack(() => fetchTrackerData(true));
      }, 10000); // 10s refresh
    }
    
    return () => {
      if (refreshTimer) clearInterval(refreshTimer);
    };
  });

  onDestroy(() => {
    if (refreshTimer) clearInterval(refreshTimer);
  });

  // Derived plotting data
  let elevationPlotData = $derived(
    snapshotData ? snapshotData.elevation_profile.map((el, i) => ({ t: i - 40, el })) : []
  );
  
  let mapLocation = $derived(
    snapshotData ? {
      label: snapshotData.ground_station.name,
      lat: snapshotData.ground_station.lat,
      lon: snapshotData.ground_station.lon,
      elevationM: snapshotData.ground_station.alt_km * 1000
    } : { label: "N/A", lat: 0, lon: 0, elevationM: 0 }
  );

  let trackPoints = $derived(
    snapshotData ? snapshotData.ground_track.map(p => ({
      lat: p.lat,
      lon: p.lon,
      elevation: p.alt_km,
      time: new Date(new Date(snapshotData!.state.timestamp_utc).getTime() + p.t_offset_min * 60000)
    })) : []
  );

  // Formatting helpers
  const fmt = (num: number, digits: number = 2) => num.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

</script>

<svelte:head>
  <title>AI Tracker — Watchdog</title>
</svelte:head>

<section class="flex lg:h-full lg:min-h-0 flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <!-- HEADER -->
  <header class="flex flex-none flex-wrap items-end justify-between gap-6 pb-2 border-b border-border/40">
    <div class="space-y-2">
      <div class="flex items-center gap-2 text-brand">
        <Crosshair class="size-4" />
        <p class="text-[10px] font-bold uppercase tracking-[0.25em]">Real-time Tracking Engine</p>
      </div>
      <h1 class="text-3xl font-bold tracking-tight text-ink drop-shadow-sm">Mission Tracker</h1>
      <p class="text-sm text-ink-3 max-w-xl">Live orbital mechanics, conjunction risk assessment, and position forecasting via SGP4 propagation.</p>
    </div>

    <div class="relative z-20 flex flex-wrap items-center gap-4 bg-surface/30 p-1.5 rounded-xl border border-border/50 shadow-inner">
      <div class="flex items-center gap-2 pl-3">
        <label for="tracker-sat-select" class="text-[10px] font-bold uppercase tracking-wider text-ink-3">Target</label>
        <Select
          id="tracker-sat-select"
          bind:value={noradId}
          options={[{ value: '43880', label: 'UWE-4 (43880)' }]}
          class="rounded-lg border-transparent bg-transparent pl-2 pr-8 py-1.5 min-w-[140px] outline-none hover:bg-surface focus:bg-surface transition-colors"
          labelClass="text-sm text-brand font-bold"
        />
      </div>

      <div class="h-6 w-px bg-border/60 mx-1 hidden lg:block"></div>

      <div class="flex flex-wrap items-center gap-1 overflow-x-auto max-w-full lg:max-w-none">
        {#each [
          { id: "mission", label: "Mission Control" },
          { id: "orbital", label: "Orbital (COE)" },
          { id: "forecast", label: "Forecast" },
          { id: "conjunctions", label: "Conjunctions" }
        ] as tab}
          <button
            onclick={() => activeTab = tab.id as any}
            class="px-3 py-1.5 text-xs font-bold rounded-lg transition-all duration-300 {activeTab === tab.id ? 'bg-panel text-brand shadow-[0_2px_10px_rgba(139,92,246,0.15)] ring-1 ring-border' : 'text-ink-3 hover:text-ink hover:bg-surface/50'}"
          >
            {tab.label}
          </button>
        {/each}
      </div>
    </div>
  </header>

  <!-- MAIN CONTENT -->
  <div class="flex lg:min-h-0 lg:flex-1 flex-col lg:overflow-hidden overflow-y-auto overflow-x-hidden pb-safe relative">
    {#if noradId === "all"}
      <div class="flex h-full items-center justify-center p-12 text-center text-sm text-ink-3">
        Please select a specific satellite to track.
      </div>
    {:else if snapshotLoading}
      <div class="flex h-full items-center justify-center py-12">
        <div class="flex flex-col items-center gap-4">
          <div class="relative">
            <div class="h-12 w-12 rounded-full border-2 border-surface border-t-brand animate-spin shadow-[0_0_15px_rgba(139,92,246,0.5)]"></div>
            <Crosshair class="size-5 text-brand absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2" />
          </div>
          <p class="text-xs font-bold uppercase tracking-widest text-brand animate-pulse">Computing Mechanics...</p>
        </div>
      </div>
    {:else if snapshotError}
      <div class="m-6 flex items-start gap-3 rounded-xl border border-critical/50 bg-critical/10 p-5 text-sm text-critical shadow-sm">
        <AlertTriangle class="size-5 shrink-0" />
        <div>
          <p class="font-bold mb-1">Tracker Engine Error</p>
          <p class="opacity-90">{snapshotError}</p>
        </div>
      </div>
    {:else if snapshotData}
      
      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- TAB 1: MISSION CONTROL                                 -->
      <!-- ═══════════════════════════════════════════════════════ -->
      {#if activeTab === "mission"}
        <div in:fade={{duration: 200}} class="flex flex-col gap-6">
          <ConjunctionBanner events={conjunctionData} />
          
          <TelemetryMatrix state={snapshotData.state} />
          
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div class="lg:col-span-2 chart-card flex flex-col min-h-[400px]">
              <div class="px-4 py-3 border-b border-border/50 flex justify-between items-center bg-surface/50">
                <span class="chart-card-title flex items-center gap-2"><MapIcon class="size-4" /> Ground Track</span>
                <span class="text-[10px] text-ink-3 uppercase font-bold tracking-widest flex items-center gap-1">
                  <span class="w-1.5 h-1.5 rounded-full bg-ok animate-pulse"></span> Live (-40m to +80m)
                </span>
              </div>
              <div class="flex-1 relative z-0">
                <GroundStationMap location={mapLocation} selectedTrack={trackPoints} />
              </div>
            </div>
            
            <div class="flex flex-col gap-6">
              <div class="chart-card flex flex-col bg-surface/50">
                <div class="px-4 py-3 border-b border-border/50">
                  <span class="chart-card-title flex items-center gap-2"><Orbit class="size-4" /> Phase Radar</span>
                </div>
                <div class="p-4 flex-1 flex items-center justify-center">
                  <OrbitalPhaseWidget coe={snapshotData.state.coe} />
                </div>
              </div>
            </div>
          </div>
        </div>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- TAB 2: ORBITAL (COE) + DIAGNOSTICS                    -->
      <!-- ═══════════════════════════════════════════════════════ -->
      {:else if activeTab === "orbital"}
        {@const coe = snapshotData.state.coe}
        <div in:fade={{duration: 200}} class="flex flex-col gap-4 flex-1 min-h-0 lg:h-full">
          
          <!-- Primary COE row -->
          <div class="grid grid-cols-2 md:grid-cols-5 gap-3 flex-none">
            {#each [
              { label: "Semi-Major Axis (a)", value: fmt(coe.semi_major_axis_km, 2), unit: "km" },
              { label: "Eccentricity (e)", value: fmt(coe.eccentricity, 6), unit: "" },
              { label: "Inclination (i)", value: fmt(coe.inclination_deg, 2), unit: "°" },
              { label: "RAAN (Ω)", value: fmt(coe.raan_deg, 2), unit: "°" },
              { label: "Arg Perigee (ω)", value: fmt(coe.arg_perigee_deg, 2), unit: "°" }
            ] as item}
              <div class="chart-card p-4 bg-surface/30">
                <div class="text-[10px] font-bold uppercase tracking-widest text-ink-3 mb-1.5">{item.label}</div>
                <div class="text-xl font-bold text-ink font-mono">{item.value}{#if item.unit} <span class="text-sm text-ink-3">{item.unit}</span>{/if}</div>
              </div>
            {/each}
          </div>

          <!-- Middle row: 3 equal-width columns -->
          <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:flex-1 lg:min-h-[300px]">
            <!-- Derived Parameters -->
            <div class="chart-card flex flex-col bg-surface/50 h-full">
              <div class="px-4 py-2.5 border-b border-border/50 bg-surface/30">
                <span class="chart-card-title text-xs flex items-center gap-2"><Orbit class="size-4" /> Derived Parameters</span>
              </div>
              <div class="p-4 flex-1 flex flex-col justify-between text-xs font-mono">
                {#each [
                  { label: "True Anomaly (ν)", value: `${fmt(coe.true_anomaly_deg, 2)}°`, highlight: true },
                  { label: "Mean Anomaly (M)", value: `${fmt(coe.mean_anomaly_deg, 2)}°` },
                  { label: "Orbital Period", value: `${fmt(coe.period_min, 2)} min` },
                  { label: "Mean Motion", value: `${fmt(coe.mean_motion_rev_day, 4)} rev/d` },
                  { label: "Apogee Altitude", value: `${fmt(coe.apogee_km, 2)} km` },
                  { label: "Perigee Altitude", value: `${fmt(coe.perigee_km, 2)} km` }
                ] as item}
                  <div class="flex justify-between items-center py-2 border-b border-border/20 last:border-0">
                    <span class="text-ink-3 font-sans font-medium">{item.label}</span>
                    <span class="font-bold {item.highlight ? 'text-brand' : 'text-ink'}">{item.value}</span>
                  </div>
                {/each}
              </div>
            </div>

            <!-- ECI State Vectors -->
            <div class="chart-card flex flex-col bg-surface/50 h-full">
              <div class="px-4 py-2.5 border-b border-border/50 bg-surface/30">
                <span class="chart-card-title text-xs flex items-center gap-2"><Target class="size-4" /> ECI State Vectors</span>
              </div>
              <div class="p-4 flex-1 flex flex-col justify-between text-xs font-mono">
                {#each [
                  { label: "Position X", value: `${fmt(snapshotData.state.pos_eci.x, 2)} km` },
                  { label: "Position Y", value: `${fmt(snapshotData.state.pos_eci.y, 2)} km` },
                  { label: "Position Z", value: `${fmt(snapshotData.state.pos_eci.z, 2)} km` },
                  { label: "Velocity X", value: `${fmt(snapshotData.state.vel_eci.x, 4)} km/s` },
                  { label: "Velocity Y", value: `${fmt(snapshotData.state.vel_eci.y, 4)} km/s` },
                  { label: "Velocity Z", value: `${fmt(snapshotData.state.vel_eci.z, 4)} km/s` },
                  { label: "Drag Coeff (B*)", value: coe.bstar, highlight: true }
                ] as item}
                  <div class="flex justify-between items-center py-1.5 border-b border-border/20 last:border-0">
                    <span class="text-ink-3 font-sans font-medium">{item.label}</span>
                    <span class="font-bold {item.highlight ? 'text-brand' : 'text-ink'}">{item.value}</span>
                  </div>
                {/each}
              </div>
            </div>

            <!-- Phase Radar -->
            <div class="chart-card flex flex-col bg-surface/50 h-full">
              <div class="px-4 py-2.5 border-b border-border/50 bg-surface/30">
                <span class="chart-card-title text-xs flex items-center gap-2"><Orbit class="size-4" /> Phase Radar</span>
              </div>
              <div class="p-4 flex-1 flex items-center justify-center">
                <OrbitalPhaseWidget coe={coe} />
              </div>
            </div>
          </div>

          <!-- Diagnostics footer — compact inline bar -->
          <div class="chart-card p-4 bg-surface/30 flex flex-wrap items-center gap-x-8 gap-y-2 text-xs font-mono flex-none">
            <div class="flex items-center gap-2">
              <Network class="size-3.5 text-ink-3" />
              <span class="text-ink-3 uppercase font-bold tracking-wider">TLE</span>
              <span class="text-ok font-bold">CelesTrak</span>
              <span class="text-ink-3">·</span>
              <span class="text-ink">{snapshotData.tle_age_hr ? snapshotData.tle_age_hr.toFixed(1) : '?'}h old</span>
              <span class="text-ink-3">·</span>
              <span class="text-ink">SGP4/OMM</span>
            </div>
            <div class="flex items-center gap-2">
              <Cpu class="size-3.5 text-ink-3" />
              <span class="text-ink-3 uppercase font-bold tracking-wider">Engine</span>
              <span class="text-ok font-bold">skyfield</span>
              <span class="text-ink-3">·</span>
              <span class="text-ink">WGS84</span>
              <span class="text-ink-3">·</span>
              <span class="text-ok font-bold">1-min sieve</span>
            </div>
          </div>
        </div>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- TAB 3: FORECAST (merged Dynamics + Forecast)           -->
      <!-- ═══════════════════════════════════════════════════════ -->
      {:else if activeTab === "forecast"}
        <div in:fade={{duration: 200}} class="flex flex-col gap-4 flex-1 min-h-0 lg:h-full">
          
          <!-- Top row: Table (left) + Altitude chart (right) -->
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-4 lg:h-[320px] lg:min-h-[320px] flex-none">
            <!-- Compact forecast table -->
            <div class="lg:col-span-7 chart-card !p-0 overflow-hidden flex flex-col h-full">
              <div class="px-6 py-3.5 border-b border-border/50 bg-surface/50">
                <span class="chart-card-title text-xs">7-Point Trajectory Forecast</span>
              </div>
              <div class="overflow-x-auto overflow-y-hidden flex-1">
                <table class="w-full text-left text-xs whitespace-nowrap">
                  <thead class="bg-surface/30 border-b border-border text-[10px] uppercase tracking-widest text-ink-3 sticky top-0 backdrop-blur z-10">
                    <tr>
                      <th class="px-6 py-2.5 font-medium">Horizon</th>
                      <th class="px-6 py-2.5 font-medium">UTC Time</th>
                      <th class="px-6 py-2.5 font-medium text-right">Altitude</th>
                      <th class="px-6 py-2.5 font-medium text-right">Velocity</th>
                      <th class="px-6 py-2.5 font-medium text-right">Anomaly (<span class="normal-case">ν</span>)</th>
                    </tr>
                  </thead>
                  <tbody class="divide-y divide-border/50">
                    {#each snapshotData.forecast as fp}
                      <tr class="hover:bg-surface/30 transition-colors">
                        <td class="px-6 py-2 font-bold text-brand">{fp.label}</td>
                        <td class="px-6 py-2 font-mono text-ink-2">{new Date(fp.timestamp_utc).toISOString().replace('T', ' ').substring(0, 19)}</td>
                        <td class="px-6 py-2 text-right font-mono font-bold">{fp.altitude_km.toFixed(2)} <span class="text-ink-3">km</span></td>
                        <td class="px-6 py-2 text-right font-mono">{fp.velocity_km_s.toFixed(4)} <span class="text-ink-3">km/s</span></td>
                        <td class="px-6 py-2 text-right font-mono">{fp.true_anomaly_deg.toFixed(1)}°</td>
                      </tr>
                    {/each}
                  </tbody>
                </table>
              </div>
            </div>

            <!-- Altitude forecast chart -->
            <div class="lg:col-span-5 chart-card flex flex-col h-full">
              <div class="px-4 py-3 border-b border-border/50 bg-surface/50">
                <span class="chart-card-title text-xs flex items-center gap-2"><LineChart class="size-3.5" /> Altitude Profile</span>
              </div>
              <div class="p-2 flex-1 min-h-0 flex items-center justify-center">
                <ResponsivePlot 
                  height={240}
                  options={{
                    marginLeft: 45,
                    marginBottom: 20,
                    marginTop: 15,
                    y: { grid: true, label: "Altitude (km)" },
                    x: { type: "point", label: "Horizon", domain: snapshotData.forecast.map((d: any) => d.label) },
                    marks: [
                      // @ts-ignore
                      Plot.line(snapshotData.forecast, { x: "label", y: "altitude_km", stroke: "var(--color-brand)", strokeWidth: 2 }),
                      // @ts-ignore
                      Plot.dot(snapshotData.forecast, { x: "label", y: "altitude_km", fill: "var(--color-panel)", stroke: "var(--color-brand)", strokeWidth: 2, r: 3 }),
                      // @ts-ignore
                      Plot.text(snapshotData.forecast, { x: "label", y: "altitude_km", text: (d: any) => `${d.altitude_km.toFixed(0)}`, dy: -10, fill: "var(--color-ink-2)", fontSize: 9 })
                    ]
                  }} 
                />
              </div>
            </div>
          </div>
          
          <!-- Bottom row: Elevation profile + Sky track / GS Status -->
          <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:flex-1 lg:min-h-[270px]">
            <div class="chart-card flex flex-col h-full">
              <div class="px-4 py-3 border-b border-border/50 bg-surface/50">
                <span class="chart-card-title text-xs flex items-center gap-2"><Target class="size-3.5" /> GS Elevation Profile</span>
              </div>
              <div class="p-2 flex-1 min-h-0 flex items-center justify-center">
                <ResponsivePlot 
                  height={200}
                  options={{
                    marginLeft: 45,
                    marginBottom: 35,
                    marginTop: 10,
                    y: { grid: true, label: "Elevation (°)", domain: [-90, 90] },
                    x: { label: "Time to TCA (min)", domain: [-40, 80] },
                    marks: [
                      // @ts-ignore
                      Plot.ruleY([0], { stroke: "var(--color-critical)", strokeWidth: 1, strokeDasharray: "4 4" }),
                      // @ts-ignore
                      Plot.line(elevationPlotData, { x: "t", y: "el", stroke: "var(--color-brand)", strokeWidth: 2 }),
                      // @ts-ignore
                      Plot.areaY(elevationPlotData, { x: "t", y: "el", fill: "var(--color-brand)", fillOpacity: 0.1 }),
                      // @ts-ignore
                      Plot.dot(elevationPlotData.filter((d: any) => d.t === 0), { x: "t", y: "el", fill: "var(--color-ink)", r: 3 })
                    ]
                  }} 
                />
              </div>
            </div>

            {#if snapshotData.azimuth_profile.some((_, i) => snapshotData!.elevation_profile[i] > 0)}
              <div class="chart-card flex flex-col h-full">
                <div class="px-4 py-3 border-b border-border/50 bg-surface/50">
                  <span class="chart-card-title text-xs flex items-center gap-2"><Activity class="size-3.5" /> Sky Track (Visible Pass)</span>
                </div>
                <div class="p-2 flex-1 min-h-0 flex items-center justify-center">
                  <ResponsivePlot 
                    height={200}
                    options={{
                      marginLeft: 45,
                      marginBottom: 35,
                      marginTop: 10,
                      y: { grid: true, label: "Elevation (°)", domain: [0, 90] },
                      x: { grid: true, label: "Azimuth (°)", domain: [0, 360], tickFormat: (d: any) => `${d}°` },
                      marks: [
                        // @ts-ignore
                        Plot.line(
                          snapshotData.azimuth_profile.map((az: number, i: number) => ({ az, el: snapshotData!.elevation_profile[i] })).filter((d: any) => d.el > 0),
                          { x: "az", y: "el", stroke: "var(--color-ok)", strokeWidth: 2 }
                        ),
                        // @ts-ignore
                        Plot.dot(
                          [{ az: snapshotData.state.ground_station.azimuth_deg, el: snapshotData.state.ground_station.elevation_deg }].filter((d: any) => d.el > 0),
                          { x: "az", y: "el", fill: "var(--color-ink)", r: 4.5 }
                        )
                      ]
                    }} 
                  />
                </div>
              </div>
            {:else}
              <div class="chart-card flex flex-col h-full bg-surface/30 justify-between">
                <div class="px-4 py-3 border-b border-border/50 bg-surface/50">
                  <span class="chart-card-title text-xs flex items-center gap-2"><Network class="size-3.5" /> GS Acquisition Link</span>
                </div>
                <div class="p-6 flex-1 flex flex-col justify-between text-xs">
                  <!-- Ground Station Info & Status -->
                  <div class="flex justify-between items-start">
                    <div class="space-y-1">
                      <div class="text-sm font-bold text-ink">{snapshotData.ground_station.name}</div>
                      <div class="text-[10px] font-mono text-ink-3">
                        {snapshotData.ground_station.lat.toFixed(4)}°N · {snapshotData.ground_station.lon.toFixed(4)}°E · {snapshotData.ground_station.alt_km.toFixed(0)}m
                      </div>
                    </div>
                    <span class="flex items-center gap-1.5 px-2.5 py-1 bg-amber-500/10 text-amber-500 text-[9px] font-bold rounded-full uppercase tracking-wider border border-amber-500/20">
                      <span class="relative flex h-1.5 w-1.5"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span><span class="relative inline-flex rounded-full h-1.5 w-1.5 bg-amber-500"></span></span>
                      Awaiting Pass
                    </span>
                  </div>

                  <div class="grid grid-cols-3 gap-2 border-t border-b border-border/30 py-4 my-2 font-mono text-center">
                    <div>
                      <div class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-0.5">GS Elevation</div>
                      <div class="text-sm font-bold text-ink">{snapshotData.state.ground_station.elevation_deg.toFixed(1)}°</div>
                    </div>
                    <div>
                      <div class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-0.5">Range</div>
                      <div class="text-sm font-bold text-ink">{snapshotData.state.ground_station.range_km.toFixed(0)} km</div>
                    </div>
                    <div>
                      <div class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-0.5">Doppler Shift</div>
                      <div class="text-sm font-bold text-brand">{snapshotData.state.ground_station.doppler_khz.toFixed(2)} kHz</div>
                    </div>
                  </div>

                  <div class="text-ink-3 text-[10px] leading-relaxed">
                    The satellite is currently below the local horizon. The next telemetry acquisition window will open when the elevation angle rises above 0.0° relative to the station horizon mask.
                  </div>
                </div>
              </div>
            {/if}
          </div>
        </div>

      <!-- ═══════════════════════════════════════════════════════ -->
      <!-- TAB 4: CONJUNCTIONS                                    -->
      <!-- ═══════════════════════════════════════════════════════ -->
      {:else if activeTab === "conjunctions"}
        <div in:fade={{duration: 200}} class="chart-card overflow-hidden flex flex-col h-full">
          <div class="px-4 py-3 border-b border-border/50 bg-surface/50 flex justify-between items-center">
            <span class="chart-card-title flex items-center gap-2"><ShieldAlert class="size-4" /> Threat Catalog</span>
            <span class="px-2.5 py-0.5 rounded-full bg-surface text-[10px] font-bold tracking-widest uppercase border border-border">
              {conjunctionData.length} Events Loaded
            </span>
          </div>
          
          <div class="overflow-x-auto flex-1">
            <table class="w-full text-left text-sm whitespace-nowrap min-w-[800px]">
              <thead class="bg-surface/30 border-b border-border text-xs uppercase tracking-widest text-ink-3 sticky top-0 backdrop-blur z-10">
                <tr>
                  <th class="px-4 py-3 font-medium">Risk Level</th>
                  <th class="px-4 py-3 font-medium">Secondary Object</th>
                  <th class="px-4 py-3 font-medium">Time of Closest Approach (UTC)</th>
                  <th class="px-4 py-3 font-medium text-right">Miss Distance</th>
                  <th class="px-4 py-3 font-medium text-right">Rel Velocity</th>
                  <th class="px-4 py-3 font-medium text-right">Probability</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-border/50">
                {#if conjunctionData.length === 0}
                  <tr>
                    <td colspan="6" class="px-4 py-12 text-center text-ink-3 italic">
                      No conjunction threats detected in the lookahead window.
                    </td>
                  </tr>
                {/if}
                {#each conjunctionData as event}
                  <tr class="hover:bg-surface/30 transition-colors">
                    <td class="px-4 py-3">
                      <span class="px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider
                        {event.risk_level === 'CRITICAL' ? 'bg-critical/20 text-critical border border-critical/50' : 
                         event.risk_level === 'HIGH' ? 'bg-warning/20 text-warning border border-warning/50' : 
                         event.risk_level === 'WARNING' ? 'bg-brand/20 text-brand border border-brand/50' : 
                         'bg-ok/10 text-ok border border-ok/30'}">
                        {event.risk_level}
                      </span>
                    </td>
                    <td class="px-4 py-3 font-mono">
                      <span class="text-ink">{event.secondary_name}</span> 
                      <span class="text-ink-3 text-xs">({event.secondary_norad})</span>
                    </td>
                    <td class="px-4 py-3 text-ink-2">{new Date(event.tca).toISOString().replace('T', ' ').substring(0, 19)}</td>
                    <td class="px-4 py-3 text-right font-mono font-bold {event.miss_distance_km < 10 ? 'text-warning' : ''}">
                      {event.miss_distance_km.toFixed(2)} km
                    </td>
                    <td class="px-4 py-3 text-right font-mono text-ink-2">{event.relative_velocity_km_s.toFixed(2)} km/s</td>
                    <td class="px-4 py-3 text-right font-mono">{event.probability.toExponential(2)}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        </div>
      {/if}

    {/if}
  </div>
</section>
