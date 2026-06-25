<script lang="ts">
  import { gsapAction } from "$lib/actions/gsap";
  import gsap from "gsap";
  import { ScrollTrigger } from "gsap/dist/ScrollTrigger";
  import { themeState } from "$lib/theme.svelte";
  import { Activity, Radio, Satellite, LayoutDashboard, LineChart, Search } from "lucide-svelte";

  const features = [
    {
      title: "Mission Control",
      description: "The ultimate command center. Instant top-level metrics, active satellite profiles, and live system health at a glance.",
      icon: LayoutDashboard,
      color: "text-brand",
      bgLight: "bg-brand/10",
      bgDark: "bg-brand/20",
      imageLight: "/screenshots/home-light.png",
      imageDark: "/screenshots/home-dark.png"
    },
    {
      title: "Operations Map",
      description: "Interactive Ground Station Map. Track real-time satellite trajectories and predict upcoming line-of-sight passes.",
      icon: Satellite,
      color: "text-info",
      bgLight: "bg-info/10",
      bgDark: "bg-info/20",
      imageLight: "/screenshots/ops-light.png",
      imageDark: "/screenshots/ops-dark.png"
    },
    {
      title: "Live Watcher",
      description: "High-speed WebSocket telemetry stream. Watch raw data flow directly from your hardware in real-time.",
      icon: Radio,
      color: "text-emerald-500",
      bgLight: "bg-emerald-500/10",
      bgDark: "bg-emerald-500/20",
      imageLight: "/screenshots/live-light.png",
      imageDark: "/screenshots/live-dark.png"
    },
    {
      title: "Telemetry Inspector",
      description: "Detailed frame analysis. Filter, sort, and search through thousands of raw telemetry packets to isolate exact edge cases.",
      icon: Search,
      color: "text-brand",
      bgLight: "bg-brand/10",
      bgDark: "bg-brand/20",
      imageLight: "/screenshots/inspector-light.png",
      imageDark: "/screenshots/inspector-dark.png"
    },
    {
      title: "Inference Inspector",
      description: "Deep dive into anomaly detection. Inspect specific telemetry frames and see exactly which features the VAE flagged.",
      icon: Activity,
      color: "text-warning",
      bgLight: "bg-warning/10",
      bgDark: "bg-warning/20",
      imageLight: "/screenshots/ml-light.png",
      imageDark: "/screenshots/ml-dark.png"
    },
    {
      title: "Data Analytics",
      description: "Long-term data visualization. Powerful aggregated charts and trend analysis over massive telemetry datasets.",
      icon: LineChart,
      color: "text-brand",
      bgLight: "bg-brand/10",
      bgDark: "bg-brand/20",
      imageLight: "/screenshots/analytics-light.png",
      imageDark: "/screenshots/analytics-dark.png"
    }
  ];

  function horizontalScrollAnim(node: HTMLElement) {
    gsap.registerPlugin(ScrollTrigger);
    
    const container = node.querySelector('.pin-container') as HTMLElement;
    const strip = node.querySelector('.scroll-strip') as HTMLElement;
    
    // Total width to scroll: the full width of the strip MINUS the viewport width
    const getScrollAmount = () => -(strip.scrollWidth - window.innerWidth);
    
    const tween = gsap.to(strip, {
      x: getScrollAmount,
      ease: "none"
    });
    
    ScrollTrigger.create({
      trigger: node,
      start: "top top",
      end: () => `+=${getScrollAmount() * -1}`,
      pin: true,
      animation: tween,
      scrub: 1, // Add 1 second of smoothing to the horizontal scroll!
      snap: {
        snapTo: 1 / (features.length - 1),
        duration: { min: 0.2, max: 0.6 },
        delay: 0.1,
        ease: "power2.inOut"
      },
      invalidateOnRefresh: true
    });
    
    return {
      destroy() {
        tween.kill();
        ScrollTrigger.getAll().forEach(t => t.kill());
      }
    };
  }
</script>

<section use:gsapAction={{ animation: horizontalScrollAnim }} class="relative bg-surface border-t border-border h-screen w-full flex flex-col justify-center overflow-hidden">
  <div class="pin-container h-full w-full flex flex-col justify-center">
    
    <!-- Title section that stays fixed in place -->
    <div class="absolute top-16 left-0 w-full px-8 md:px-16 z-20 pointer-events-none">
      <h2 class="text-4xl md:text-5xl font-black tracking-tight text-ink drop-shadow-sm">
        Explore the <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand to-info">Dashboard.</span>
      </h2>
      <p class="text-lg text-ink-3 mt-4 max-w-2xl">
        A comprehensive suite of tools designed for Edge Operators. Scroll to explore the different modules available in the Watchdog platform.
      </p>
    </div>

    <!-- The horizontally scrolling strip -->
    <div class="scroll-strip flex h-[65vh] mt-24 px-8 md:px-16 gap-8 md:gap-16 items-center w-max">
      {#each features as feature, i}
        <div class="flex flex-col lg:flex-row gap-8 lg:gap-12 w-[85vw] md:w-[70vw] lg:w-[60vw] shrink-0 items-center">
          
          <!-- Text Description -->
          <div class="flex-1 w-full lg:w-1/3 flex flex-col gap-4">
            <div class="inline-flex items-center justify-center size-12 rounded-xl border border-border/50 only-dark {feature.bgDark}">
              <feature.icon class="size-6 {feature.color}" />
            </div>
            <div class="inline-flex items-center justify-center size-12 rounded-xl border border-border/50 only-light {feature.bgLight}">
              <feature.icon class="size-6 {feature.color}" />
            </div>
            
            <h3 class="text-3xl font-bold tracking-tight text-ink">{feature.title}</h3>
            <p class="text-base md:text-lg text-ink-3 leading-relaxed">
              {feature.description}
            </p>
            <div class="text-xs font-bold uppercase tracking-widest text-ink-3/50 mt-4">
              0{i + 1} / 0{features.length}
            </div>
          </div>

          <!-- Image / Placeholder -->
          <div class="w-full lg:w-2/3 aspect-[16/9] rounded-2xl border border-border bg-panel shadow-[0_0_50px_rgba(0,0,0,0.1)] overflow-hidden relative group">
            <img src={feature.imageDark} alt={feature.title} class="w-full h-full object-cover only-dark" />
            <img src={feature.imageLight} alt={feature.title} class="w-full h-full object-cover only-light" />
            
            <!-- Sleek glass reflection -->
            <div class="absolute inset-0 bg-gradient-to-tr from-transparent via-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none"></div>
          </div>

        </div>
      {/each}
      
      <!-- Blank spacing at the end so the last slide centers -->
      <div class="w-[10vw] shrink-0"></div>
    </div>
  </div>
</section>
