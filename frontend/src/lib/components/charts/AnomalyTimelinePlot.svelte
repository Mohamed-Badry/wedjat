<script lang="ts">
  import ResponsivePlot from './ResponsivePlot.svelte';
  import * as Plot from '@observablehq/plot';
  import { BRAND, MUTED, COMPACT_MARGIN } from '$lib/chart-theme';

  let { frames, threshold, selectedTimestamp, height = 130 } = $props<{
    frames: { timestamp: string; anomaly_score: number; is_anomaly: boolean }[];
    threshold: number;
    selectedTimestamp?: string | null;
    height?: number;
  }>();

  type PlotFrame = {
    timestamp: string;
    anomaly_score: number;
    is_anomaly: boolean;
    date: Date;
  };

  let plotData = $derived(
    (frames ?? [])
      .map((f: any) => ({
        ...f,
        date: new Date(f.timestamp),
      }))
      .filter((f: PlotFrame) => Number.isFinite(f.date.getTime()) && Number.isFinite(f.anomaly_score))
      .sort((a: PlotFrame, b: PlotFrame) => a.date.getTime() - b.date.getTime())
  );

  let yMax = $derived(
    Math.max(
      1,
      threshold ? threshold * 1.15 : 0,
      ...plotData.map((f: PlotFrame) => f.anomaly_score * 1.1)
    )
  );

  let selectedData = $derived(
    selectedTimestamp ? plotData.filter((d: PlotFrame) => d.timestamp === selectedTimestamp) : []
  );

  let plotOptions = $derived({
    x: { type: 'utc', label: null },
    y: { label: null, grid: true, domain: [0, yMax] },
    marginTop: COMPACT_MARGIN.top + 8,
    marginRight: COMPACT_MARGIN.right + 8,
    marginBottom: COMPACT_MARGIN.bottom,
    marginLeft: COMPACT_MARGIN.left + 4,
    marks: [
      Plot.ruleY([threshold], { stroke: BRAND, strokeDasharray: "4 4", strokeOpacity: 0.5 }),
      Plot.areaY(plotData, { x: "date", y: "anomaly_score", fill: BRAND, fillOpacity: 0.15 }),
      Plot.lineY(plotData, { x: "date", y: "anomaly_score", stroke: BRAND, strokeWidth: 2 }),
      Plot.dot(plotData, { 
        x: "date", 
        y: "anomaly_score", 
        fill: (d: PlotFrame) => d.is_anomaly ? 'var(--color-critical)' : 'var(--color-panel)', 
        stroke: (d: PlotFrame) => d.is_anomaly ? 'var(--color-critical)' : BRAND, 
        strokeWidth: 1.5, 
        r: 3 
      }),
      ...(selectedData.length > 0 ? [
        Plot.ruleX(selectedData, { x: "date", stroke: BRAND, strokeWidth: 2 }),
        Plot.dot(selectedData, { x: "date", y: "anomaly_score", fill: "var(--color-panel)", stroke: BRAND, strokeWidth: 2, r: 5 })
      ] : [])
    ]
  });
</script>

<div class="h-full w-full">
  <ResponsivePlot {height} options={plotOptions} />
</div>
