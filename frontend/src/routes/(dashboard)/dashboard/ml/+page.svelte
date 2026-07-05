<script lang="ts">
  import type { PageData } from './$types';
  import { page } from '$app/stores';
  import { apiFetch } from '$lib/api';
  import { onMount } from 'svelte';
  import { fly, fade } from 'svelte/transition';
  import type { AnomalyRecord } from '$lib/types/api';
  import Tooltip from '$lib/components/ui/Tooltip.svelte';
  import Select from '$lib/components/ui/Select.svelte';
  import { getFeatureDescription } from '$lib/data/dictionary';
  import AnomalyContributionChart from '$lib/components/charts/AnomalyContributionChart.svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  import { uiState } from '$lib/stores/ui-state.svelte';

  let noradId = $state<string>(uiState.ml.noradId);
  let dataLimit = $state<number>(uiState.ml.dataLimit);
  let loading = $state(false);

  let anomalies = $state<AnomalyRecord[]>(uiState.ml.anomalies);

  $effect(() => {
    uiState.ml.noradId = noradId;
    uiState.ml.dataLimit = dataLimit;
    uiState.ml.anomalies = anomalies;
  });
  let selectedAnomalyId = $state<string | null>(null);

  let mounted = $state(false);
  onMount(() => {
    mounted = true;
  });

  let selectedAnomaly = $derived(
    selectedAnomalyId ? anomalies.find(a => (a.timestamp + a.norad_id) === selectedAnomalyId) : null
  );

  async function fetchAnomalies() {
    loading = true;
    let path = `/api/anomalies/recent?limit=${dataLimit}`;
    if (noradId !== 'all') {
      path += `&norad_id=${noradId}`;
    }
    try {
      const json = await apiFetch<any>(path);
      anomalies = Array.isArray(json) ? json : (json.anomalies || []);
      if (anomalies.length > 0) {
        const queryTs = $page.url.searchParams.get('timestamp');
        const queryNorad = $page.url.searchParams.get('norad_id');
        let matched = null;
        if (queryTs) {
          matched = anomalies.find(a => a.timestamp === queryTs && (!queryNorad || String(a.norad_id) === queryNorad));
        }
        if (matched) {
          selectedAnomalyId = matched.timestamp + matched.norad_id;
        } else {
          selectedAnomalyId = anomalies[0].timestamp + anomalies[0].norad_id;
        }
      } else {
        selectedAnomalyId = null;
      }
    } catch (e) {
      console.error(e);
      anomalies = [];
      selectedAnomalyId = null;
    } finally {
      loading = false;
    }
  }

  // Auto-fetch on mount
  $effect(() => {
    fetchAnomalies();
  });
</script>

<svelte:head>
  <title>ML Interface — Wedjat</title>
</svelte:head>

