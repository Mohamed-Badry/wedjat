import { SERIES_TEMP_BATT, SERIES_AMBER, SERIES_CURRENT, SERIES_BASELINE, ML_NORMAL, ML_FAULT } from '$lib/chart-theme';

// ── Model Comparison ROC ────────────────────────────────────────────────────
// Multi-model ROC comparison with AUROC labels.
// Static benchmark data from the Python analysis.

export const ROC_MODELS = [
  { name: 'VAE', auroc: 0.982, color: SERIES_TEMP_BATT,
    pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.85},{fpr:.02,tpr:.93},{fpr:.05,tpr:.96},{fpr:.1,tpr:.98},{fpr:.15,tpr:.99},{fpr:.2,tpr:.995},{fpr:.4,tpr:1},{fpr:.7,tpr:1},{fpr:1,tpr:1}] },
  { name: 'One-Class SVM', auroc: 0.813, color: SERIES_AMBER,
    pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.59},{fpr:.02,tpr:.61},{fpr:.05,tpr:.63},{fpr:.1,tpr:.65},{fpr:.15,tpr:.67},{fpr:.2,tpr:.69},{fpr:.4,tpr:.76},{fpr:.7,tpr:.85},{fpr:1,tpr:1}] },
  { name: 'Isolation Forest', auroc: 0.809, color: SERIES_CURRENT,
    pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.05},{fpr:.02,tpr:.25},{fpr:.05,tpr:.37},{fpr:.1,tpr:.48},{fpr:.15,tpr:.58},{fpr:.2,tpr:.65},{fpr:.4,tpr:.81},{fpr:.7,tpr:.91},{fpr:1,tpr:1}] },
  { name: 'Z-Score (Baseline)', auroc: 0.724, color: SERIES_BASELINE,
    pts: [{fpr:0,tpr:0},{fpr:.005,tpr:.15},{fpr:.02,tpr:.28},{fpr:.05,tpr:.41},{fpr:.1,tpr:.52},{fpr:.15,tpr:.59},{fpr:.2,tpr:.64},{fpr:.4,tpr:.75},{fpr:.7,tpr:.88},{fpr:1,tpr:1}] },
];
export const ROC_DIAG = [{fpr:0,tpr:0},{fpr:1,tpr:1}];

// ── Feature Contribution Plot ───────────────────────────────────────────────
// Per-feature reconstruction error by fault type

export const CONTRIBUTION_NORMAL = 'Normal baseline';
export const CONTRIBUTION_FAULT = 'Injected fault';
export const CONTRIBUTION_NORMAL_COLOR = ML_NORMAL;
export const CONTRIBUTION_FAULT_COLOR = ML_FAULT;

export const CONTRIBUTION_FEATURES = [
  { key: 'batt_voltage', label: 'Voltage' },
  { key: 'batt_current', label: 'Current' },
  { key: 't_batt_a', label: 'Batt A' },
  { key: 't_batt_b', label: 'Batt B' },
  { key: 't_panel_z', label: 'Panel Z' },
];

export const CONTRIBUTION_LABELS = CONTRIBUTION_FEATURES.map((feature) => feature.label);

export const CONTRIBUTION_FAULTS = [
  { name: 'Sensor Stuck', data: [
    ...CONTRIBUTION_FEATURES.map((f, i) => ({ feature: f.label, type: CONTRIBUTION_NORMAL, error: [0.25, 0.35, 0.10, 0.12, 0.40][i] })),
    ...CONTRIBUTION_FEATURES.map((f, i) => ({ feature: f.label, type: CONTRIBUTION_FAULT, error: [0.47, 0.53, 0.10, 0.10, 0.30][i] })),
  ]},
  { name: 'Panel Failure', data: [
    ...CONTRIBUTION_FEATURES.map((f, i) => ({ feature: f.label, type: CONTRIBUTION_NORMAL, error: [0.25, 0.35, 0.10, 0.12, 0.40][i] })),
    ...CONTRIBUTION_FEATURES.map((f, i) => ({ feature: f.label, type: CONTRIBUTION_FAULT, error: [0.82, 1.47, 0.11, 0.12, 0.69][i] })),
  ]},
  { name: 'Thermal Runaway', data: [
    ...CONTRIBUTION_FEATURES.map((f, i) => ({ feature: f.label, type: CONTRIBUTION_NORMAL, error: [0.25, 0.35, 0.10, 0.12, 0.40][i] })),
    ...CONTRIBUTION_FEATURES.map((f, i) => ({ feature: f.label, type: CONTRIBUTION_FAULT, error: [0.72, 0.52, 0.74, 0.34, 0.33][i] })),
  ]},
];

// ── Sensitivity Sweep Plot ──────────────────────────────────────────────────
// VAE vs Z-Score Baseline crossover

export const SENSITIVITY_THERMAL = {
  vae: [{x:0.5,y:.45},{x:1,y:.49},{x:2,y:.58},{x:3,y:.71},{x:5,y:.81},{x:7,y:.93},{x:10,y:1},{x:15,y:1},{x:20,y:1},{x:30,y:1},{x:45,y:1}],
  zs:  [{x:0.5,y:.43},{x:1,y:.41},{x:2,y:.42},{x:3,y:.49},{x:5,y:.60},{x:7,y:.88},{x:10,y:.93},{x:15,y:1},{x:20,y:1},{x:30,y:1},{x:45,y:1}],
};

export const SENSITIVITY_PANEL = {
  vae: [{x:0,y:.70},{x:-.05,y:.75},{x:-.1,y:.76},{x:-.15,y:.79},{x:-.2,y:.84},{x:-.3,y:.89},{x:-.4,y:.97},{x:-.5,y:.99},{x:-.6,y:1},{x:-.8,y:1}],
  zs:  [{x:0,y:.55},{x:-.05,y:.55},{x:-.1,y:.55},{x:-.15,y:.55},{x:-.2,y:.55},{x:-.3,y:.60},{x:-.4,y:.75},{x:-.5,y:.88},{x:-.6,y:.95},{x:-.8,y:1}],
};
