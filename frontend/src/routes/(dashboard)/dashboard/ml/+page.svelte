<script lang="ts">
  import type { PageData } from './$types';
  import { env } from '$env/dynamic/public';
  import { untrack } from 'svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let selectedSatId = $state<string>('');
  let sensitivityData = $state<any>(null);
  let loadingSensitivity = $state(false);

  $effect(() => {
    if (satellites.length > 0 && !selectedSatId) {
      selectedSatId = satellites[0].norad_id.toString();
    }
  });

  let selectedSat = $derived(satellites.find((s: any) => s.norad_id.toString() === selectedSatId) || null);

  async function fetchSensitivity(noradId: string) {
    if (!noradId) return;
    loadingSensitivity = true;
    const apiUrl = env.PUBLIC_API_URL || 'http://127.0.0.1:8000';
    try {
      const res = await fetch(`${apiUrl}/api/ml/sensitivity?norad_id=${noradId}`);
      if (res.ok) {
        sensitivityData = await res.json();
      } else {
        sensitivityData = null;
      }
    } catch (e) {
      console.error(e);
      sensitivityData = null;
    } finally {
      loadingSensitivity = false;
    }
  }

  $effect(() => {
    const id = selectedSatId;
    if (id) {
      untrack(() => fetchSensitivity(id));
    }
  });
</script>

