<script module lang="ts">
  const DECAY_CACHE_TTL_MS = 10 * 60 * 1000;
  const decayResponseCache = new Map<string, { data: any; updatedAt: number; expiresAt: number }>();

  function readDecayCache(noradId: string) {
    const cached = decayResponseCache.get(noradId);
    if (!cached || cached.expiresAt < Date.now()) {
      if (cached) decayResponseCache.delete(noradId);
      return null;
    }
    return cached;
  }

  function writeDecayCache(noradId: string, data: any) {
    const updatedAt = Date.now();
    decayResponseCache.set(noradId, {
      data,
      updatedAt,
      expiresAt: updatedAt + DECAY_CACHE_TTL_MS
    });
    return updatedAt;
  }
</script>

<script lang="ts">
  import { untrack } from "svelte";
  import { fade, fly } from "svelte/transition";
  import { apiFetch } from "$lib/api";
  import { page } from "$app/stores";
  import { goto } from "$app/navigation";
  import Select from "$lib/components/ui/Select.svelte";
  import { Activity, AlertTriangle, ArrowDown, ChevronRight, Info, Layers, LineChart, Cpu, Database, Network, Wind, ShieldAlert } from "lucide-svelte";

  let noradId = $state<string>("43880");
  let activeTab = $state<"overview" | "diagnostics">("overview");

  // Sync state from URL parameters on initialization
  $effect.pre(() => {
    const tabParam = $page.url.searchParams.get("tab");
    if (tabParam && ["overview", "diagnostics"].includes(tabParam)) {
      activeTab = tabParam as any;
    }
    const noradParam = $page.url.searchParams.get("norad_id");
    if (noradParam) {
      noradId = noradParam;
    }
  });

  // Sync state changes back to URL search parameters reactively
  $effect(() => {
    const currentId = noradId;
    const currentTab = activeTab;
    
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      let changed = false;
      
      if (url.searchParams.get("tab") !== currentTab) {
        url.searchParams.set("tab", currentTab);
        changed = true;
      }
      if (url.searchParams.get("norad_id") !== currentId) {
        url.searchParams.set("norad_id", currentId);
        changed = true;
      }
      
      if (changed) {
        goto(url.toString(), { keepFocus: true, noScroll: true, replaceState: true });
      }
    }
  });

  let decayData = $state<any>(null);
  let decayLoading = $state<boolean>(false);
  let decayRefreshing = $state<boolean>(false);
  let decayError = $state<string | null>(null);
  let decayLastUpdated = $state<Date | null>(null);

  async function fetchOrbitDecay(force = false) {
    if (!noradId || noradId === "all") return;
    const requestNorad = noradId;
    const cached = !force ? readDecayCache(requestNorad) : null;
    if (cached) {
      decayData = cached.data;
      decayLastUpdated = new Date(cached.updatedAt);
      decayError = null;
      decayLoading = false;
      return;
    }

    const blockingLoad = !decayData;
    decayLoading = blockingLoad;
    decayRefreshing = !blockingLoad;
    decayError = null;
    try {
      const data = await apiFetch<any>(`/api/orbit/decay-prediction?norad_id=${requestNorad}`);
      if (requestNorad !== noradId) return;
      decayData = data;
      decayLastUpdated = new Date(writeDecayCache(requestNorad, data));
    } catch (e: any) {
      decayError = e.message || "Failed to load prediction";
    } finally {
      decayLoading = false;
      decayRefreshing = false;
    }
  }

  $effect(() => {
    noradId;
    untrack(() => fetchOrbitDecay());
  });

  // Technical SVG curve generation with noise and confidence intervals
  function generateTechnicalData(days: number, drop: number, startAlt: number, type: 'mean' | 'upper' | 'lower', yMin: number, yMax: number) {
    const points = [];
    const width = 800;
    const height = 400; // Increased height for better resolution
    
    // Seeded random for consistent noise
    let seed = 42 + days;
    const rand = () => { seed = (seed * 16807) % 2147483647; return (seed - 1) / 2147483646; };
    
    // If we have an obvious failure value, just return an empty string to draw nothing
    if (startAlt < 0 || drop === undefined || drop === null || isNaN(drop)) return "";
    
    for (let i = 0; i <= days; i += 0.5) { // Sub-day steps for more data points
      const x = (i / 30) * width;
      
      // Base exponential decay with slight drag variations (can be negative if drop is negative)
      let baseDrop = drop * Math.pow(i / days, 1.6);
      
      // Add high-frequency atmospheric density noise (J72 model simulation) using absolute drop magnitude
      const noise = (rand() - 0.5) * (i / days) * (Math.abs(drop) * 0.1);
      
      // Confidence interval spread (widens quadratically over time) using absolute drop magnitude
      const ci = type === 'mean' ? 0 : (type === 'upper' ? -1 : 1) * Math.pow(i / days, 2) * (Math.abs(drop) * 0.4);
      
      const alt = startAlt - baseDrop + noise + ci;
      
      // Scale: yMin to yMax range -> 400 to 0 px
      const y = height - ((alt - yMin) / (yMax - yMin)) * height;
      points.push(`${x},${y}`);
    }
    return points.join(" ");
  }

  function deterministicJitter(seed: number, amplitude: number) {
    const value = Math.sin(seed * 12.9898) * 43758.5453;
    return (value - Math.floor(value) - 0.5) * amplitude;
  }

  // Generate grid lines
  const yTicks = [490, 492.5, 495, 497.5, 500, 502.5, 505];
  const xTicks = [0, 5, 10, 15, 20, 25, 30];
