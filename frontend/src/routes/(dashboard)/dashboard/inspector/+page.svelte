<script lang="ts">
  import { env } from '$env/dynamic/public';
  import type { PageData } from './$types';
  import { untrack } from 'svelte';
  import Tooltip from '$lib/components/ui/Tooltip.svelte';
  import { getFeatureDescription } from '$lib/data/dictionary';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let noradId = $state<string>('all');
  let dataLimit = $state<number>(50);
  let loading = $state(false);

  let telemetryFrames = $state<any[]>([]);
  let selectedFrameId = $state<string | null>(null);

  let selectedFrame = $derived(
    selectedFrameId ? telemetryFrames.find(f => (f.timestamp + f.norad_id) === selectedFrameId) : null
  );

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
        if (telemetryFrames.length > 0) {
            selectedFrameId = telemetryFrames[0].timestamp + telemetryFrames[0].norad_id;
        } else {
            selectedFrameId = null;
        }
      } else {
        console.error(`Failed to fetch telemetry: ${res.status}`);
        telemetryFrames = [];
        selectedFrameId = null;
      }
    } catch (e) {
      console.error(e);
      telemetryFrames = [];
      selectedFrameId = null;
    } finally {
      loading = false;
    }
  }

  function formatHex(hexStr: string | null | undefined): string {
    if (!hexStr) return "Raw frame data not available.";
    // Split into pairs of 2 characters and join with space
    return hexStr.match(/.{1,2}/g)?.join(' ') || hexStr;
  }
</script>

