<script lang="ts">
  import { ShieldAlert, AlertTriangle, Info, Clock, X } from "lucide-svelte";
  import type { ConjunctionEvent } from "$lib/types/api";
  import { onDestroy } from "svelte";

  let { events = [] } = $props<{ events: ConjunctionEvent[] }>();

  // Find the most critical event that hasn't passed yet
  let now = $state(new Date());
  
  // Update "now" every second for the countdown
  let timer: ReturnType<typeof setInterval>;
  $effect(() => {
    timer = setInterval(() => {
      now = new Date();
    }, 1000);
    return () => clearInterval(timer);
  });

  let upcomingEvents = $derived(
    events.filter((e: ConjunctionEvent) => new Date(e.tca).getTime() > now.getTime())
  );
  
  // Sort by risk priority, then by time
  const riskWeights: Record<string, number> = { "CRITICAL": 3, "HIGH": 2, "WARNING": 1, "NOMINAL": 0 };
  
  let primaryEvent = $derived(
    upcomingEvents.length > 0 
      ? upcomingEvents.sort((a: ConjunctionEvent, b: ConjunctionEvent) => {
          const wA = riskWeights[a.risk_level] || 0;
          const wB = riskWeights[b.risk_level] || 0;
          if (wA !== wB) return wB - wA;
          return new Date(a.tca).getTime() - new Date(b.tca).getTime();
        })[0]
      : null
  );

  let dismissed = $state(false);
  let showBanner = $derived(primaryEvent !== null && primaryEvent.risk_level !== "NOMINAL" && !dismissed);

  function formatCountdown(tcaStr: string, current: Date) {
    const target = new Date(tcaStr).getTime();
    const diff = target - current.getTime();
    if (diff <= 0) return "T-00:00:00";
    
    const h = Math.floor(diff / (1000 * 60 * 60));
    const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
    const s = Math.floor((diff % (1000 * 60)) / 1000);
    return `T-${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  
  let riskColors = $derived((({
    "CRITICAL": "bg-critical/20 border-critical/50 text-critical shadow-[0_0_15px_rgba(239,68,68,0.3)]",
    "HIGH": "bg-warning/20 border-warning/50 text-warning shadow-[0_0_15px_rgba(245,158,11,0.2)]",
    "WARNING": "bg-brand/20 border-brand/50 text-brand shadow-[0_0_15px_rgba(139,92,246,0.2)]",
    "NOMINAL": "bg-ok/10 text-ok border-ok/30"
  }) as Record<string, string>)[primaryEvent?.risk_level || "WARNING"]);

</script>

{#if showBanner && primaryEvent}
  <div class="mb-6 lg:mb-0 lg:absolute lg:top-4 lg:right-6 lg:z-40 w-full lg:max-w-md flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 rounded-xl border {riskColors} p-4 shadow-sm lg:shadow-xl lg:backdrop-blur-md animate-in fade-in slide-in-from-top-4 duration-500 relative pr-10">
    <!-- Dismiss button -->
    <button 
      onclick={() => dismissed = true} 
      class="absolute top-3 right-3 text-ink-3 hover:text-ink transition-colors p-1 rounded-lg hover:bg-white/10" 
      aria-label="Dismiss alert"
    >
      <X class="size-4" />
    </button>

    <div class="flex items-start sm:items-center gap-3">
      {#if primaryEvent.risk_level === "CRITICAL"}
        <ShieldAlert class="size-6 shrink-0 animate-pulse" />
      {:else if primaryEvent.risk_level === "HIGH"}
        <AlertTriangle class="size-6 shrink-0" />
      {:else}
        <Info class="size-6 shrink-0" />
      {/if}
      <div>
        <h3 class="font-bold flex items-center gap-2">
          <span class="uppercase tracking-widest text-xs opacity-90">{primaryEvent.risk_level} CONJUNCTION ALERT</span>
        </h3>
        <p class="text-sm opacity-90 mt-0.5">
          Object <span class="font-mono bg-black/20 px-1 rounded">{primaryEvent.secondary_name} ({primaryEvent.secondary_norad})</span> 
          approaching within <span class="font-bold">{primaryEvent.miss_distance_km.toFixed(2)} km</span>
        </p>
      </div>
    </div>
    
    <div class="flex items-center gap-4 bg-black/20 px-4 py-2 rounded-lg shrink-0 w-full sm:w-auto">
      <div class="flex flex-col text-right">
        <span class="text-[9px] uppercase tracking-widest opacity-80">Time to Closest Approach</span>
        <span class="font-mono font-bold text-lg">{formatCountdown(primaryEvent.tca, now)}</span>
      </div>
      <div class="h-8 w-px bg-current opacity-20"></div>
      <div class="flex flex-col text-right">
        <span class="text-[9px] uppercase tracking-widest opacity-80">Probability</span>
        <span class="font-mono font-bold">{(primaryEvent.probability * 100).toExponential(2)}%</span>
      </div>
    </div>
  </div>
{/if}