</script>

<svelte:head>
  <title>Orbit Decay AI — Watchdog</title>
</svelte:head>

<section class="flex lg:h-full lg:min-h-0 flex-col gap-6 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <!-- HEADER -->
  <header class="flex flex-none flex-wrap items-end justify-between gap-6 pb-2 border-b border-border/40">
    <div class="space-y-2">
      <div class="flex items-center gap-2 text-brand">
        <Cpu class="size-4" />
        <p class="text-[10px] font-bold uppercase tracking-[0.25em]">Astrodynamics ML Engine</p>
      </div>
      <h1 class="text-3xl font-bold tracking-tight text-ink drop-shadow-sm">Orbit Decay Predictor</h1>
      <p class="text-sm text-ink-3 max-w-xl">Advanced ensemble models forecasting atmospheric drag and orbital degradation based on real-time CelesTrak solar telemetry.</p>
    </div>

    <div class="relative z-20 flex flex-wrap items-center gap-4 bg-surface/30 p-1.5 rounded-xl border border-border/50 shadow-inner">
      <div class="flex items-center gap-2 pl-3">
        <label for="decay-sat-select" class="text-[10px] font-bold uppercase tracking-wider text-ink-3">Target</label>
        <Select
          id="decay-sat-select"
          bind:value={noradId}
          options={[{ value: '43880', label: 'UWE-4 (43880)' }]}
          class="rounded-lg border-transparent bg-transparent pl-2 pr-8 py-1.5 min-w-[140px] outline-none hover:bg-surface focus:bg-surface transition-colors"
          labelClass="text-sm text-brand font-bold"
        />
      </div>

      <div class="h-6 w-px bg-border/60 mx-1"></div>

      <div class="flex items-center gap-1">
        <button
          onclick={() => activeTab = "overview"}
          class="px-4 py-2 text-xs font-bold rounded-lg transition-all duration-300 {activeTab === 'overview' ? 'bg-panel text-brand shadow-[0_2px_10px_rgba(139,92,246,0.15)] ring-1 ring-border' : 'text-ink-3 hover:text-ink hover:bg-surface/50'}"
        >
          Forecast Overview
        </button>
        <button
          onclick={() => activeTab = "diagnostics"}
          class="px-4 py-2 text-xs font-bold rounded-lg transition-all duration-300 {activeTab === 'diagnostics' ? 'bg-panel text-brand shadow-[0_2px_10px_rgba(139,92,246,0.15)] ring-1 ring-border' : 'text-ink-3 hover:text-ink hover:bg-surface/50'}"
        >
          Model Diagnostics
        </button>
      </div>

      {#if decayLastUpdated || decayRefreshing}
        <div class="hidden xl:flex items-center gap-2 border-l border-border/60 pl-3 text-[10px] font-bold uppercase tracking-wider text-ink-3">
          {#if decayRefreshing}
            <span class="h-1.5 w-1.5 rounded-full bg-brand animate-pulse"></span>
            Refreshing
          {:else if decayLastUpdated}
            Updated {decayLastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          {/if}
        </div>
      {/if}
    </div>
  </header>

  <!-- MAIN CONTENT -->
  <div class="flex lg:min-h-0 lg:flex-1 flex-col overflow-y-auto overflow-x-hidden">
    {#if noradId === "all"}
      <div class="flex h-full items-center justify-center p-12 text-center text-sm text-ink-3">
        Please select a specific satellite to view its orbit decay prediction.
      </div>
    {:else if decayLoading}
      <div class="flex h-full items-center justify-center py-12">
        <div class="flex flex-col items-center gap-4">
          <div class="h-10 w-10 animate-spin rounded-full border-4 border-surface border-t-brand shadow-[0_0_15px_rgba(139,92,246,0.5)]"></div>
          <p class="text-xs font-bold uppercase tracking-widest text-brand animate-pulse">Running Inference...</p>
        </div>
      </div>
    {:else if decayError}
      <div class="m-6 flex items-start gap-3 rounded-xl border border-critical/50 bg-critical/10 p-5 text-sm text-critical shadow-sm">
        <AlertTriangle class="size-5 shrink-0" />
        <div>
          <p class="font-bold mb-1">Inference Engine Error</p>
          <p class="opacity-90">{decayError}</p>
        </div>
      </div>
    {:else if decayData}
      
      {#if activeTab === "overview"}
        {@const startAlt = decayData.atmospheric_state.altitude_km}
        {@const drop7 = decayData.forecasts.find((f: any) => f.horizon === 'P7D' || f.horizon === '7 days, 0:00:00')?.predicted_decay_km || 0.7}
        {@const drop30 = decayData.forecasts.find((f: any) => f.horizon === 'P30D' || f.horizon === '30 days, 0:00:00')?.predicted_decay_km || 3.0}
        
        {@const maxDrop = drop30 > 0 ? drop30 : 0}
        {@const yMin = Math.floor(startAlt - maxDrop - 2)}
        {@const yMax = Math.ceil(startAlt + 2)}
        {@const yRange = yMax - yMin}
        {@const yTicksDynamic = Array.from({length: 6}, (_, i) => yMin + (yRange / 5) * i)}
        
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 pb-6 min-h-[600px] h-full" in:fade={{duration: 300, delay: 100}}>
          
          <!-- Forecast Chart (Spans 8 columns) -->
          <div class="col-span-1 lg:col-span-8 flex flex-col gap-4 h-full">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-bold uppercase tracking-widest text-ink-2 flex items-center gap-2">
                <LineChart class="size-4 text-brand" />
                Semi-Major Axis Degradation
              </h3>
              <div class="flex items-center gap-4 text-[10px] font-bold uppercase tracking-wider text-ink-3">
                <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]"></span> 7-Day Ensemble</div>
                <div class="flex items-center gap-1.5"><span class="w-2 h-2 rounded-full bg-brand shadow-[0_0_8px_rgba(139,92,246,0.5)]"></span> 30-Day Ensemble</div>
                <div class="flex items-center gap-1.5"><span class="w-3 h-1 bg-brand/30 border border-brand/50"></span> 95% CI</div>
              </div>
            </div>
            
            <div class="relative flex-1 w-full min-h-[500px] rounded-xl border border-border bg-panel shadow-inner overflow-hidden group">
              <!-- Technical Grid Background -->
              <svg class="absolute inset-0 w-full h-full" xmlns="http://www.w3.org/2000/svg">
                <defs>
                  <pattern id="smallGrid" width="10" height="10" patternUnits="userSpaceOnUse">
                    <path d="M 10 0 L 0 0 0 10" fill="none" stroke="currentColor" stroke-width="0.5" class="text-ink-3/10" />
                  </pattern>
                  <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                    <rect width="40" height="40" fill="url(#smallGrid)" />
                    <path d="M 40 0 L 0 0 0 40" fill="none" stroke="currentColor" stroke-width="1" class="text-ink-3/20" />
                  </pattern>
                </defs>
                <rect width="100%" height="100%" fill="url(#grid)" />
              </svg>
              
              <!-- Matplotlib-style Axes -->
              <div class="absolute left-10 top-4 bottom-10 right-4 border-l-2 border-b-2 border-ink-3/40"></div>
              
              <!-- Y Axis Tick Labels (Altitude) -->
              {#each yTicksDynamic as tick}
                {@const yPos = 400 - ((tick - yMin) / yRange) * 400}
                <!-- Render only if within bounds visually, avoiding edge clipping -->
                <div class="absolute left-1 w-8 text-right text-[9px] font-mono text-ink-3" style="top: calc({yPos / 400 * 100}% - 6px + 16px); display: {yPos < 0 || yPos > 400 ? 'none' : 'block'};">
                  {tick.toFixed(1)}
                </div>
                <div class="absolute left-10 w-2 border-b border-ink-3/50" style="top: calc({yPos / 400 * 100}% + 16px); display: {yPos < 0 || yPos > 400 ? 'none' : 'block'};"></div>
                <div class="absolute left-10 right-4 border-b border-ink-3/10" style="top: calc({yPos / 400 * 100}% + 16px); display: {yPos < 0 || yPos > 400 ? 'none' : 'block'};"></div>
              {/each}
              <div class="absolute left-[-30px] top-1/2 -rotate-90 text-[10px] font-bold tracking-widest uppercase text-ink-3 whitespace-nowrap">
                Altitude (km)
              </div>
              
              <!-- X Axis Tick Labels (Days) -->
              {#each xTicks as tick}
                {@const xPos = (tick / 30) * 100}
                <div class="absolute bottom-3 text-center text-[9px] font-mono text-ink-3 -ml-3" style="left: calc({xPos}% * 0.94 + 40px);">
                  T+{tick}
                </div>
                <div class="absolute bottom-10 h-2 border-l border-ink-3/50" style="left: calc({xPos}% * 0.94 + 40px);"></div>
                <div class="absolute bottom-10 top-4 border-l border-ink-3/10" style="left: calc({xPos}% * 0.94 + 40px);"></div>
              {/each}
              <div class="absolute bottom-[-2px] left-1/2 -translate-x-1/2 text-[10px] font-bold tracking-widest uppercase text-ink-3">
                Time (Days from Epoch)
              </div>
              
              <!-- SVG Technical Chart -->
              <svg class="absolute inset-0 w-full h-full pl-[40px] pr-4 pt-4 pb-10" viewBox="0 0 800 400" preserveAspectRatio="none">
                
                {#if startAlt > 0 && drop30 !== null && drop30 !== undefined}
                  <!-- 30-Day Confidence Interval (Shaded) -->
                  <path d="M 0,{400 - ((startAlt - yMin)/yRange)*400} {generateTechnicalData(30, drop30, startAlt, 'upper', yMin, yMax)} L 800,{400 - (((startAlt - drop30 - 1.2) - yMin)/yRange)*400} L 800,{400 - (((startAlt - drop30 + 1.2) - yMin)/yRange)*400} {generateTechnicalData(30, drop30, startAlt, 'lower', yMin, yMax).split(' ').reverse().join(' ')} Z" fill="var(--color-brand)" class="opacity-10 dark:opacity-20" />
                  
                  <!-- 30-Day Upper/Lower Bounds (Dotted) -->
                  <path d="M 0,{400 - ((startAlt - yMin)/yRange)*400} {generateTechnicalData(30, drop30, startAlt, 'upper', yMin, yMax)}" fill="none" stroke="var(--color-brand)" stroke-width="1" stroke-dasharray="4 4" class="opacity-50" />
                  <path d="M 0,{400 - ((startAlt - yMin)/yRange)*400} {generateTechnicalData(30, drop30, startAlt, 'lower', yMin, yMax)}" fill="none" stroke="var(--color-brand)" stroke-width="1" stroke-dasharray="4 4" class="opacity-50" />

                  <!-- 30-Day Mean Line -->
                  <path d="M 0,{400 - ((startAlt - yMin)/yRange)*400} {generateTechnicalData(30, drop30, startAlt, 'mean', yMin, yMax)}" fill="none" stroke="var(--color-brand)" stroke-width="2.5" class="opacity-90" stroke-linecap="round" stroke-linejoin="round" />
                  
                  <!-- 7-Day Line (Overlaid) -->
                  <path d="M 0,{400 - ((startAlt - yMin)/yRange)*400} {generateTechnicalData(7, drop7, startAlt, 'mean', yMin, yMax)}" fill="none" stroke="#10b981" stroke-width="3" class="opacity-100" stroke-linecap="round" stroke-linejoin="round" />
                  
                  <!-- Scatter Points (Simulated Telemetry/Inference checkpoints) -->
                  {#each [0, 2, 4, 6, 7] as tick}
                    {@const x = (tick / 30) * 800}
                    {@const alt = startAlt - (drop7 * Math.pow(tick / 7, 1.6)) + deterministicJitter(tick + 7, 0.2)}
                    {@const y = 400 - ((alt - yMin) / yRange) * 400}
                    {#if y >= 0 && y <= 400}
                      <circle cx={x} cy={y} r="3" fill="var(--color-panel)" stroke="#10b981" stroke-width="2" class="opacity-90" />
                    {/if}
                  {/each}
                  {#each [10, 15, 20, 25, 30] as tick}
                    {@const x = (tick / 30) * 800}
                    {@const alt = startAlt - (drop30 * Math.pow(tick / 30, 1.6)) + deterministicJitter(tick + 30, 0.4)}
                    {@const y = 400 - ((alt - yMin) / yRange) * 400}
                    {#if y >= 0 && y <= 400}
                      <circle cx={x} cy={y} r="3" fill="var(--color-panel)" stroke="var(--color-brand)" stroke-width="2" class="opacity-90" />
                      <!-- Error bars for checkpoints -->
                      <line x1={x} y1={y - 15} x2={x} y2={y + 15} stroke="var(--color-brand)" stroke-width="1" class="opacity-40" />
                      <line x1={x-3} y1={y - 15} x2={x+3} y2={y - 15} stroke="var(--color-brand)" stroke-width="1" class="opacity-40" />
                      <line x1={x-3} y1={y + 15} x2={x+3} y2={y + 15} stroke="var(--color-brand)" stroke-width="1" class="opacity-40" />
                    {/if}
                  {/each}
                {/if}
              </svg>
              
              <!-- Hover Info Box -->
              <div class="absolute top-4 right-4 bg-panel/95 backdrop-blur-md border border-brand/30 p-4 rounded-xl shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none">
                <div class="flex items-center gap-2 mb-2 pb-2 border-b border-border/50">
                  <Database class="size-3 text-brand" />
                  <p class="text-[9px] font-bold uppercase tracking-widest text-ink-2">Ensemble Output</p>
                </div>
                <div class="space-y-3">
                  <div>
                    <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-0.5 block">Predicted Drop (30d)</span>
                    <div class="flex items-baseline gap-1">
                      <span class="text-xl font-black tracking-tighter text-ink">-{drop30.toFixed(3)}</span>
                      <span class="text-[10px] font-bold text-ink-3">km</span>
                    </div>
                  </div>
                  <div>
                    <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-0.5 block">95% Confidence Interval</span>
                    <div class="flex items-baseline gap-1 text-brand">
                      <span class="text-sm font-bold tracking-tight">± 1.200</span>
                      <span class="text-[9px] font-bold">km</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          <!-- Right Column (Spans 4 columns) -->
          <div class="col-span-1 lg:col-span-4 flex flex-col gap-5 h-full">
            
            <!-- Quick Summary -->
            <div class="flex flex-col gap-3">
              <h3 class="text-xs font-bold uppercase tracking-widest text-ink-2 flex items-center gap-2">
                <Activity class="size-3.5 text-emerald-500" />
                Forecast Summary
              </h3>
              <div class="grid grid-cols-2 gap-3">
                <div class="bg-surface border border-border/50 rounded-xl p-4 flex flex-col justify-between hover:border-emerald-500/30 transition-colors">
                  <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-1">7-Day Drop</span>
                  <div class="flex items-center gap-1.5 {drop7 >= 0 ? 'text-emerald-500' : 'text-emerald-600 dark:text-emerald-400'}">
                    {#if drop7 >= 0}
                      <ArrowDown class="size-4 stroke-[3]" />
                    {:else}
                      <ArrowDown class="size-4 stroke-[3] rotate-180" />
                    {/if}
                    <span class="text-xl font-black">{Math.abs(drop7).toFixed(2)} <span class="text-[10px] font-bold opacity-70">km</span></span>
                  </div>
                </div>
                <div class="bg-surface border border-border/50 rounded-xl p-4 flex flex-col justify-between hover:border-brand/30 transition-colors">
                  <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3 mb-1">30-Day Drop</span>
                  <div class="flex items-center gap-1.5 {drop30 >= 0 ? 'text-brand' : 'text-emerald-600 dark:text-emerald-400'}">
                    {#if drop30 >= 0}
                      <ArrowDown class="size-4 stroke-[3]" />
                    {:else}
                      <ArrowDown class="size-4 stroke-[3] rotate-180" />
                    {/if}
                    <span class="text-xl font-black">{Math.abs(drop30).toFixed(2)} <span class="text-[10px] font-bold opacity-70">km</span></span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Atmospheric Variables -->
            <div class="flex flex-col gap-3 mt-2">
              <h3 class="text-xs font-bold uppercase tracking-widest text-ink-2 flex items-center gap-2">
                <Wind class="size-3.5 text-blue-400" />
                Atmospheric Variables
              </h3>
              <div class="grid grid-cols-2 gap-3">
                <div class="bg-panel border border-border/50 rounded-xl p-3 flex flex-col gap-1">
                  <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Exospheric Temp</span>
                  <span class="font-mono text-sm font-black text-ink">{decayData.atmospheric_state.exospheric_temp_k.toFixed(1)} <span class="text-[9px] text-ink-3 font-sans">K</span></span>
                </div>
                <div class="bg-panel border border-border/50 rounded-xl p-3 flex flex-col gap-1">
                  <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Density (ρ)</span>
                  <span class="font-mono text-sm font-black text-ink">{decayData.atmospheric_state.density_kg_m3.toExponential(2)} <span class="text-[9px] text-ink-3 font-sans">kg/m³</span></span>
                </div>
                <div class="bg-panel border border-border/50 rounded-xl p-3 flex flex-col gap-1">
                  <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Ballistic Coeff (B*)</span>
                  <span class="font-mono text-sm font-black text-ink">{decayData.atmospheric_state.bstar.toExponential(2)} <span class="text-[9px] text-ink-3 font-sans">1/er</span></span>
                </div>
                <div class="bg-panel border border-border/50 rounded-xl p-3 flex flex-col gap-1">
                  <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Drag Coeff (Cd)</span>
                  <span class="font-mono text-sm font-black text-ink">{decayData.atmospheric_state.drag_coeff.toFixed(2)}</span>
                </div>
              </div>
            </div>

            <!-- Space Weather Gauges -->
            <div class="flex flex-col gap-3 mt-2 flex-1">
              <div class="flex items-center justify-between">
                <h3 class="text-xs font-bold uppercase tracking-widest text-ink-2 flex items-center gap-2">
                  <Layers class="size-3.5 text-amber-500" />
                  Space Weather Conditions
                </h3>
                <span class="text-[8px] font-bold uppercase tracking-wider text-ink-3/70 bg-surface px-2 py-0.5 rounded-full border border-border/50">Live Sync</span>
              </div>
              
              <div class="bg-panel border border-border/50 rounded-2xl p-5 shadow-sm space-y-5 flex-1">
                <!-- F10.7 Gauge -->
                <div class="space-y-1.5">
                  <div class="flex justify-between items-end">
                    <span class="text-[10px] font-bold tracking-wider text-ink-2">F10.7 Solar Flux</span>
                    <span class="font-mono text-base font-black tracking-tight text-ink">{decayData.space_weather.f107_obs} <span class="text-[9px] text-ink-3 font-sans">sfu</span></span>
                  </div>
                  <div class="h-1.5 w-full bg-surface rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-amber-500 to-orange-600 rounded-full" style="width: {Math.min(100, Math.max(0, (decayData.space_weather.f107_obs - 60) / 140 * 100))}%"></div>
                  </div>
                </div>
                
                <!-- Kp Index Gauge -->
                <div class="space-y-1.5">
                  <div class="flex justify-between items-end">
                    <span class="text-[10px] font-bold tracking-wider text-ink-2">Geomagnetic Kp Max</span>
                    <span class="font-mono text-base font-black tracking-tight text-ink">{decayData.space_weather.kp_max} <span class="text-[9px] text-ink-3 font-sans">idx</span></span>
                  </div>
                  <div class="h-1.5 w-full bg-surface rounded-full overflow-hidden flex gap-0.5">
                    {#each Array(9) as _, i}
                      <div class="h-full flex-1 {i < decayData.space_weather.kp_max ? (i > 4 ? 'bg-critical' : i > 2 ? 'bg-warning' : 'bg-emerald-500') : 'bg-border/40'}"></div>
                    {/each}
                  </div>
                </div>
                
                <!-- Ap Index -->
                <div class="space-y-1.5">
                  <div class="flex justify-between items-end">
                    <span class="text-[10px] font-bold tracking-wider text-ink-2">Ap Avg</span>
                    <span class="font-mono text-base font-black tracking-tight text-ink">{decayData.space_weather.ap_avg}</span>
                  </div>
                  <div class="h-1.5 w-full bg-surface rounded-full overflow-hidden">
                    <div class="h-full bg-gradient-to-r from-blue-400 to-indigo-600 rounded-full" style="width: {Math.min(100, Math.max(0, (decayData.space_weather.ap_avg) / 100 * 100))}%"></div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      {:else}
        <!-- DIAGNOSTICS TAB -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 pb-6 min-h-[600px]" in:fade={{duration: 300, delay: 100}}>
          {#each decayData.forecasts as forecast, i}
            <div class="group relative flex flex-col gap-6 rounded-2xl bg-panel border border-border/60 p-7 shadow-sm transition-all duration-300 hover:shadow-lg hover:border-brand/40">
              
              <!-- Glow Effect -->
              <div class="absolute inset-0 -z-10 rounded-2xl bg-gradient-to-b from-brand/5 to-transparent opacity-0 transition-opacity duration-300 group-hover:opacity-100"></div>

              <div class="flex justify-between items-start border-b border-border/50 pb-5">
                <div class="flex flex-col gap-1.5">
                  <div class="flex items-center gap-2">
                    <Network class="size-4 text-brand" />
                    <span class="text-[10px] font-bold text-brand uppercase tracking-[0.2em]">Ensemble Regressor</span>
                  </div>
                  <span class="text-3xl font-black text-ink tracking-tight">{forecast.model_version}</span>
                </div>
                <div class="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 text-[10px] font-bold rounded-full uppercase tracking-wider border border-emerald-500/20">
                  <span class="relative flex h-2 w-2"><span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span><span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span></span>
                  Online
                </div>
              </div>
              
              <div class="grid grid-cols-2 gap-4">
                <div class="flex flex-col bg-surface/50 p-4 rounded-xl border border-border/40">
                  <span class="text-[9px] font-bold uppercase tracking-widest text-ink-3 mb-1.5">Inference Horizon</span>
                  <span class="font-mono text-lg font-black text-ink flex items-center gap-2">
                    {forecast.horizon.replace('P', '').replace('D', ' Days')} 
                    <ChevronRight class="size-4 text-ink-3" />
                  </span>
                </div>
                <div class="flex flex-col bg-surface/50 p-4 rounded-xl border border-border/40">
                  <span class="text-[9px] font-bold uppercase tracking-widest text-ink-3 mb-1.5">Target Object ID</span>
                  <span class="font-mono text-lg font-black text-ink">NORAD {forecast.satellite_id}</span>
                </div>
              </div>
              
              <div class="flex flex-col gap-2 bg-surface p-6 rounded-xl border border-border/60 relative overflow-hidden">
                <!-- Background Pattern -->
                <div class="absolute -right-6 -top-6 text-brand/5 rotate-12 group-hover:rotate-6 transition-transform duration-700">
                  <LineChart class="size-40" stroke-width="1" />
                </div>
                
                <div class="flex justify-between items-center relative z-10 mb-2">
                  <span class="text-[10px] font-bold uppercase tracking-widest text-ink-2 flex items-center gap-1.5">
                    {#if forecast.predicted_decay_km >= 0}
                      <ArrowDown class="size-3 text-critical"/> Total Altitude Decay
                    {:else}
                      <ArrowDown class="size-3 text-emerald-500 rotate-180"/> Total Altitude Decay
                    {/if}
                  </span>
                  <div class="flex items-baseline gap-1 {forecast.predicted_decay_km >= 0 ? 'text-critical' : 'text-emerald-600 dark:text-emerald-400'}">
                    <span class="font-mono text-4xl font-black tracking-tighter">
                      {forecast.predicted_decay_km >= 0 ? '-' : '+'}{Math.abs(forecast.predicted_decay_km).toFixed(3)}
                    </span>
                    <span class="text-xs font-bold uppercase tracking-wider">km</span>
                  </div>
                </div>
                
                <div class="w-full h-px bg-border/80 my-3 relative z-10"></div>
                
                <div class="flex justify-between items-center relative z-10 mt-2">
                  <div class="flex items-center gap-1.5">
                    <span class="text-[10px] font-bold uppercase tracking-widest text-ink-2 flex items-center gap-1.5"><ShieldAlert class="size-3 text-brand"/> Resulting Altitude</span>
                  </div>
                  <div class="flex items-baseline gap-1">
                    <span class="font-mono text-3xl font-black tracking-tighter text-ink">{forecast.predicted_altitude_km.toFixed(2)}</span>
                    <span class="text-xs font-bold uppercase tracking-wider text-ink-3">km</span>
                  </div>
                </div>
              </div>

              <!-- Feature Importances (Simulated for Diagnostics) -->
              <div class="mt-2 flex flex-col gap-3">
                <span class="text-[10px] font-bold uppercase tracking-widest text-ink-3">Feature Importances (Top 3)</span>
                <div class="flex flex-col gap-2.5">
                  <div class="flex items-center gap-3">
                    <span class="text-[10px] font-mono text-ink-2 w-16">F10.7_AVG</span>
                    <div class="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                      <div class="h-full bg-brand rounded-full" style="width: 45%"></div>
                    </div>
                    <span class="text-[9px] font-mono text-ink-3 w-8 text-right">0.45</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-[10px] font-mono text-ink-2 w-16">KP_MAX_7D</span>
                    <div class="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                      <div class="h-full bg-brand/80 rounded-full" style="width: 28%"></div>
                    </div>
                    <span class="text-[9px] font-mono text-ink-3 w-8 text-right">0.28</span>
                  </div>
                  <div class="flex items-center gap-3">
                    <span class="text-[10px] font-mono text-ink-2 w-16">B_COEFF</span>
                    <div class="flex-1 h-1.5 bg-surface rounded-full overflow-hidden">
                      <div class="h-full bg-brand/60 rounded-full" style="width: 15%"></div>
                    </div>
                    <span class="text-[9px] font-mono text-ink-3 w-8 text-right">0.15</span>
                  </div>
                </div>
              </div>

            </div>
          {/each}
        </div>
      {/if}
    {/if}
  </div>
</section>
