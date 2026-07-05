<script lang="ts">
  import type { PageData } from './$types';

  import ModelComparisonROC from '$lib/components/charts/ModelComparisonROC.svelte';
  import SensitivitySweepPlot from '$lib/components/charts/SensitivitySweepPlot.svelte';
  import FeatureContributionPlot from '$lib/components/charts/FeatureContributionPlot.svelte';

  let { data }: { data: PageData } = $props();
</script>

<svelte:head>
  <title>Model Analysis — Wedjat</title>
</svelte:head>

<div class="mx-auto w-full max-w-7xl pb-24">
  <header class="space-y-4 mb-12 animate-in fade-in slide-in-from-bottom-4 duration-500 ease-out max-w-4xl">
    <p class="text-xs font-semibold uppercase tracking-[0.2em] text-muted">Analysis Report</p>
    <h1 class="text-4xl font-bold tracking-tight text-ink sm:text-5xl">Model Architecture & Benchmarks</h1>
    <p class="text-lg leading-8 text-ink-2">
      Offline experiments and synthetic fault injection results. This notebook explains why we chose the <a href="#glossary-vae" class="text-brand hover:underline">Variational Autoencoder (VAE)</a> over standard models.
    </p>
  </header>

  <div class="space-y-32">
    
    <section class="grid gap-12 xl:grid-cols-2 items-start">
      <div class="prose max-w-none xl:sticky xl:top-24">
        <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">1. Model Selection & Diagnosis Masking</h2>
        <p>
          Orbital telemetry changes significantly based on the <a href="#glossary-eclipse" class="text-brand hover:underline">day/night eclipse cycle</a>, and the systems are highly connected. Simple limits or single-variable Z-scores fail because they cannot track these complex relationships.
        </p>
        <p>
          We tested four methods against a dataset containing fake problems like subtle power drops and heat issues:
        </p>
        <ul>
          <li><strong>Z-Score (Baseline):</strong> Basic statistical limits.</li>
          <li><strong>Isolation Forest:</strong> Finds data points that are alone.</li>
          <li><strong>One-Class SVM:</strong> Draws a boundary around normal data.</li>
          <li><strong>Variational Autoencoder (VAE) with Diagnosis Masking:</strong> Learns to recreate normal data using all features for context, but scores anomalies using only a subset of core health metrics (the <strong>Diagnosis Mask</strong>) to avoid false positives from environmental variables like eclipse transitions.</li>
        </ul>
        <div class="my-6 rounded-xl border border-border bg-surface/50 p-5">
          <p class="m-0 text-sm leading-relaxed">
            <strong>Conclusion:</strong> The VAE is the best model. It takes all features as input to learn inter-system context, but uses a <strong>Diagnosis Mask</strong> to compute anomaly scores only on internal health metrics (e.g. battery voltage, current, temperatures) &mdash; excluding environmental proxies like panel temperature. The threshold is set at the <strong>99.9th percentile</strong> of raw validation scores, ensuring an expected false positive rate of ~0.1%. Because it learns how all the systems work together, it can find real problems without giving false alarms when the satellite enters the earth's shadow.
          </p>
        </div>
      </div>
      <div class="flex flex-col gap-6">
        <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
          <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
            <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
            Model Comparison: ROC Curves
          </h3>
          <div>
            <ModelComparisonROC />
          </div>
        </div>
      </div>
    </section>

    <!-- SECTION 2: Sensitivity Sweep -->
    <section class="grid gap-12 xl:grid-cols-[1fr_2fr] items-start">
      <div class="prose max-w-none xl:sticky xl:top-24">
        <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">2. Sensitivity & Subtlety</h2>
        <p>
          We need to catch problems early. A dead battery is obvious, but a battery draining 5% faster than normal is hard to spot.
        </p>
        <p>
          We tested the models by slowly increasing the size of the fake problems to see when they would trigger an alarm.
        </p>
        <div class="my-6 rounded-xl border border-brand/30 bg-brand/5 p-5">
          <p class="m-0 text-sm leading-relaxed text-ink">
            <strong>Why Z-Score Fails:</strong> A tiny 0.1A current drop doesn't trigger the Z-Score because the satellite's normal changes are bigger than the error. The VAE catches it because the current no longer matches the panel temperature, causing a spike in the error score.
          </p>
        </div>
      </div>
      <div class="flex flex-col gap-6">
        <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
          <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
            <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
            VAE vs. Z-Score Baseline
          </h3>
          <div>
            <SensitivitySweepPlot />
          </div>
        </div>
      </div>
    </section>

    <!-- SECTION 3: Root Cause & Attribution -->
    <section class="grid gap-12 xl:grid-cols-[1fr_2fr] items-start">
      <div class="prose max-w-none xl:sticky xl:top-24">
        <h2 class="text-2xl font-bold tracking-tight text-ink border-b border-border pb-4">3. Root Cause Attribution</h2>
        <p>
          Just knowing there is a problem isn't enough. Operators need to know exactly which part is failing to fix it quickly.
        </p>
        <p>
          Because the VAE tries to recreate the normal data, the difference between the real data and the VAE's recreation points to the broken sensor. We tested three common issues:
        </p>
        <ul>
          <li><strong>Thermal Runaway:</strong> This happens when a battery overheats and cannot cool down, leading to a fire or explosion. The VAE correctly blames the battery temperature sensors (`temp_batt_a` and `temp_batt_b`).</li>
          <li><strong>Panel Failure:</strong> This simulates a solar panel breaking or getting disconnected. The VAE blames the battery current and the panel temperature sensors, recognizing they no longer match up.</li>
          <li><strong>Eclipse EPS Fault:</strong> This is a failure in the electrical power system while in the earth's shadow. The VAE blames the voltage reading for dropping too fast.</li>
        </ul>
      </div>
      <div class="flex flex-col gap-6">
        <div class="rounded-2xl border border-border bg-panel p-6 shadow-sm">
          <h3 class="mt-0 mb-6 flex items-center gap-3 text-sm font-semibold uppercase tracking-widest text-ink-3">
            <span class="inline-block h-3 w-1 rounded-sm bg-brand"></span>
            Autoencoder Per-Feature Reconstruction Error
          </h3>
          <div>
            <FeatureContributionPlot />
          </div>
        </div>
      </div>
    </section>

    <!-- SECTION 4: Glossary -->
    <section class="border-t border-border pt-12">
      <h2 class="text-xl font-bold tracking-tight text-ink mb-6">Glossary & Abbreviations</h2>
      <dl class="space-y-4 text-sm text-ink-2">
        <div id="glossary-vae" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
          <dt class="font-semibold text-ink">VAE</dt>
          <dd>Variational Autoencoder. A machine learning model that learns normal patterns by compressing and recreating data.</dd>
        </div>
        <div id="glossary-eclipse" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
          <dt class="font-semibold text-ink">Eclipse Cycle</dt>
          <dd>The period when the satellite passes through the Earth's shadow, meaning it relies on battery power instead of solar panels.</dd>
        </div>
        <div id="glossary-auc" class="grid grid-cols-[120px_1fr] items-baseline gap-4">
          <dt class="font-semibold text-ink">AUC</dt>
          <dd>Area Under the Curve. A score from 0 to 1 measuring how well a model separates normal data from problems (1.0 is perfect).</dd>
        </div>
      </dl>
    </section>

  </div>
</div>
