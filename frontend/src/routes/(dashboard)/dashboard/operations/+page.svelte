<script lang="ts">
  import type { PageData } from './$types';
  import { env } from '$env/dynamic/public';
  import { untrack } from 'svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let groundStation = $state<string>('cairo');
  let lookaheadHours = $state<number>(24);
  let minElevation = $state<number>(10);
  
  let loading = $state(false);
  let passes = $state<any[]>([]);

  async function fetchPassPredictions() {
    loading = true;
    const apiUrl = env.PUBLIC_API_URL || 'http://127.0.0.1:8000';
    let url = `${apiUrl}/api/operations/passes?ground_station=${groundStation}&lookahead_hours=${lookaheadHours}&min_elevation=${minElevation}`;
    
    try {
      const res = await fetch(url);
      if (res.ok) {
        const json = await res.json();
        passes = json.passes.map((p: any) => ({
          ...p,
          aos: new Date(p.aos),
          los: new Date(p.los),
        }));
      } else {
        console.error("Failed to fetch passes");
      }
    } catch (e) {
      console.error(e);
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    groundStation; lookaheadHours; minElevation;
    untrack(() => fetchPassPredictions());
  });
</script>

<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Operations Center</p>
    <h1 class="text-4xl font-semibold tracking-tight text-ink">Pass Predictions & Timeline</h1>
    <p class="max-w-3xl text-base leading-7 text-ink-2">
      Simulated skyfield orbital prediction and pass scheduling for operational active tracking.
    </p>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else}
    <div class="flex flex-wrap items-end gap-6 rounded-[1.5rem] border border-border bg-panel p-6 shadow-panel backdrop-blur lg:p-8">
      <div class="flex flex-col gap-2">
        <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Ground Station</label>
        <select bind:value={groundStation} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
          <option value="cairo">GS-Alpha (Cairo, EG)</option>
          <option value="berlin">GS-Beta (Berlin, DE)</option>
          <option value="tokyo">GS-Gamma (Tokyo, JP)</option>
        </select>
      </div>

      <div class="flex flex-col gap-2">
        <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Lookahead Window</label>
        <select bind:value={lookaheadHours} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
          <option value={12}>Next 12 Hours</option>
          <option value={24}>Next 24 Hours</option>
          <option value={48}>Next 48 Hours</option>
          <option value={168}>Next 7 Days</option>
        </select>
      </div>

      <div class="flex flex-col gap-2">
        <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Min Elevation (deg)</label>
        <select bind:value={minElevation} class="rounded-xl border border-border bg-surface px-4 py-2.5 text-sm text-ink outline-none transition hover:border-brand focus:border-brand focus:ring-1 focus:ring-brand">
          <option value={0}>0° (Horizon)</option>
          <option value={10}>10°</option>
          <option value={20}>20°</option>
          <option value={30}>30° (Good)</option>
          <option value={45}>45° (Excellent)</option>
        </select>
      </div>
    </div>

    <!-- Pass Timeline -->
    <div class="space-y-4">
      <h2 class="text-lg font-medium tracking-tight text-ink">Upcoming Passes</h2>
      <div class="overflow-hidden rounded-[1.5rem] border border-border bg-panel shadow-panel backdrop-blur">
        {#if loading}
          <div class="flex h-40 items-center justify-center">
            <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
          </div>
        {:else if passes.length === 0}
          <div class="p-12 text-center text-ink-3">
            <p>No passes predicted matching the current parameters.</p>
          </div>
        {:else}
          {@const now = new Date()}
          {@const endTime = new Date(now.getTime() + lookaheadHours * 3600 * 1000)}
          {@const durationMs = lookaheadHours * 3600 * 1000}
          {@const uniqueSats = [...new Set(passes.map(p => p.satellite))]}
          
          <!-- Timeline Gantt Chart -->
          <div class="border-b border-border bg-surface/30 p-6 lg:p-8">
            <h3 class="text-sm font-semibold uppercase tracking-wider text-ink-3 mb-6">Pass Schedule Timeline</h3>
            
            <div class="relative mt-2">
              <!-- Grid Background -->
              <div class="absolute inset-0 flex flex-col justify-between pointer-events-none">
                 {#each uniqueSats as _}
                   <div class="flex-1 border-b border-border/50"></div>
                 {/each}
              </div>
              
              <!-- Satellites / Rows -->
              <div class="relative space-y-4">
                 {#each uniqueSats as sat, rowIdx}
                   <div class="relative h-8 w-full flex items-center">
                      <!-- Sat Name -->
                      <div class="absolute -left-2 top-1/2 -translate-y-1/2 -translate-x-full text-xs font-medium text-ink-2 mr-4 whitespace-nowrap">{sat}</div>
                      <!-- Passes -->
                      {#each passes.filter(p => p.satellite === sat) as pass}
                         {@const leftPct = Math.max(0, (pass.aos.getTime() - now.getTime()) / durationMs) * 100}
                         {@const widthPct = Math.min(100 - leftPct, (pass.los.getTime() - pass.aos.getTime()) / durationMs * 100)}
                         {#if leftPct < 100 && widthPct > 0}
                           <div 
                             class="absolute top-1 bottom-1 rounded-md bg-brand shadow-[0_0_8px_rgba(177,33,66,0.6)] opacity-90 transition-all hover:opacity-100 hover:scale-105 cursor-pointer flex items-center justify-center overflow-hidden"
                             style="left: {leftPct}%; width: {widthPct}%; min-width: 4px;"
                             title="{pass.satellite} pass: {pass.aos.toLocaleTimeString()} - {pass.los.toLocaleTimeString()} (Elev: {pass.max_elevation}°)"
                           >
                           </div>
                         {/if}
                      {/each}
                   </div>
                 {/each}
              </div>
              
              <!-- Time Axis -->
              <div class="mt-4 flex justify-between text-[0.6rem] font-medium tracking-wider text-ink-3 uppercase border-t border-border pt-2">
                 <span>Now</span>
                 <span>+{Math.floor(lookaheadHours/2)}h</span>
                 <span>+{lookaheadHours}h</span>
              </div>
            </div>
          </div>

          <table class="w-full text-left text-sm">
            <thead class="border-b border-border bg-surface/50 text-ink-3">
              <tr>
                <th class="px-6 py-4 font-medium">Satellite</th>
                <th class="px-6 py-4 font-medium">AOS (Acquisition)</th>
                <th class="px-6 py-4 font-medium">LOS (Loss)</th>
                <th class="px-6 py-4 font-medium">Duration</th>
                <th class="px-6 py-4 font-medium text-right">Max Elev</th>
                <th class="px-6 py-4 font-medium text-right">Direction</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-border">
              {#each passes as pass}
                <tr class="transition-colors hover:bg-surface/80">
                  <td class="px-6 py-4">
                    <span class="font-semibold text-ink">{pass.satellite}</span>
                    <span class="ml-2 rounded bg-surface px-1.5 py-0.5 text-[0.65rem] font-bold tracking-widest text-brand">ID {pass.norad_id}</span>
                  </td>
                  <td class="px-6 py-4 text-ink-2">
                    <div class="flex flex-col">
                      <span class="font-medium text-ink">{pass.aos.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      <span class="text-xs text-ink-3">{pass.aos.toLocaleDateString()}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4 text-ink-2">
                    <div class="flex flex-col">
                      <span class="font-medium text-ink">{pass.los.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                      <span class="text-xs text-ink-3">{pass.los.toLocaleDateString()}</span>
                    </div>
                  </td>
                  <td class="px-6 py-4 text-ink-2">
                    {Math.round((pass.los.getTime() - pass.aos.getTime()) / 60000)} min
                  </td>
                  <td class="px-6 py-4 text-right">
                    <span class="inline-flex items-center gap-1 rounded-lg border border-border bg-surface px-2.5 py-1 font-mono text-xs font-medium text-ink">
                      {pass.max_elevation}°
                    </span>
                  </td>
                  <td class="px-6 py-4 text-right text-xs font-semibold uppercase tracking-widest text-ink-3">
                    {pass.direction}
                  </td>
                </tr>
              {/each}
            </tbody>
          </table>
        {/if}
      </div>
    </div>
  {/if}
</section>
