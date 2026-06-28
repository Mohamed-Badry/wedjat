<script lang="ts">
  import type { SatelliteState } from "$lib/types/api";

  let { state } = $props<{ state: SatelliteState }>();

  // Formatting helpers
  const fmt = (num: number, digits: number = 2) => num.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });

  let metrics = $derived([
    {
      label: "Altitude",
      value: fmt(state.altitude_km, 2),
      unit: "km",
      trend: state.vel_eci.z > 0 ? "asc" : "desc" // simple heuristic
    },
    {
      label: "Velocity",
      value: fmt(state.velocity_km_s, 3),
      unit: "km/s",
    },
    {
      label: "Latitude",
      value: fmt(Math.abs(state.latitude_deg), 4),
      unit: state.latitude_deg >= 0 ? "° N" : "° S",
    },
    {
      label: "Longitude",
      value: fmt(Math.abs(state.longitude_deg), 4),
      unit: state.longitude_deg >= 0 ? "° E" : "° W",
    },
    {
      label: "Elevation (GS)",
      value: fmt(state.ground_station.elevation_deg, 2),
      unit: "°",
      color: state.ground_station.elevation_deg > 0 ? "text-ok" : "text-ink-2"
    },
    {
      label: "Azimuth (GS)",
      value: fmt(state.ground_station.azimuth_deg, 2),
      unit: "°",
    },
    {
      label: "Doppler",
      value: fmt(state.ground_station.doppler_khz, 3),
      unit: "kHz",
      color: state.ground_station.doppler_khz > 0 ? "text-brand" : "text-warning"
    },
    {
      label: "Range",
      value: fmt(state.ground_station.range_km, 1),
      unit: "km",
    }
  ]);
</script>

<div class="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
  {#each metrics as metric}
    <div class="relative overflow-hidden flex flex-col justify-between p-4 bg-surface/30 rounded-xl border border-border/50 shadow-inner group hover:bg-surface/50 transition-colors duration-300">
      <div class="text-[10px] font-bold uppercase tracking-widest text-ink-3 mb-1">
        {metric.label}
      </div>
      <div class="flex items-baseline gap-1.5">
        <span class="text-xl sm:text-2xl font-bold tracking-tight {metric.color || 'text-ink'} font-mono">
          {metric.value}
        </span>
        <span class="text-xs font-bold text-ink-3 uppercase tracking-wider">{metric.unit}</span>
      </div>
      
      <!-- Decorative background accent -->
      <div class="absolute -right-4 -bottom-4 w-16 h-16 bg-brand/5 rounded-full blur-xl group-hover:bg-brand/10 transition-colors duration-500"></div>
    </div>
  {/each}
</div>
