<script lang="ts">
  import { gsapAction } from "$lib/actions/gsap";
  import gsap from "gsap";
  import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
  import { themeState } from "$lib/theme.svelte";
  import { 
    LayoutDashboard, Satellite, Crosshair, Cpu,
    Radio, Search, LineChart, Activity, BookOpen, BrainCircuit,
    ArrowRight
  } from "lucide-svelte";

  const features = [
    // operations
    {
      category: "operations",
      route: "/dashboard",
      title: "Mission Control Hub",
      description: "The central entrypoint for edge operators. Displays live communication uptime, real-time subsystem statuses, and active orbital profiles.",
      icon: LayoutDashboard,
      imageLight: "/screenshots/home-light.png",
      imageDark: "/screenshots/home-dark.png",
      badge: "Command Center"
    },
    {
      category: "operations",
      route: "/dashboard/operations",
      title: "Ground Station Pass Planner",
      description: "Calculate line-of-sight communication passes for any custom ground coordinate. Includes real-time azimuth/elevation path tracking and Cairo/ Beni Suef ground station presets.",
      icon: Satellite,
      imageLight: "/screenshots/ops-light.png",
      imageDark: "/screenshots/ops-dark.png",
      badge: "Navigation"
    },
    {
      category: "operations",
      route: "/dashboard/tracker",
      title: "Satellite Orbit Tracker",
      description: "Real-time orbital tracking using Two-Line Element (TLE) propagation. Track orbital elements, sub-satellite points, and future conjunction risks.",
      icon: Crosshair,
      imageLight: "/screenshots/tracker-mission-light.png",
      imageDark: "/screenshots/tracker-mission-dark.png",
      badge: "TLE Propagation",
      subImageLight: "/screenshots/tracker-conjunctions-light.png",
      subImageDark: "/screenshots/tracker-conjunctions-dark.png"
    },
    {
      category: "operations",
      route: "/dashboard/orbit-decay",
      title: "Orbit Decay AI Predictor",
      description: "Predict satellite orbital lifespan and decay rates. Combines physical atmospheric density models with neural network adjustments for high-accuracy forecasts.",
      icon: Cpu,
      imageLight: "/screenshots/orbit-decay-overview-light.png",
      imageDark: "/screenshots/orbit-decay-overview-dark.png",
      badge: "Decay Simulation",
      subImageLight: "/screenshots/orbit-decay-diagnostics-light.png",
      subImageDark: "/screenshots/orbit-decay-diagnostics-dark.png"
    },

    // telemetry
    {
      category: "telemetry",
      route: "/dashboard/live",
      title: "Live Telemetry Watcher",
      description: "A sub-second WebSocket telemetry stream. Watch raw packet frames parse live directly from hardware radio receivers.",
      icon: Radio,
      imageLight: "/screenshots/live-light.png",
      imageDark: "/screenshots/live-dark.png",
      badge: "WebSocket Stream"
    },
    {
      category: "telemetry",
      route: "/dashboard/inspector",
      title: "Telemetry Frame Inspector",
      description: "Search and filter through historical telemetry archives. Query specific parameters, isolate anomalies, and export raw data.",
      icon: Search,
      imageLight: "/screenshots/inspector-light.png",
      imageDark: "/screenshots/inspector-dark.png",
      badge: "Search Index"
    },
    {
      category: "telemetry",
      route: "/dashboard/analytics",
      title: "Macro Data Analytics",
      description: "Aggregate data over weeks or months to see trends. Render macro battery charge state profiles, temperature cycles, and signal-to-noise ratios.",
      icon: LineChart,
      imageLight: "/screenshots/analytics-light.png",
      imageDark: "/screenshots/analytics-dark.png",
      badge: "Long-Term Trends"
    },

    // ai
    {
      category: "ai",
      route: "/dashboard/ml",
      title: "Inference Inspector",
      description: "Root-cause diagnostics using Variational Autoencoders. Hover over flagged anomalies to view exactly which sensor deviated from the VAE's reconstructed baseline.",
      icon: Activity,
      imageLight: "/screenshots/ml-light.png",
      imageDark: "/screenshots/ml-dark.png",
      badge: "Deep Learning",
      subImageLight: "/screenshots/ml-report-light.png",
      subImageDark: "/screenshots/ml-report-dark.png"
    },
    {
      category: "ai",
      route: "/dashboard/eda",
      title: "Exploratory Data Analysis",
      description: "A physics-driven notebook detailing battery charge bimodalities, solar panel temperatures, and sensor Pearson correlations.",
      icon: BookOpen,
      imageLight: "/screenshots/eda-light.png",
      imageDark: "/screenshots/eda-dark.png",
      badge: "Data Validation"
    },
    {
      category: "ai",
      route: "/dashboard/ml-report",
      title: "Model Architecture & Benchmarks",
      description: "Explore the VAE's sensitivity sweeps, ROC curves, and false-positive thresholds against One-Class SVM and Isolation Forest baselines.",
      icon: BrainCircuit,
      imageLight: "/screenshots/ml-report-light.png",
      imageDark: "/screenshots/ml-report-dark.png",
      badge: "Model Validation"
    }
  ];

  // Layered mouse movement state for each index
  let hoverStates = $state<Record<number, { x: number; y: number; active: boolean }>>({});

  function onMouseMove(e: MouseEvent, index: number) {
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const offsetX = (x / rect.width - 0.5) * 15; // max 15px translation
    const offsetY = (y / rect.height - 0.5) * 15;
    hoverStates[index] = { x: offsetX, y: offsetY, active: true };
  }

  function onMouseLeave(index: number) {
    hoverStates[index] = { x: 0, y: 0, active: false };
  }

  function horizontalScrollAnim(node: HTMLElement) {
    gsap.registerPlugin(ScrollTrigger);
    
    const container = node.querySelector('.pin-container') as HTMLElement;
    const strip = node.querySelector('.scroll-strip') as HTMLElement;
    
    // Total width to scroll: the full width of the strip MINUS the viewport width
    const getScrollAmount = () => -(strip.scrollWidth - window.innerWidth);
    
    const tl = gsap.timeline();
    
    // Translate the strip horizontally
    tl.to(strip, {
      x: getScrollAmount,
      ease: "none"
    });
    
    // Flow out cards as we scroll
    const cards = gsap.utils.toArray('.showcase-card', strip) as HTMLElement[];
    cards.forEach((card, index) => {
      const isEven = index % 2 === 0;
      
      tl.to(card, {
        y: isEven ? 30 : -30,   // flow out vertically
        x: isEven ? 15 : -15,   // flow out horizontally
        ease: "none"
      }, 0); // parallel to the main strip translation
    });
    
    ScrollTrigger.create({
      trigger: node,
      start: "top top",
      end: () => `+=${(strip.scrollWidth - window.innerWidth) * 1.15}`,
      pin: true,
      animation: tl,
      scrub: 1, // Add 1 second of smoothing to the horizontal scroll!
      snap: {
        snapTo: 1 / (features.length - 1),
        duration: { min: 0.2, max: 0.6 },
        delay: 0.05,
        ease: "power2.out"
      },
      invalidateOnRefresh: true
    });
    
    return {
      destroy() {
        tl.kill();
        ScrollTrigger.getAll().forEach(t => t.kill());
      }
    };
  }
