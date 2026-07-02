export const telemetryDictionary: Record<string, string> = {
  // Metadata
  timestamp: "The exact UTC time the telemetry frame was received or generated.",
  norad_id: "NORAD catalog ID of the satellite.",
  source: "The ingestion source database or stream (e.g., satnogs_db, live_mqtt).",
  src_callsign: "Source callsign from the AX.25 transmission header.",
  dest_callsign: "Destination callsign from the AX.25 transmission header.",
  
  // Power System
  batt_voltage: "Volts (V) — Combined or averaged battery voltage across the EPS.",
  batt_current: "Amps (A) — Combined battery current (+ indicates charging from panels, - indicates discharging to payloads).",
  batt_a_voltage: "Volts (V) — Voltage of Battery Pack A.",
  batt_b_voltage: "Volts (V) — Voltage of Battery Pack B.",
  batt_a_current: "Amps (A) — Current flow for Battery Pack A.",
  batt_b_current: "Amps (A) — Current flow for Battery Pack B.",
  power_consumption: "Watts (W) — Total power consumption of the satellite payload.",
  
  // Thermal
  temp_obc: "Celsius (°C) — Temperature of the On-Board Computer (Main processing unit).",
  temp_batt_a: "Celsius (°C) — Temperature of Battery Pack A.",
  temp_batt_b: "Celsius (°C) — Temperature of Battery Pack B.",
  temp_panel_z: "Celsius (°C) — Temperature of Solar Panel Z. High values indicate sunlight; low values are a physical proxy for orbital eclipse.",
  
  // Status
  uptime: "Seconds since the satellite's on-board computer last rebooted.",

  // Quality & Pipeline Flags
  frame_is_complete: "Boolean indicating if all required fields in the Kaitai contract were successfully parsed without nulls.",
  missing_raw_fields: "List of fields that were expected by the decoder but missing from the raw hex payload.",
  missing_raw_field_count: "Total number of missing raw fields.",
  sampling_irregular: "Boolean indicating if the time between this frame and the previous frame violates the expected transmission cadence.",
  dropped_packet_suspect: "Boolean indicating if a packet was likely dropped over the radio link, based on a missing cadence window.",
  same_timestamp_collision: "Boolean indicating if multiple frames were received at the exact same millisecond (usually ground-station duplication).",
  seconds_since_prev: "Time delta in seconds since the previously received frame.",
  seconds_to_next: "Time delta in seconds until the next frame.",
  pass_id: "Unique identifier for the continuous line-of-sight pass over the ground station.",
  pass_duration_sec: "Total duration of the current pass in seconds.",
  pass_frame_index: "The sequential index of this frame within the current pass.",
  pass_frame_count: "The total number of frames received during this specific pass.",
  pass_median_cadence_sec: "The median time gap between frames during this pass.",
  cadence_reference_sec: "The expected baseline transmission rate used to calculate dropped packets.",

  // Machine Learning Outputs
  anomaly_score: "Reconstruction error score assigned by the unsupervised ML model (VAE). Higher scores indicate abnormal structural relationships.",
  threshold: "The calibrated limit (e.g., 95th percentile of validation set). Scores above this trigger an anomaly classification.",
  is_anomaly: "Boolean classification. True if the anomaly_score strictly exceeds the model's calibrated threshold.",

  // Glossary & Scientific Concepts
  mqtt: "Message Queuing Telemetry Transport. A lightweight messaging protocol used for connecting remote ground stations.",
  leo: "Low Earth Orbit. An orbit relatively close to Earth's surface (typically below 2,000 km).",
  eclipse_cycle: "The period when the satellite passes through the Earth's shadow, shifting reliance from solar panels to battery power.",
  autoencoder: "A neural network that learns normal patterns by compressing and attempting to losslessly recreate the data. Used for unsupervised anomaly detection.",
  vae: "Variational Autoencoder. A probabilistic autoencoder that compresses data into a continuous latent distribution, excellent for handling bimodal orbital physics.",
  auc: "Area Under the ROC Curve. A metric from 0 to 1 measuring how well a model separates normal data from synthetic faults (1.0 is perfect).",
  stateless_ensemble: "A machine learning architecture that evaluates each telemetry frame in a vacuum, ignoring historical sequence. Necessary because satellite line-of-sight passes create massive 10-hour data blackouts.",
  golden_features: "The standardized, SI-unit normalized floating-point variables derived from raw telemetry, guaranteeing a consistent contract for ML models.",
  bimodal_physics: "Physical states that cluster into two distinct modes (e.g., Battery discharging in eclipse vs charging in sunlight). Requires non-linear anomaly models.",
  thermal_runaway: "A failure cascade where overheating batteries cannot shed heat, potentially leading to catastrophic failure.",
  panel_failure: "A hardware fault where a solar panel stops generating expected current despite being physically exposed to sunlight."
};

export function getFeatureDescription(key: string): string {
  const normalizedKey = key.toLowerCase();
  return telemetryDictionary[normalizedKey] || "No description available for this field.";
}