<section class="flex flex-col tall-lg:flex-1 tall-lg:min-h-0 gap-5 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="flex-none space-y-1">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Live Dashboards</p>
    <h1 class="text-3xl font-semibold tracking-tight text-ink">Inference Inspector</h1>
  </div>

  {#if error}
    <div class="flex-none rounded-xl border border-brand/50 bg-brand/10 p-4 text-sm text-brand">
      {error}
    </div>
  {:else if mounted}
    <!-- Controls -->
    <div in:fly|global={{ y: -20, duration: 400, delay: 100 }} class="relative z-20 flex-none flex flex-wrap items-end gap-4 rounded-[1.25rem] border border-border bg-panel p-4 shadow-sm backdrop-blur hover:shadow-md transition-shadow duration-300">
      <div class="flex flex-col gap-1.5 flex-1 min-w-0 sm:min-w-[200px]">
        <label for="ml-sat-select" class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Satellite Filter</label>
        <Select
          id="ml-sat-select"
          bind:value={noradId}
          options={[{ value: 'all', label: 'All Satellites' }, ...satellites.map(s => ({ value: s.norad_id.toString(), label: `${s.name} (${s.norad_id})` }))]}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 min-w-full outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <div class="flex flex-col gap-1.5 w-full sm:w-40">
        <label for="ml-limit" class="text-[10px] font-semibold uppercase tracking-wider text-ink-3">Fetch Limit</label>
        <Select
          id="ml-limit"
          bind:value={dataLimit}
          options={[{ value: 50, label: 'Last 50 Anomalies' }, { value: 100, label: 'Last 100 Anomalies' }, { value: 200, label: 'Last 200 Anomalies' }]}
          class="rounded-xl sm:rounded-lg border border-border bg-surface px-3 py-3 sm:py-2 min-w-full outline-none transition hover:border-brand"
          labelClass="text-base sm:text-sm text-ink font-medium"
        />
      </div>

      <button 
        onclick={fetchAnomalies}
        disabled={loading}
        class="flex items-center justify-center w-full sm:w-auto rounded-xl sm:rounded-lg bg-brand px-5 py-3.5 sm:py-2 text-base sm:text-sm font-semibold text-white shadow-md shadow-brand/20 transition hover:bg-brand/90 disabled:opacity-50 mt-2 sm:mt-0"
      >
        {loading ? 'Fetching...' : 'Fetch Anomalies'}
      </button>
    </div>

    <!-- Main Grid Layout -->
    <div class="tall-lg:flex-1 tall-lg:min-h-0 grid gap-5 lg:grid-cols-[300px_minmax(0,1fr)] xl:grid-cols-[350px_minmax(0,1fr)]">
      
      <!-- LEFT COLUMN: Anomaly Triage Queue -->
      <div in:fly|global={{ x: -20, duration: 400, delay: 200 }} class="flex flex-col tall-lg:flex-1 tall-lg:min-h-0 w-full h-full rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur hover:shadow-lg transition-shadow duration-300">
        <div class="bg-surface/35 p-4 border-b border-border shrink-0 flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Anomaly Triage Queue</h2>
          <span class="text-xs font-mono text-ink-3">{anomalies.length}</span>
        </div>
        <div class="flex-1 relative min-h-[300px] tall-lg:min-h-0">
          <div class="absolute inset-0 overflow-y-auto p-3 space-y-2">
          {#if loading && anomalies.length === 0}
            <div class="flex h-32 items-center justify-center">
              <div class="h-6 w-6 animate-spin rounded-full border-2 border-surface border-t-brand"></div>
            </div>
          {:else if anomalies.length === 0}
            <div class="p-6 text-center text-sm text-ink-3">
              No anomalies found.
            </div>
          {:else}
            {#each anomalies as anomaly, i}
              {@const frameId = anomaly.timestamp + anomaly.norad_id}
              <button
                in:fly|global={{ x: -10, duration: 300, delay: Math.min(300 + i * 30, 800) }}
                type="button"
                class="w-full text-left rounded-lg border p-3 transition-all duration-300 {selectedAnomalyId === frameId ? 'border-critical bg-critical/10 shadow-[0_0_15px_rgba(244,63,94,0.15)] ring-1 ring-critical/50 scale-[1.02]' : 'border-border bg-surface/50 hover:border-critical/40 hover:bg-surface hover:scale-[1.01]'}"
                onclick={() => selectedAnomalyId = frameId}
              >
                <div class="flex items-center justify-between mb-1.5">
                  <span class="rounded bg-critical/20 text-critical px-1.5 py-0.5 font-mono text-[10px] font-bold border border-critical/20">NORAD {anomaly.norad_id}</span>
                  <span class="text-[10px] text-ink-3">{new Date(anomaly.timestamp).toLocaleTimeString()}</span>
                </div>
                <div class="flex items-baseline justify-between mt-2">
                  <span class="text-sm font-medium text-ink">{new Date(anomaly.timestamp).toLocaleDateString()}</span>
                  <div class="flex flex-col items-end">
                    <span class="text-xs font-semibold text-critical">{anomaly.score.toFixed(3)}</span>
                    <span class="text-[8px] uppercase tracking-wider text-ink-3">Score</span>
                  </div>
                </div>
              </button>
            {/each}
          {/if}
          </div>
        </div>
      </div>

      <!-- RIGHT COLUMN: Inference Inspector -->
      <div in:fly|global={{ y: 20, duration: 400, delay: 300 }} class="flex flex-col tall-lg:flex-1 tall-lg:min-h-0 rounded-[1.25rem] border border-border bg-panel shadow-panel backdrop-blur hover:shadow-lg transition-shadow duration-300">
        <div class="bg-surface/35 p-4 border-b border-border shrink-0 flex items-center justify-between">
          <h2 class="text-sm font-semibold uppercase tracking-[0.16em] text-ink-3">Root Cause Attribution</h2>
          {#if selectedAnomaly}
             <span class="text-xs font-mono text-ink-3">{new Date(selectedAnomaly.timestamp).toLocaleString()}</span>
          {/if}
        </div>
        
        <div class="tall-lg:flex-1 tall-lg:min-h-0 p-5 flex flex-col overflow-y-auto">
          {#if !selectedAnomaly}
            <div class="flex h-full items-center justify-center text-ink-3 text-sm">
              Select an anomaly from the queue to inspect.
            </div>
          {:else}
            <div class="flex flex-col h-full gap-5">
              
              <div class="flex shrink-0 gap-5 flex-col 2xl:flex-row">
                <div class="flex flex-col gap-4 2xl:w-[280px]">
                  <!-- Severity Meter -->
                  <section class="flex flex-col items-center justify-center bg-surface/50 rounded-xl border border-border p-5 shadow-sm h-full">
                     <h3 class="text-[10px] font-semibold uppercase tracking-wider text-ink-3 mb-3">Anomaly Severity</h3>
                     <div class="flex items-end gap-3">
                       <div class="flex flex-col items-center">
                         <span class="text-3xl font-bold tracking-tight text-critical leading-none">{selectedAnomaly.score.toFixed(3)}</span>
                         <span class="text-[9px] uppercase tracking-wider text-ink-3 mt-1.5 text-center">Recon Error</span>
                       </div>
                       <div class="h-8 border-r border-border mx-2"></div>
                       <div class="flex flex-col items-center">
                         <span class="text-xl font-bold tracking-tight text-ink-2 leading-none">{selectedAnomaly.threshold.toFixed(3)}</span>
                         <span class="text-[9px] uppercase tracking-wider text-ink-3 mt-1.5 text-center">Threshold</span>
                       </div>
                     </div>
                  </section>
  

                </div>

                <!-- Contribution Bar Chart -->
                {#if selectedAnomaly.feature_contributions && selectedAnomaly.reconstructed_features}
                  <section class="flex flex-col border border-border bg-surface/30 rounded-xl p-3 shadow-sm flex-1">
                     <h3 class="text-[10px] font-semibold uppercase tracking-wider text-ink-3 mb-1 flex items-center gap-2">
                      <span class="inline-block h-1.5 w-1.5 rounded-full bg-critical"></span>
                      Error Contribution
                    </h3>
                    <div class="h-[160px] w-full">
                      <AnomalyContributionChart 
                        actual={selectedAnomaly.features} 
                        expected={selectedAnomaly.reconstructed_features} 
                        scaledActual={selectedAnomaly.scaled_features || {}} 
                        scaledExpected={selectedAnomaly.scaled_reconstructed_features || {}}
                        activeFeatures={Object.keys(selectedAnomaly.feature_contributions)}
                        height={160}
                      />
                    </div>
                  </section>
                {/if}
              </div>

              <!-- Actual vs Expected Grid -->
              <section class="flex flex-col 2xl:flex-1 2xl:min-h-0 pr-2 pb-2">
                <div class="flex flex-col 2xl:flex-row gap-6">
                  
                  <div class="flex flex-col flex-1 min-w-0">
                    <div class="flex items-center justify-between mb-4">
                      <h3 class="text-xs font-semibold uppercase tracking-wider text-ink-3 flex items-center gap-2">
                        <span class="inline-block h-2 w-2 rounded-full bg-critical"></span>
                        Actual vs. Expected (VAE)
                      </h3>
                      <p class="text-[10px] text-ink-3 max-w-xs text-right">
                        The VAE model flags anomalies when physical relationships break. The feature with the highest delta (Contribution) is the root cause.
                      </p>
                    </div>
    
                    {#if selectedAnomaly.feature_contributions && selectedAnomaly.reconstructed_features}
                      {@const features = Object.entries(selectedAnomaly.feature_contributions).sort((a: any, b: any) => b[1] - a[1])}
                      
                      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
                        {#each features as [key, contribution], i}
                          {@const isRootCause = i === 0}
                          <div class="flex flex-col rounded-xl border {isRootCause ? 'border-critical bg-critical/5 shadow-md shadow-critical/10' : 'border-border bg-surface/50'} p-4 transition-colors">
                            <div class="flex items-center justify-between gap-2 mb-3">
                              <span class="text-[10px] font-semibold uppercase tracking-wider {isRootCause ? 'text-critical' : 'text-ink-3'} truncate">{key}</span>
                              <Tooltip text={getFeatureDescription(key)} align="right" />
                            </div>
                            
                            <div class="flex items-center justify-between mb-2">
                              <div class="flex flex-col">
                                <span class="text-[9px] uppercase tracking-wider text-ink-3">Actual</span>
                                <span class="font-mono text-sm font-medium text-ink mt-0.5">
                                  {Number(selectedAnomaly.features[key]).toFixed(3)}
                                </span>
                              </div>
                              <div class="flex flex-col text-right">
                                <span class="text-[9px] uppercase tracking-wider text-ink-3">Expected</span>
                                <span class="font-mono text-sm font-medium text-ink-2 mt-0.5">
                                  {Number(selectedAnomaly.reconstructed_features[key]).toFixed(3)}
                                </span>
                              </div>
                            </div>
    
                            <div class="mt-2 pt-2 border-t {isRootCause ? 'border-critical/20' : 'border-border/50'} flex items-center justify-between">
                              <span class="text-[9px] uppercase tracking-wider {isRootCause ? 'text-critical' : 'text-ink-3'}">Delta (Contribution)</span>
                              <span class="font-mono text-xs font-bold {isRootCause ? 'text-critical' : 'text-ink'}">
                                {Number(contribution).toFixed(4)}
                              </span>
                            </div>
                          </div>
                        {/each}
                      </div>
                    {:else}
                      <div class="p-6 text-center text-sm text-ink-3 rounded-xl border border-border border-dashed bg-surface/30">
                        Expected feature reconstruction data is not available for this anomaly. 
                        <br><span class="text-xs opacity-70">(Did you restart the backend to clear the cache?)</span>
                      </div>
                    {/if}
                  </div>

                  <!-- Right Sidebar: Context Variables -->
                  {#if selectedAnomaly.feature_contributions && Object.keys(selectedAnomaly.features).some(f => !selectedAnomaly.feature_contributions![f])}
                    {@const contextFeatures = Object.keys(selectedAnomaly.features).filter(f => !selectedAnomaly.feature_contributions!.hasOwnProperty(f))}
                    <div class="flex flex-col 2xl:w-[220px] shrink-0 border-t 2xl:border-t-0 2xl:border-l border-border/50 pt-5 2xl:pt-0 2xl:pl-6">
                      <h4 class="text-[10px] font-semibold uppercase tracking-wider text-ink-3 mb-4">Context Variables (Masked)</h4>
                      <div class="grid grid-cols-1 sm:grid-cols-2 2xl:grid-cols-1 gap-3">
                        {#each contextFeatures as ctxFeature}
                           <div class="flex flex-col gap-1 border-l-2 border-brand/40 pl-3 py-0.5" title={getFeatureDescription(ctxFeature)}>
                             <span class="text-[9px] uppercase tracking-wider text-ink-3 leading-none">{ctxFeature}</span>
                             <span class="font-mono text-sm font-bold text-ink leading-none mt-0.5">{Number(selectedAnomaly.features[ctxFeature]).toFixed(2)}</span>
                           </div>
                        {/each}
                      </div>
                    </div>
                  {/if}

                </div>
              </section>
              
            </div>
          {/if}
        </div>
      </div>
      
    </div>
  {/if}
</section>
