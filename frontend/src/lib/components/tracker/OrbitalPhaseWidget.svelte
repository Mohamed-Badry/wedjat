<script lang="ts">
  import type { OrbitalElements } from "$lib/types/api";

  let { coe } = $props<{ coe: OrbitalElements }>();

  // Dimensions
  const SIZE = 180;
  const CENTER = SIZE / 2;
  const R_EARTH = 36; // visual radius of Earth

  let a_visual = SIZE * 0.4; 
  let e_visual = $derived(Math.min(coe.eccentricity, 0.9)); // Cap visual eccentricity
  let b_visual = $derived(a_visual * Math.sqrt(1 - e_visual * e_visual));
  
  // Focus offset from center (where Earth is)
  let c_visual = $derived(a_visual * e_visual);
  
  // The center of the ellipse is offset from the focus (Earth) by -c
  let cx = $derived(CENTER - c_visual);
  let cy = CENTER;

  // True Anomaly to X/Y on the visual ellipse
  let nu_rad = $derived((coe.true_anomaly_deg * Math.PI) / 180.0);
  let r_visual = $derived((a_visual * (1 - e_visual * e_visual)) / (1 + e_visual * Math.cos(nu_rad)));
  
  // Satellite position relative to focus (Earth)
  let sat_x = $derived(CENTER + r_visual * Math.cos(nu_rad));
  let sat_y = $derived(CENTER - r_visual * Math.sin(nu_rad)); // Y axis is inverted in SVG

  // Formatting helpers
  const fmt = (num: number, digits: number = 2) => num.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
</script>

<div class="flex flex-col items-center justify-between w-full h-full group">
  <div class="flex-1 flex items-center justify-center py-1 min-h-0 w-full">
    <svg viewBox="0 0 {SIZE} {SIZE}" class="overflow-visible w-full h-full max-h-[180px] max-w-[180px]">
      <!-- Grid/Axes (Subtle) -->
      <line x1="0" y1={CENTER} x2={SIZE} y2={CENTER} stroke="currentColor" class="text-border/20" stroke-width="1" stroke-dasharray="2 4" />
      <line x1={CENTER} y1="0" x2={CENTER} y2={SIZE} stroke="currentColor" class="text-border/20" stroke-width="1" stroke-dasharray="2 4" />

      <!-- Orbit Path -->
      <ellipse 
        cx={cx} 
        cy={cy} 
        rx={a_visual} 
        ry={b_visual} 
        fill="none" 
        class="stroke-ink/20 group-hover:stroke-brand/40 transition-colors duration-500" 
        stroke-width="1.5" 
      />

      <!-- Earth -->
      <circle cx={CENTER} cy={CENTER} r={R_EARTH} fill="currentColor" class="text-panel stroke-border/40" stroke-width="1.5" />
      <!-- Earth Terminator (Day/Night illusion) -->
      <path d="M {CENTER} {CENTER - R_EARTH} A {R_EARTH} {R_EARTH} 0 0 1 {CENTER} {CENTER + R_EARTH} A {R_EARTH/2} {R_EARTH} 0 0 0 {CENTER} {CENTER - R_EARTH}" fill="currentColor" class="text-surface/80" />
      <circle cx={CENTER} cy={CENTER} r={R_EARTH} fill="none" class="stroke-brand/10" stroke-width="1" />

      <!-- Perigee Marker (Right side) -->
      <circle cx={CENTER + a_visual * (1 - e_visual)} cy={CENTER} r="2.5" fill="currentColor" class="text-brand/60" />
      <!-- Apogee Marker (Left side) -->
      <circle cx={CENTER - a_visual * (1 + e_visual)} cy={CENTER} r="2.5" fill="currentColor" class="text-ink-3" />

      <!-- Satellite Marker -->
      <g style="transform: translate({sat_x}px, {sat_y}px)" class="transition-transform duration-300">
        <!-- Glow -->
        <circle cx="0" cy="0" r="7" class="fill-brand/20 animate-pulse" />
        <circle cx="0" cy="0" r="3.5" class="fill-brand" />
        <!-- Line to center -->
        <line x1="0" y1="0" x2={CENTER - sat_x} y2={CENTER - sat_y} stroke="currentColor" class="text-brand/30" stroke-width="1" stroke-dasharray="2 2" />
      </g>
    </svg>
  </div>

  <!-- Phase stats grid -->
  <div class="w-full grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border/30 pt-2 mt-1 font-mono text-xs shrink-0">
    <div class="flex flex-col">
      <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">True Anomaly</span>
      <span class="text-brand font-bold">{fmt(coe.true_anomaly_deg, 1)}°</span>
    </div>
    <div class="flex flex-col text-right">
      <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Ang Velocity</span>
      <span class="text-ink-2">{fmt(coe.angular_velocity_deg_min, 2)}°/m</span>
    </div>
    <div class="flex flex-col">
      <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">To Perigee</span>
      <span class="text-ink-2">{fmt(coe.time_to_perigee_min, 1)}m</span>
    </div>
    <div class="flex flex-col text-right">
      <span class="text-[9px] font-bold uppercase tracking-wider text-ink-3">Since Perigee</span>
      <span class="text-ink-2">{fmt(coe.time_since_perigee_min, 1)}m</span>
    </div>
  </div>
</div>
