<script lang="ts">
  import ResponsivePlot from './ResponsivePlot.svelte';
  import { Dot, Link } from 'svelteplot';

  let { 
    actual = {}, 
    expected = {},
    scaledActual = {},
    scaledExpected = {},
    activeFeatures = null,
    height = 200
  } = $props<{ 
    actual: Record<string, number>, 
    expected: Record<string, number>,
    scaledActual: Record<string, number>,
    scaledExpected: Record<string, number>,
    activeFeatures?: string[] | null,
    height?: number
  }>();

  const ACTUAL_LBL = 'Actual';
  const EXPECTED_LBL = 'Expected';
  const ACTUAL_COLOR = 'var(--color-brand)';
  const EXPECTED_COLOR = 'var(--color-highlight)';

  let sortedFeatures = $derived(
    (activeFeatures || Object.keys(expected)).sort((a: string, b: string) => Math.abs(scaledActual[b] - scaledExpected[b]) - Math.abs(scaledActual[a] - scaledExpected[a]))
  );

  let dataActual = $derived(sortedFeatures.map((f: string) => ({ 
    feature: f, 
    value: Number(scaledActual[f]), 
    raw: Number(actual[f]),
    type: ACTUAL_LBL 
  })));

  let dataExpected = $derived(sortedFeatures.map((f: string) => ({ 
    feature: f, 
    value: Number(scaledExpected[f]), 
    raw: Number(expected[f]),
    type: EXPECTED_LBL 
  })));

  let dataLinks = $derived(sortedFeatures.map((f: string) => ({
    feature: f,
    val1: Number(scaledExpected[f]),
    val2: Number(scaledActual[f])
  })));
</script>

<div class="w-full">
  {#if Object.keys(scaledExpected).length > 0}
    <ResponsivePlot {height}
      x={{ label: 'Standardized Deviation (Z-Score)', labelAnchor: 'center', grid: true, nice: true }}
      y={{ label: false, domain: sortedFeatures, tickFormat: (d: string) => d.replace(/_/g, ' ').toUpperCase() }}
      marginTop={12} marginRight={20} marginBottom={40} marginLeft={110}>
      
      <!-- Connect Expected to Actual -->
      <Link data={dataLinks} x1="val1" x2="val2" y1="feature" y2="feature" stroke="var(--color-ink-3)" strokeWidth={2} strokeOpacity={0.5} />
      
      <!-- Expected Dots -->
      <Dot data={dataExpected} x="value" y="feature" fill={EXPECTED_COLOR} r={5} 
           title={(d: any) => `${d.feature}\nExpected (Raw): ${d.raw.toFixed(3)}\nZ-Score: ${d.value.toFixed(3)}`} />
           
      <!-- Actual Dots (Plotted last so they sit on top if they overlap) -->
      <Dot data={dataActual} x="value" y="feature" fill={ACTUAL_COLOR} r={5}
           title={(d: any) => `${d.feature}\nActual (Raw): ${d.raw.toFixed(3)}\nZ-Score: ${d.value.toFixed(3)}`} />
    </ResponsivePlot>
    
    <div class="mt-1 flex items-center justify-center gap-6 text-[0.65rem] uppercase tracking-wider font-semibold text-ink-3">
      <span class="flex items-center gap-1.5">
        <span class="inline-block h-2.5 w-2.5 rounded-full" style="background: {EXPECTED_COLOR}"></span>
        Expected
      </span>
      <span class="flex items-center gap-1.5">
        <span class="inline-block h-2.5 w-2.5 rounded-full" style="background: {ACTUAL_COLOR}"></span>
        Actual
      </span>
    </div>
  {:else}
    <div class="flex h-[200px] items-center justify-center text-sm text-ink-3">No scaled data available.</div>
  {/if}
</div>