<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Machine Learning</p>
    <h1 class="text-4xl font-semibold tracking-tight text-ink">ML Lab & Artifacts</h1>
    <p class="max-w-3xl text-base leading-7 text-ink-2">
      Inspect live VAE model artifacts, health checks, and feature contracts for operational satellite profiles.
    </p>
  </div>

  {#if error}
    <div class="rounded-xl border border-brand/50 bg-brand/10 p-6 text-brand">
      <h2 class="text-lg font-semibold">Connection Error</h2>
      <p class="mt-2 text-sm">{error}</p>
    </div>
  {:else if satellites.length === 0}
    <div class="rounded-[1.5rem] border border-border border-dashed p-12 text-center text-ink-3">
      <p>No model artifacts found in the system.</p>
    </div>
  {:else}
    <div class="grid gap-8 lg:grid-cols-4">
      <!-- Sidebar / Select -->
      <div class="flex flex-col gap-4 lg:col-span-1">
        <label class="text-xs font-semibold uppercase tracking-wider text-ink-3">Active Models</label>
        <div class="flex flex-col gap-2">
          {#each satellites as sat}
            <button 
              onclick={() => selectedSatId = sat.norad_id.toString()}
              class="flex w-full items-center justify-between rounded-xl border p-4 text-left transition-all {selectedSatId === sat.norad_id.toString() ? 'border-brand bg-brand/10 shadow-[0_0_12px_rgba(177,33,66,0.2)] text-ink' : 'border-border bg-panel text-ink-2 hover:border-brand/50 hover:bg-surface'}"
            >
              <div>
                <p class="font-semibold">{sat.name}</p>
                <p class="text-xs opacity-75">NORAD {sat.norad_id}</p>
              </div>
              <div class="h-2 w-2 rounded-full {sat.model?.status === 'ready' ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.5)]'}"></div>
            </button>
          {/each}
        </div>
      </div>

      <!-- Main Panel -->
      <div class="lg:col-span-3">
        {#if selectedSat}
          <div class="overflow-hidden rounded-[1.75rem] border border-border bg-panel shadow-panel backdrop-blur transition-all">
            <!-- Header -->
            <div class="border-b border-border bg-surface/50 p-6 lg:p-8">
              <div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div>
                  <h2 class="text-2xl font-semibold tracking-tight text-ink">{selectedSat.name} Autoencoder</h2>
                  <p class="mt-1 flex items-center gap-2 text-sm text-ink-3">
                    Status: 
                    <span class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium {selectedSat.model.status === 'ready' ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400' : 'bg-amber-500/10 text-amber-600 dark:text-amber-400'}">
                      {selectedSat.model.status}
                    </span>
                  </p>
                </div>
                {#if selectedSat.model.error}
                  <div class="rounded-xl border border-brand/20 bg-brand/10 p-3 text-xs text-brand max-w-xs">
                    {selectedSat.model.error}
                  </div>
                {/if}
              </div>
            </div>

            <div class="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-4">
              <!-- Stats block -->
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Inference Mode</p>
                <p class="mt-2 text-xl font-medium tracking-tight text-ink capitalize">{selectedSat.model.inference_mode || 'Unknown'}</p>
              </div>
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Threshold</p>
                <p class="mt-2 text-xl font-medium tracking-tight text-brand">{selectedSat.model.threshold?.toFixed(3) || 'N/A'}</p>
              </div>
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Contract Ver</p>
                <p class="mt-2 text-xl font-medium tracking-tight text-ink">v{selectedSat.model.feature_contract_version || '?'}</p>
              </div>
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Artifact Ver</p>
                <p class="mt-2 text-xl font-medium tracking-tight text-ink">v{selectedSat.model.artifact_version || '?'}</p>
              </div>
            </div>

            <div class="p-6 lg:p-8">
              <div class="space-y-6">
                <div>
                  <h3 class="text-sm font-semibold uppercase tracking-wider text-ink-3">Feature Engineering Contract</h3>
                  <div class="mt-3 flex flex-wrap gap-2">
                    {#each selectedSat.model.feature_names || [] as feature}
                      <span class="rounded-lg border border-border bg-surface px-3 py-1 text-xs font-medium text-ink-2 shadow-sm transition hover:border-brand hover:text-ink">{feature}</span>
                    {/each}
                    {#if !selectedSat.model.feature_names || selectedSat.model.feature_names.length === 0}
                      <span class="text-sm text-ink-3">No features defined.</span>
                    {/if}
                  </div>
                </div>

                <div class="pt-6 border-t border-border">
                  <h3 class="text-sm font-semibold uppercase tracking-wider text-ink-3">Dataset Provenance (Chronological Split)</h3>
                  <div class="mt-4 grid gap-4 sm:grid-cols-3">
                    <div class="rounded-xl border border-border bg-surface p-4">
                      <p class="text-xs font-medium text-ink-2 mb-1">Training Set</p>
                      <p class="text-2xl font-semibold tracking-tight text-ink">{selectedSat.model.train_rows?.toLocaleString() || 0}</p>
                      <p class="text-[0.65rem] text-ink-3 mt-2">{selectedSat.model.train_start ? new Date(selectedSat.model.train_start).toLocaleDateString() : '-'} →</p>
                    </div>
                    <div class="rounded-xl border border-border bg-surface p-4">
                      <p class="text-xs font-medium text-ink-2 mb-1">Validation Set</p>
                      <p class="text-2xl font-semibold tracking-tight text-ink">{selectedSat.model.validation_rows?.toLocaleString() || 0}</p>
                      <p class="text-[0.65rem] text-ink-3 mt-2">{selectedSat.model.validation_start ? new Date(selectedSat.model.validation_start).toLocaleDateString() : '-'} →</p>
                    </div>
                    <div class="rounded-xl border border-border bg-surface p-4">
                      <p class="text-xs font-medium text-ink-2 mb-1">Testing Set</p>
                      <p class="text-2xl font-semibold tracking-tight text-ink">{selectedSat.model.test_rows?.toLocaleString() || 0}</p>
                      <p class="text-[0.65rem] text-ink-3 mt-2">{selectedSat.model.test_start ? new Date(selectedSat.model.test_start).toLocaleDateString() : '-'} →</p>
                    </div>
                  </div>
                </div>

                <div class="pt-6 border-t border-border">
                  <h3 class="text-sm font-semibold uppercase tracking-wider text-ink-3">Sensitivity Sweep & ROC</h3>
                  {#if loadingSensitivity && !sensitivityData}
                    <div class="mt-4 flex h-40 items-center justify-center rounded-xl border border-border bg-surface/50">
                      <div class="h-8 w-8 animate-spin rounded-full border-4 border-surface border-t-brand"></div>
                    </div>
                  {:else if sensitivityData}
                    {@const currIdx = sensitivityData.sweep.findIndex((s: any) => Math.abs(s.threshold - sensitivityData.current_threshold) < 0.02)}
                    <div class="mt-4 grid gap-6 md:grid-cols-2">
                      <!-- ROC Curve approximation -->
                      <div class="rounded-xl border border-border bg-surface p-6">
                        <p class="text-xs font-semibold text-ink-2 mb-6 text-center tracking-wide uppercase">Receiver Operating Characteristic</p>
                        <div class="relative h-48 w-full max-w-[200px] mx-auto border-l-2 border-b-2 border-border bg-panel">
                          <div class="absolute inset-0 bg-gradient-to-tr from-transparent to-brand/10 pointer-events-none"></div>
                          <!-- Diagonal random guessing line -->
                          <svg class="absolute inset-0 h-full w-full pointer-events-none opacity-40" viewBox="0 0 100 100" preserveAspectRatio="none">
                            <line x1="0" y1="100" x2="100" y2="0" stroke="currentColor" stroke-width="1.5" stroke-dasharray="4" class="text-ink-3" />
                          </svg>
                          <!-- Plot points -->
                          <svg class="absolute inset-0 h-full w-full" viewBox="0 0 100 100" preserveAspectRatio="none">
                            <polyline
                              points={sensitivityData.roc.map((p: any) => `${p.fpr * 100},${100 - p.tpr * 100}`).join(' ')}
                              fill="none"
                              stroke="var(--color-brand)"
                              stroke-width="2.5"
                              stroke-linejoin="round"
                              class="text-brand shadow-[0_0_8px_rgba(177,33,66,0.8)]"
                            />
                            <!-- Current Threshold marker -->
                            {#if currIdx !== -1 && sensitivityData.roc[currIdx]}
                              <circle 
                                cx={sensitivityData.roc[currIdx].fpr * 100} 
                                cy={100 - sensitivityData.roc[currIdx].tpr * 100} 
                                r="4" 
                                fill="var(--color-brand)"
                                class="shadow-[0_0_12px_rgba(177,33,66,1)]"
                              />
                            {/if}
                          </svg>
                          <div class="absolute -left-10 top-1/2 -translate-y-1/2 -rotate-90 text-[0.65rem] font-medium tracking-wider text-ink-3 uppercase">TPR</div>
                          <div class="absolute -bottom-8 left-1/2 -translate-x-1/2 text-[0.65rem] font-medium tracking-wider text-ink-3 uppercase">FPR</div>
                        </div>
                      </div>

                      <!-- Sensitivity Curve -->
                      <div class="rounded-xl border border-border bg-surface p-6 flex flex-col justify-end">
                        <p class="text-xs font-semibold text-ink-2 mb-6 text-center tracking-wide uppercase">F1 Score vs Threshold</p>
                        <div class="relative h-48 w-full border-b-2 border-border mt-auto">
                          <div class="flex h-full w-full items-end gap-[1px]">
                            {#each sensitivityData.sweep as point, i}
                              {#if i % 2 === 0}
                                <div 
                                  class="flex-1 rounded-t-sm transition-all {Math.abs(point.threshold - sensitivityData.current_threshold) < 0.02 ? 'bg-brand opacity-100 shadow-[0_0_8px_rgba(177,33,66,0.8)]' : 'bg-brand opacity-40 hover:opacity-80'}"
                                  style="height: {point.f1_score * 100}%"
                                  title="Threshold: {point.threshold.toFixed(2)}, F1: {point.f1_score.toFixed(2)}"
                                ></div>
                              {/if}
                            {/each}
                          </div>
                          <!-- Threshold Marker -->
                          <div 
                            class="absolute top-0 bottom-0 w-0.5 bg-ink shadow-[0_0_12px_rgba(255,255,255,0.8)] z-10"
                            style="left: {sensitivityData.current_threshold * 100}%"
                          >
                            <div class="absolute -top-6 -translate-x-1/2 rounded bg-ink px-1.5 py-0.5 text-[0.6rem] font-bold text-surface">
                              {sensitivityData.current_threshold.toFixed(2)}
                            </div>
                          </div>
                        </div>
                        <div class="mt-3 flex justify-between text-[0.65rem] font-medium text-ink-3 uppercase">
                          <span>0.0</span>
                          <span>Threshold</span>
                          <span>1.0</span>
                        </div>
                      </div>
                    </div>
                  {:else}
                    <div class="mt-4 p-8 text-center text-sm text-ink-3 border border-border border-dashed rounded-xl">
                      No sensitivity sweep data available for this model.
                    </div>
                  {/if}
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</section>