</script>

<section use:gsapAction={{ animation: horizontalScrollAnim }} class="relative bg-surface border-t border-border h-screen w-full flex flex-col justify-center overflow-hidden">
  <div class="pin-container h-full w-full flex flex-col justify-center pb-0">
    
    <!-- Title section raised up -->
    <div class="absolute top-6 md:top-8 left-0 w-full px-8 md:px-16 z-20 pointer-events-none">
      <h2 class="text-4xl md:text-5xl font-black tracking-tight text-ink drop-shadow-sm">
        Explore the <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand to-info">Dashboard.</span>
      </h2>
      <p class="text-sm md:text-base text-ink-3 mt-2 max-w-2xl leading-relaxed">
        A comprehensive suite of tools designed for Edge Operators. Scroll to explore the different modules available in the Watchdog platform.
      </p>
    </div>

    <!-- The horizontally scrolling strip shifted down -->
    <div class="scroll-strip flex h-[60vh] px-16 gap-16 md:gap-24 items-center w-max">
      {#each features as feature, i}
        {@const isEven = i % 2 === 0}
        {@const hState = hoverStates[i] ?? { x: 0, y: 0, active: false }}
        
        <div class="showcase-card flex flex-col gap-5 w-[60vw] md:w-[42vw] lg:w-[35vw] shrink-0 {isEven ? 'translate-y-[6%]' : '-translate-y-[6%]'}">
          
          <!-- Image Container with Collage -->
          <div 
            role="presentation"
            class="relative w-full aspect-[16/9] rounded-2xl border border-border bg-panel shadow-2xl overflow-visible cursor-pointer group"
            onmousemove={(e) => onMouseMove(e, i)}
            onmouseleave={() => onMouseLeave(i)}
          >
            <!-- Main Image -->
            <div class="w-full h-full rounded-2xl overflow-hidden border border-white/5 relative z-10 transition-transform duration-500 group-hover:scale-[1.01] bg-surface">
              <img src={feature.imageDark} alt={feature.title} class="w-full h-full object-cover only-dark" />
              <img src={feature.imageLight} alt={feature.title} class="w-full h-full object-cover only-light" />
              <div class="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>
            </div>

            <!-- Secondary Image (Floating Collage) -->
            {#if feature.subImageDark}
              <div 
                class="absolute -bottom-6 -right-6 w-2/5 aspect-[16/9] rounded-xl border border-border/80 bg-panel/85 backdrop-blur-md shadow-2xl transition-all duration-300 ease-out overflow-hidden z-20 hidden sm:block"
                style="transform: translate3d({hState.x}px, {hState.y}px, 0) scale({hState.active ? 1.05 : 1});"
              >
                <img src={feature.subImageDark} alt="Overlay view" class="w-full h-full object-cover only-dark" />
                <img src={feature.subImageLight} alt="Overlay view" class="w-full h-full object-cover only-light" />
                <div class="absolute inset-0 bg-white/5 border border-white/10 rounded-xl pointer-events-none"></div>
              </div>
            {/if}
            
            <!-- Glow background -->
            <div class="absolute -inset-1 bg-gradient-to-r from-brand to-info rounded-2xl opacity-0 group-hover:opacity-20 transition-opacity duration-500 blur-xl pointer-events-none z-0"></div>
          </div>

          <!-- Description / Metadata -->
          <div class="flex flex-col gap-2 mt-2 px-1">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-3">
                <div class="flex items-center justify-center size-7 rounded-lg bg-brand/10 border border-brand/20 text-brand">
                  <feature.icon class="size-4" />
                </div>
                <span class="text-[10px] font-bold uppercase tracking-widest text-brand bg-brand/10 border border-brand/15 px-2.5 py-0.5 rounded-md">{feature.badge}</span>
              </div>
              <span class="text-xs font-bold uppercase tracking-widest text-ink-3/55">
                0{i + 1} / 0{features.length}
              </span>
            </div>
            
            <h3 class="text-xl font-bold tracking-tight text-ink mt-1">{feature.title}</h3>
            <p class="text-xs md:text-sm text-ink-3 leading-relaxed max-w-xl">
              {feature.description}
            </p>
            
            <div class="mt-2">
              <a 
                href={feature.route} 
                class="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-widest text-brand hover:text-brand/80 transition-colors group"
              >
                Launch Module 
                <ArrowRight class="size-3.5 transition-transform duration-300 group-hover:translate-x-1" />
              </a>
            </div>
          </div>
          
        </div>
      {/each}
      
      <!-- Blank spacing at the end so the last slide centers -->
      <div class="w-[20vw] shrink-0"></div>
    </div>
  </div>
</section>
