<script lang="ts">
  /**
   * Multi-model ROC comparison with AUROC labels.
   * Uses static benchmark data from the Python analysis.
   */
  import { Plot, Line } from 'svelteplot';

  const MODELS = [
    { name: 'VAE', auroc: 0.982, color: '#e64848',
      pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.85},{fpr:.02,tpr:.93},{fpr:.05,tpr:.96},{fpr:.1,tpr:.98},{fpr:.15,tpr:.99},{fpr:.2,tpr:.995},{fpr:.4,tpr:1},{fpr:.7,tpr:1},{fpr:1,tpr:1}] },
    { name: 'One-Class SVM', auroc: 0.813, color: '#f59e0b',
      pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.59},{fpr:.02,tpr:.61},{fpr:.05,tpr:.63},{fpr:.1,tpr:.65},{fpr:.15,tpr:.67},{fpr:.2,tpr:.69},{fpr:.4,tpr:.76},{fpr:.7,tpr:.85},{fpr:1,tpr:1}] },
    { name: 'Isolation Forest', auroc: 0.809, color: '#3a86ff',
      pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.05},{fpr:.02,tpr:.25},{fpr:.05,tpr:.37},{fpr:.1,tpr:.48},{fpr:.15,tpr:.58},{fpr:.2,tpr:.65},{fpr:.4,tpr:.81},{fpr:.7,tpr:.91},{fpr:1,tpr:1}] },
    { name: 'Z-Score (Baseline)', auroc: 0.724, color: '#94a3b8',
      pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.15},{fpr:.02,tpr:.28},{fpr:.05,tpr:.41},{fpr:.1,tpr:.52},{fpr:.15,tpr:.59},{fpr:.2,tpr:.64},{fpr:.4,tpr:.75},{fpr:.7,tpr:.88},{fpr:1,tpr:1}] },
  ];
  const diag = [{fpr:0,tpr:0},{fpr:1,tpr:1}];
</script>

<div class="h-full w-full max-w-2xl mx-auto">
  <Plot height={450}
    x={{ domain: [0, 1], label: 'False Positive Rate', grid: true }}
    y={{ domain: [0, 1], label: 'True Positive Rate (Recall)', grid: true }}
    marginTop={28} marginRight={28} marginBottom={44} marginLeft={52}>
    <Line data={diag} x="fpr" y="tpr" stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" strokeOpacity={0.3} />
    {#each MODELS as m}
      <Line data={m.pts} x="fpr" y="tpr" stroke={m.color} strokeWidth={2.5} />
    {/each}
  </Plot>
</div>
<div class="mt-4 flex flex-wrap items-center justify-center gap-x-5 gap-y-2 text-xs text-ink-2">
  <span class="flex items-center gap-1.5">
    <span class="inline-block h-px w-5 border-t border-dashed" style="border-color: #94a3b8; opacity: 0.5"></span>
    Random baseline
  </span>
  {#each MODELS as m}
    <span class="flex items-center gap-1.5">
      <span class="inline-block h-0.5 w-5 rounded" style="background: {m.color}"></span>
      {m.name} <span class="font-mono text-ink-3">(AUROC={m.auroc.toFixed(3)})</span>
    </span>
  {/each}
</div>
