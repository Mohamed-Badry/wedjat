/**
 * Lightweight data adapters for SveltePlot chart components.
 * These sit between the raw API response and the <Plot> data prop.
 */

// ── Throughput / Dashboard ──────────────────────────────────────────────────

/** Map a throughput bucket's ISO string to a Date for temporal scales. */
export function parseBucketTimestamp<T extends { timestamp: string }>(b: T) {
  return { ...b, date: new Date(b.timestamp) };
}

/** Derive the nominal (non-anomaly) count from total minus anomalies. */
export function addNominalCount<T extends { frame_count: number; anomaly_count: number }>(b: T) {
  return { ...b, nominal: b.frame_count - b.anomaly_count };
}

// ── Feature Normalization ───────────────────────────────────────────────────
// Shared helpers for converting raw telemetry feature maps into typed,
// validated numeric values. Used by EDA, MacroHealthPlot, and any future
// component that needs to interpret raw `features: Record<string, unknown>`.

export type FeatureMap = Record<string, unknown>;

export type NormalizedFeatures = {
  batt_voltage: number | null;
  batt_current: number | null;
  batt_a_voltage: number | null;
  batt_b_voltage: number | null;
  temp_batt_a: number | null;
  temp_batt_b: number | null;
  temp_panel_z: number | null;
  [key: string]: number | null;
};

/** Safely coerce an unknown value to a finite number, or null. */
export function toFiniteNumber(value: unknown): number | null {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

/** Try multiple keys for a numeric value in a feature map. Returns the first valid hit. */
export function featureNumber(features: FeatureMap, keys: string[]): number | null {
  for (const key of keys) {
    const value = toFiniteNumber(features[key]);
    if (value !== null) return value;
  }
  return null;
}

/** Resolve battery voltage — combined, or averaged from A+B. */
export function batteryVoltage(features: FeatureMap): number | null {
  const combined = toFiniteNumber(features.batt_voltage);
  if (combined !== null) return combined;

  const batteryA = toFiniteNumber(features.batt_a_voltage);
  const batteryB = toFiniteNumber(features.batt_b_voltage);
  if (batteryA !== null && batteryB !== null) return (batteryA + batteryB) / 2;
  return batteryA ?? batteryB;
}

/** Normalize a raw feature map into a typed structure with validated numbers. */
export function normalizeFeatures(features: FeatureMap): NormalizedFeatures {
  return {
    batt_voltage: batteryVoltage(features),
    batt_current: featureNumber(features, ['batt_current']),
    batt_a_voltage: featureNumber(features, ['batt_a_voltage']),
    batt_b_voltage: featureNumber(features, ['batt_b_voltage']),
    temp_batt_a: featureNumber(features, ['temp_batt_a']),
    temp_batt_b: featureNumber(features, ['temp_batt_b']),
    temp_panel_z: featureNumber(features, ['temp_panel_z']),
  };
}
