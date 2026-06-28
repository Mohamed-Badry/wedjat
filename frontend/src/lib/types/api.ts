/**
 * Shared TypeScript contracts for Watchdog API response shapes.
 * Single source of truth — used by page loaders, components, and data transforms.
 */

// ── Satellite Identity ──────────────────────────────────────────────────────

export interface SatelliteSummary {
  name: string;
  norad_id: number;
  decoder?: string;
  dataset: { row_count: number; feature_count: number };
  model: { status: string; threshold?: number };
}

// ── Telemetry Frames ────────────────────────────────────────────────────────

export interface FrameQuality {
  frame_is_complete: boolean;
  missing_raw_fields?: string[];
  missing_raw_field_count?: number;
  sampling_irregular?: boolean;
  dropped_packet_suspect?: boolean;
  same_timestamp_collision?: boolean;
  seconds_since_prev?: number;
  seconds_to_next?: number;
  pass_id?: string;
  pass_duration_sec?: number;
  pass_frame_index?: number;
  pass_frame_count?: number;
  pass_median_cadence_sec?: number;
  cadence_reference_sec?: number;
}

export interface ModelResult {
  anomaly_score: number | null;
  threshold: number;
  is_anomaly: boolean;
  feature_contributions?: Record<string, number>;
  reconstructed_features?: Record<string, number>;
  scaled_features?: Record<string, number>;
  scaled_reconstructed_features?: Record<string, number>;
}

export interface TelemetryFrame {
  timestamp: string;
  norad_id: number;
  source: string;
  features: Record<string, number | null>;
  raw_frame?: string;
  kaitai_decoded?: Record<string, unknown>;
  quality: FrameQuality;
  model: ModelResult;
}

// ── Anomalies ───────────────────────────────────────────────────────────────

export interface AnomalyRecord {
  timestamp: string;
  norad_id: number;
  score: number;
  threshold: number;
  features: Record<string, number>;
  reconstructed_features?: Record<string, number>;
  feature_contributions?: Record<string, number>;
  scaled_features?: Record<string, number>;
  scaled_reconstructed_features?: Record<string, number>;
}

// ── Dashboard Summary ───────────────────────────────────────────────────────

export interface ServiceComponent {
  name: string;
  status: 'online' | 'offline' | 'degraded';
  detail: string;
}

export interface ThroughputBucket {
  timestamp: string;
  frame_count: number;
  anomaly_count: number;
}

export interface DashboardSummary {
  service_status: ServiceComponent[];
  totals: {
    satellite_count: number;
    frame_count: number;
    anomaly_count: number;
    pass_count: number;
  };
  active_satellites: SatelliteSummary[];
  recent_anomalies: {
    norad_id: number;
    timestamp: string;
    score: number | null;
  }[];
  throughput_buckets: ThroughputBucket[];
}

// ── Operations ──────────────────────────────────────────────────────────────

export interface TrackPoint {
  time?: string | Date;
  lat: number;
  lon: number;
  elevation?: number;
  azimuth?: number;
  range_km?: number;
}

export interface PassPrediction {
  satellite: string;
  norad_id: number;
  aos: Date;
  los: Date;
  max_elevation: number;
  direction: string;
  track?: TrackPoint[];
}

export interface StationLocation {
  id?: string;
  label: string;
  lat: number;
  lon: number;
  elevationM: number;
}

// ── Tracker ─────────────────────────────────────────────────────────────────

export interface OrbitalElements {
  semi_major_axis_km: number;
  eccentricity: number;
  inclination_deg: number;
  raan_deg: number;
  arg_perigee_deg: number;
  mean_anomaly_deg: number;
  true_anomaly_deg: number;
  period_min: number;
  mean_motion_rev_day: number;
  apogee_km: number;
  perigee_km: number;
  angular_velocity_deg_min: number;
  time_since_perigee_min: number;
  time_to_perigee_min: number;
  radial_distance_km: number;
  bstar: string;
}

export interface GroundStationView {
  azimuth_deg: number;
  elevation_deg: number;
  range_km: number;
  doppler_khz: number;
}

export interface SatelliteState {
  timestamp_utc: string;
  altitude_km: number;
  velocity_km_s: number;
  latitude_deg: number;
  longitude_deg: number;
  pos_eci: { x: number; y: number; z: number };
  vel_eci: { x: number; y: number; z: number };
  coe: OrbitalElements;
  ground_station: GroundStationView;
}

export interface ConjunctionEvent {
  primary_norad: number;
  secondary_norad: number;
  secondary_name: string;
  tca: string;
  miss_distance_km: number;
  relative_velocity_km_s: number;
  probability: number;
  risk_level: string;
}

export interface ForecastPoint {
  label: string;
  minutes: number;
  timestamp_utc: string;
  altitude_km: number;
  velocity_km_s: number;
  true_anomaly_deg: number;
}

export interface TrackerSnapshot {
  state: SatelliteState;
  forecast: ForecastPoint[];
  elevation_profile: number[];
  azimuth_profile: number[];
  ground_track: { lat: number; lon: number; alt_km: number; t_offset_min: number }[];
  ground_station: { lat: number; lon: number; alt_km: number; name: string };
  tle_source: string;
  tle_age_hr: number | null;
}
