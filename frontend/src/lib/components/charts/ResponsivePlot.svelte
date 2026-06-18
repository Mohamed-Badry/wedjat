<script lang="ts">
  import { Plot as SveltePlot } from 'svelteplot';
  import * as Plot from "@observablehq/plot";
  
  let { children, options = null, height, square = false, ...rest } = $props<{
    children?: import('svelte').Snippet;
    options?: Plot.PlotOptions | null;
    height?: number;
    square?: boolean;
    [key: string]: any;
  }>();
  
  let container: HTMLDivElement;
  let innerWidth = $state(0);
  let width = $state(0);
  
  let computedHeight = $derived.by(() => {
    if (width === 0) return height;
    if (square) return width;
    if (height && innerWidth > 0 && innerWidth < 768) {
      return Math.max(150, Math.round(height * (width / 768)));
    }
    return height;
  });

  let computedWidth = $derived.by(() => {
    if (width === 0) return 0;
    if (square) return width;
    return width;
  });

  $effect(() => {
    // Only mount native Observable Plot if options are explicitly passed
    if (!options || !container || width === 0) return;

    const finalOptions = {
      ...options,
      width: width,
      height: computedHeight,
    };

    const chart = Plot.plot(finalOptions);
    container.innerHTML = "";
    container.append(chart);

    return () => {
      chart.remove();
    };
  });
</script>

<svelte:window bind:innerWidth={innerWidth} />

{#if options}
  <!-- NATIVE OBSERVABLE PLOT MODE (NEW) -->
  <div bind:this={container} bind:clientWidth={width} class="w-full h-full min-w-0 flex items-center justify-center">
    {#if width === 0}
      <div style="height: {height ?? 300}px; width: 100%;"></div>
    {/if}
  </div>
{:else}
  <!-- SVELTEPLOT MODE (BACKWARDS COMPATIBILITY) -->
  <div class="w-full h-full min-w-0 flex items-center justify-center" bind:clientWidth={width}>
    {#if width > 0}
      <SveltePlot width={computedWidth} height={computedHeight} {...rest}>
        {@render children?.()}
      </SveltePlot>
    {:else}
      <div style="height: {height ?? 300}px; width: 100%;"></div>
    {/if}
  </div>
{/if}