<section class="flex flex-col h-full min-h-0 gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="flex-none space-y-1">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Deep Dive</p>
    <h1 class="text-3xl font-semibold tracking-tight text-ink">Telemetry Inspector</h1>
  </div>

  {#if error}
    <div class="flex-none rounded-xl border border-brand/50 bg-brand/10 p-4 text-sm text-brand">
      {error}
    </div>
  {:else}
    <!-- Controls -->
    <div class="flex-none flex flex-wrap items-end gap-4 rounded-[1.25rem] border border-border bg-panel p-4 shadow-panel backdrop-blur">
      <div class="flex flex-col gap-1.5 flex-1 min-w-[200px]">
        <label for="inspector-sat-select" class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Satellite Filter</label>
        <select id="inspector-sat-select" bind:value={noradId} class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-ink outline-none transition hover:border-brand">
          <option value="all">All Satellites</option>
          {#each satellites as sat}
            <option value={sat.norad_id.toString()}>{sat.name} ({sat.norad_id})</option>
          {/each}
        </select>
      </div>

      <div class="flex flex-col gap-1.5 w-40">
        <label for="inspector-limit" class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Fetch Limit</label>
        <select id="inspector-limit" bind:value={dataLimit} class="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-ink outline-none transition hover:border-brand">
          <option value={50}>50 frames</option>
          <option value={100}>100 frames</option>
          <option value={500}>500 frames</option>
        </select>
      </div>

      <button 
        onclick={fetchTelemetry}
        disabled={loading}
        class="flex items-center justify-center rounded-lg bg-brand px-5 py-2 text-sm font-semibold text-white shadow-md shadow-brand/20 transition hover:bg-brand/90 disabled:opacity-50"
      >
        {loading ? 'Fetching...' : 'Fetch Data'}
      </button>
    </div>

    <!-- Main Grid Layout -->
    <div class="flex-1 min-h-0 grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[350px_minmax(0,1fr)]">
      
      <!-- LEFT COLUMN: Packet List -->
      <div class="flex flex-col flex-1 min-h-0 rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur">
        <div class="bg-surface/35 p-4 border-b border-border shrink-0 flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Recent Packets</h2>
          <span class="text-xs font-mono text-ink-3">{telemetryFrames.length}</span>
        </div>
        
        <div class="flex-1 min-h-0 overflow-y-auto p-3 space-y-2">
          {#if loading && telemetryFrames.length === 0}
            <div class="flex h-32 items-center justify-center">
              <div class="h-6 w-6 animate-spin rounded-full border-2 border-surface border-t-brand"></div>
            </div>
          {:else if telemetryFrames.length === 0}
            <div class="p-6 text-center text-sm text-ink-3">
              No data fetched.
            </div>
          {:else}
            {#each telemetryFrames as frame}
              {@const frameId = frame.timestamp + frame.norad_id}
              <button
                type="button"
                class="w-full text-left rounded-lg border p-3 transition-all {selectedFrameId === frameId ? 'border-brand bg-brand/5 shadow-sm' : 'border-border bg-surface/50 hover:border-brand/40'}"
                onclick={() => selectedFrameId = frameId}
              >
                <div class="flex items-center justify-between mb-1.5">
                  <span class="rounded bg-panel px-1.5 py-0.5 font-mono text-[10px] font-bold text-ink-3 border border-border">NORAD {frame.norad_id}</span>
                  {#if frame.quality?.frame_is_complete}
                    <span class="text-[10px] text-emerald-500 font-medium">Complete</span>
                  {:else}
                    <span class="text-[10px] text-brand font-medium">Partial</span>
                  {/if}
                </div>
                <p class="font-medium text-sm text-ink">{new Date(frame.timestamp).toLocaleString()}</p>
              </button>
            {/each}
          {/if}
        </div>
      </div>

      <!-- RIGHT COLUMN: Inspector Details -->
      <div class="flex flex-col flex-1 min-h-0 rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur">
        <div class="bg-surface/35 p-4 border-b border-border shrink-0">
          <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Frame Details</h2>
        </div>
        
        <div class="flex-1 min-h-0 p-5 flex flex-col">
          {#if !selectedFrame}
            <div class="flex h-full items-center justify-center text-ink-3 text-sm">
              Select a packet from the list to inspect.
            </div>
          {:else}
            <div class="flex flex-col h-full min-h-0 gap-5">
              
              <!-- Raw Hex Section (Top, Fixed Height) -->
              <section class="flex-none">
                <h3 class="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-3 flex items-center gap-2">
                  <span class="inline-block h-2 w-2 rounded-full bg-brand"></span>
                  Raw Payload (Hex)
                </h3>
                <div class="rounded-xl border border-border bg-surface p-4 font-mono text-sm tracking-wider text-ink-2 break-all whitespace-pre-wrap leading-loose select-all shadow-sm">
                  {formatHex(selectedFrame.raw_frame)}
                </div>
              </section>

              <!-- Bottom Split (Scrollable Columns) -->
              <div class="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-2 gap-6 mt-2">
                
                <!-- Kaitai Quality Section -->
                <section class="flex flex-col min-h-0">
                  <h3 class="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-3 flex items-center gap-2">
                    <span class="inline-block h-2 w-2 rounded-full bg-amber-500"></span>
                    Kaitai Decoded State
                  </h3>
                  <div class="flex-1 min-h-0 overflow-y-auto rounded-xl border border-border bg-surface p-5 shadow-sm">
                    {#if selectedFrame.quality}
                      <table class="w-full text-left text-sm">
                        <tbody class="divide-y divide-border/50">
                          {#each Object.entries(selectedFrame.quality) as [key, value]}
                            <tr class="transition-colors hover:bg-panel/50">
                              <td class="py-3 pr-4 font-mono text-xs text-ink-3 w-1/3">
                                <div class="flex items-center gap-1.5">
                                  {key}
                                  <Tooltip text={getFeatureDescription(key)} align="left" />
                                </div>
                              </td>
                              <td class="py-3 font-mono text-xs text-ink break-words">{JSON.stringify(value)}</td>
                            </tr>
                          {/each}
                        </tbody>
                      </table>
                    {:else}
                      <p class="text-sm text-ink-3">No quality metadata available.</p>
                    {/if}
                  </div>
                </section>

                <!-- Golden Features Section -->
                <section class="flex flex-col min-h-0">
                  <h3 class="text-xs font-semibold uppercase tracking-wider text-ink-3 mb-3 flex items-center gap-2">
                    <span class="inline-block h-2 w-2 rounded-full bg-emerald-500"></span>
                    Normalized Golden Features
                  </h3>
                  <div class="flex-1 min-h-0 overflow-y-auto rounded-xl border border-border bg-surface p-4 shadow-sm">
                    {#if selectedFrame.features}
                      <div class="grid grid-cols-2 gap-y-3 gap-x-3">
                        {#each Object.entries(selectedFrame.features) as [key, value], i}
                          <div class="flex flex-col rounded-lg border border-border/50 bg-panel/50 px-3 py-2 transition-colors hover:border-brand/30">
                            <div class="flex items-center justify-between gap-2">
                              <span class="text-[9px] font-semibold uppercase tracking-wider text-ink-3 truncate">{key}</span>
                              <Tooltip text={getFeatureDescription(key)} align={i % 2 !== 0 ? 'right' : 'left'} />
                            </div>
                            <span class="font-mono text-sm font-medium text-ink mt-0.5">
                              {value !== null ? Number(value).toFixed(4) : "null"}
                            </span>
                          </div>
                        {/each}
                      </div>
                    {:else}
                      <p class="text-sm text-ink-3">No normalized features available.</p>
                    {/if}
                  </div>
                </section>

              </div>
            </div>
          {/if}
        </div>
      </div>
      
    </div>
  {/if}
</section>
