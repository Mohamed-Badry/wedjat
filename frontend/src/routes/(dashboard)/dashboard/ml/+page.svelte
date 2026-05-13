<script lang="ts">
  import type { PageData } from './$types';

  import ModelComparisonROC from '$lib/components/charts/ModelComparisonROC.svelte';
  import SensitivitySweepPlot from '$lib/components/charts/SensitivitySweepPlot.svelte';
  import FeatureContributionPlot from '$lib/components/charts/FeatureContributionPlot.svelte';

  let { data }: { data: PageData } = $props();

  let satellites = $derived(data.satellites || []);
  let error = $derived(data.error);

  let selectedSatId = $state<string>('');

  $effect(() => {
    if (satellites.length > 0 && !selectedSatId) {
      selectedSatId = satellites[0].norad_id.toString();
    }
  });

  let selectedSat = $derived(satellites.find((s: any) => s.norad_id.toString() === selectedSatId) || null);
</script>

<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out">
  <div class="space-y-3">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Machine Learning</p>
    <h1 class="text-4xl font-semibold tracking-tight text-ink">ML Lab & Artifacts</h1>
    <p class="max-w-3xl text-base leading-7 text-ink-2">
      VAE model artifacts, offline benchmark results, and subsystem blame attribution from synthetic fault injection.
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
      <!-- Sidebar -->
      <div class="flex flex-col gap-4 lg:col-span-1">
        <h2 class="text-xs font-semibold uppercase tracking-wider text-ink-3">Active Models</h2>
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

      <!-- Model Detail Panel -->
      <div class="lg:col-span-3">
        {#if selectedSat}
          <div class="overflow-hidden rounded-[1.75rem] border border-border bg-panel shadow-panel backdrop-blur">
            <div class="border-b border-border bg-surface/50 p-6 lg:p-8">
              <h2 class="text-2xl font-semibold tracking-tight text-ink">{selectedSat.name} Autoencoder</h2>
              <p class="mt-1 flex items-center gap-2 text-sm text-ink-3">
                Status:
                <span class="inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium {selectedSat.model.status === 'ready' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}">
                  {selectedSat.model.status}
                </span>
              </p>
            </div>

            <div class="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-4">
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Inference Mode</p>
                <p class="mt-2 text-xl font-medium text-ink capitalize">{selectedSat.model.inference_mode || 'Unknown'}</p>
              </div>
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Threshold</p>
                <p class="mt-2 text-xl font-medium text-brand">{selectedSat.model.threshold?.toFixed(3) || 'N/A'}</p>
              </div>
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Contract</p>
                <p class="mt-2 text-xl font-medium text-ink">v{selectedSat.model.feature_contract_version || '?'}</p>
              </div>
              <div class="bg-panel p-6">
                <p class="text-xs font-semibold uppercase tracking-wider text-ink-3">Artifact</p>
                <p class="mt-2 text-xl font-medium text-ink">v{selectedSat.model.artifact_version || '?'}</p>
              </div>
            </div>

            <div class="p-6 lg:p-8 space-y-6">
              <div>
                <h3 class="text-sm font-semibold uppercase tracking-wider text-ink-3">Feature Engineering Contract</h3>
                <div class="mt-3 flex flex-wrap gap-2">
                  {#each selectedSat.model.feature_names || [] as feature}
                    <span class="rounded-lg border border-border bg-surface px-3 py-1 text-xs font-medium text-ink-2 transition hover:border-brand hover:text-ink">{feature}</span>
                  {/each}
                  {#if !selectedSat.model.feature_names?.length}
                    <span class="text-sm text-ink-3">No features defined.</span>
                  {/if}
                </div>
              </div>

              <div class="pt-6 border-t border-border">
                <h3 class="text-sm font-semibold uppercase tracking-wider text-ink-3">Dataset Provenance</h3>
                <div class="mt-4 grid gap-4 sm:grid-cols-3">
                  {#each [
                    { label: 'Training', rows: selectedSat.model.train_rows, date: selectedSat.model.train_start },
                    { label: 'Validation', rows: selectedSat.model.validation_rows, date: selectedSat.model.validation_start },
                    { label: 'Testing', rows: selectedSat.model.test_rows, date: selectedSat.model.test_start },
                  ] as split}
                    <div class="rounded-xl border border-border bg-surface p-4">
                      <p class="text-xs font-medium text-ink-2 mb-1">{split.label} Set</p>
                      <p class="text-2xl font-semibold tracking-tight text-ink">{split.rows?.toLocaleString() || 0}</p>
                      <p class="text-[0.65rem] text-ink-3 mt-2">{split.date ? new Date(split.date).toLocaleDateString() : '-'}</p>
                    </div>
                  {/each}
                </div>
              </div>
            </div>
          </div>
        {/if}
      </div>
    </div>

    <!-- Offline Benchmark Results -->
    <div class="space-y-6 pt-4">
      <div class="space-y-1">
        <h2 class="text-xl font-semibold tracking-tight text-ink">Offline Benchmark Results</h2>
        <p class="text-xs text-ink-3">Static results from synthetic fault injection. These reproduce the Python analysis figures.</p>
      </div>

      <div class="grid gap-6 xl:grid-cols-2">
        <div class="chart-card">
          <p class="chart-card-title">Model Comparison — ROC Curves</p>
          <p class="mb-4 text-[10px] leading-4 text-ink-3">
            4 unsupervised models benchmarked. VAE provides the best trade-off for bimodal orbital data.
          </p>
          <ModelComparisonROC />
        </div>

        <div class="chart-card">
          <p class="chart-card-title">VAE vs. Z-Score Baseline</p>
          <p class="mb-4 text-[10px] leading-4 text-ink-3">
            Fault magnitudes swept from subtle to extreme. VAE outperforms static thresholding.
          </p>
          <SensitivitySweepPlot />
        </div>
      </div>

      <div class="chart-card">
        <p class="chart-card-title">Autoencoder — Per-Feature Reconstruction Error</p>
        <p class="mb-4 text-[10px] leading-4 text-ink-3">
          Subsystem blame attribution. The feature with the highest reconstruction error identifies the anomaly source.
        </p>
        <FeatureContributionPlot />
      </div>
    </div>
  {/if}
</section>
