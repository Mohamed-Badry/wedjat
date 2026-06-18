<script lang="ts">
  import { gsapAction } from "$lib/actions/gsap";
  import gsap from "gsap";
  import { Activity, Radio, ChevronRight, BrainCircuit, ShieldAlert, Satellite, Zap } from "lucide-svelte";
  
  import GroundStationMap from "$lib/components/operations/GroundStationMap.svelte";
  import AnomalyTimelinePlot from "$lib/components/charts/AnomalyTimelinePlot.svelte";
  import AnomalyContributionChart from "$lib/components/charts/AnomalyContributionChart.svelte";

  // --- Mock Data Simulator ---
  let mockFrames = $state(Array.from({ length: 60 }, (_, i) => {
    const score = Math.min(1.0, Math.max(0, 0.2 + Math.sin(i / 5) * 0.1 + (i > 45 ? 0.6 : 0) + (Math.random() * 0.05)));
    return {
      timestamp: new Date(Date.now() - (60 - i) * 1000).toISOString(),
      anomaly_score: score,
      is_anomaly: score > 0.45
    };
  }));

  $effect(() => {
    const interval = setInterval(() => {
      mockFrames = [...mockFrames.slice(1), {
        timestamp: new Date().toISOString(),
        anomaly_score: Math.max(0.01, 0.1 + (Math.sin(Date.now() / 1000) * 0.1) + (Math.random() > 0.95 ? 0.6 : 0)),
        is_anomaly: false
      }].map(f => ({ ...f, is_anomaly: f.anomaly_score > 0.45 }));
    }, 800);
    return () => clearInterval(interval);
  });

  // Realistic 'Thermal Runaway' scenario matching ML-Report benchmarks
  const mockExpected = { batt_voltage: 12.0, batt_current: 2.5, t_batt_a: 15.0, t_batt_b: 15.2, t_panel_z: -10.0 };
  const mockActual = { batt_voltage: 11.9, batt_current: 2.8, t_batt_a: 38.5, t_batt_b: 41.2, t_panel_z: -9.5 };
  const mockScaledExpected = { batt_voltage: 0.1, batt_current: -0.2, t_batt_a: 0.0, t_batt_b: 0.1, t_panel_z: -0.1 };
  const mockScaledActual = { batt_voltage: -0.5, batt_current: 1.2, t_batt_a: 4.8, t_batt_b: 5.2, t_panel_z: 0.2 };

  // Smooth orbital ground track crossing exactly over Cairo
  const previewTrack = [
    {lat: -25.0, lon: -15.0},
    {lat: -10.0, lon: -2.0},
    {lat: 5.0, lon: 10.0},
    {lat: 18.0, lon: 21.0},
    {lat: 30.0626, lon: 31.2497}, // Cairo precise center
    {lat: 40.0, lon: 42.0},
    {lat: 48.0, lon: 55.0},
    {lat: 53.0, lon: 70.0},
    {lat: 55.0, lon: 90.0}
  ];

  // --- Advanced GSAP Animations ---
  function heroAnim(node: HTMLElement) {
    const tl = gsap.timeline({ delay: 0.1 }); 
    
    tl.fromTo(".hero-badge", { y: -20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.8, ease: "back.out(1.5)" })
      .fromTo(".hero-title", { y: 40, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 1, ease: "power4.out" }, "-=0.6")
      .fromTo(".hero-desc", { y: 20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 1, ease: "power3.out" }, "-=0.8")
      .fromTo(".hero-buttons", { y: 20, autoAlpha: 0 }, { y: 0, autoAlpha: 1, duration: 0.8, ease: "power3.out" }, "-=0.8")
      .fromTo(".hero-visual", { scale: 0.8, autoAlpha: 0 }, { scale: 1, autoAlpha: 1, duration: 1.5, ease: "power4.out" }, "-=1");
      
    // Hero Parallax
    gsap.to(node, {
      yPercent: 15,
      autoAlpha: 0,
      ease: "none",
      scrollTrigger: {
        trigger: node,
        start: "top top",
        end: "bottom top",
        scrub: true
      }
    });
  }

  // The sticky crossfade story
  function stickyStoryAnim(node: HTMLElement) {
    const steps = gsap.utils.toArray('.story-step', node) as HTMLElement[];
    const visuals = gsap.utils.toArray('.story-visual', node) as HTMLElement[];

    // Ensure first visual is visible, others hidden
    gsap.set(visuals, { autoAlpha: 0, scale: 0.95, zIndex: 0 });
    gsap.set(visuals[0], { autoAlpha: 1, scale: 1, zIndex: 10 });

    steps.forEach((step, index) => {
      const content = step.querySelector('.story-content');
      
      if (content) {
        // Create a single timeline that spans the entire time this step is near the viewport
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: step,
            start: "top 85%", // Starts a bit lower to give room
            end: "bottom 15%", // Escapes a bit higher
            scrub: true
          }
        });

        tl.fromTo(content, 
          { opacity: 0, y: 80 },
          { opacity: 1, y: 0, duration: 1, ease: "none" }
        )
        // Hold state perfectly still while the right-side visual is showcased
        .to({}, { duration: 3 })
        // Fade out smoothly as it gets pushed up by the next step
        .to(content, { opacity: 0, y: -80, duration: 1, ease: "none" });
      }

      // Crossfade the right-hand visual
      gsap.timeline({
        scrollTrigger: {
          trigger: step,
          start: "top 50%",
          end: "bottom 50%",
          onEnter: () => activateVisual(index),
          onEnterBack: () => activateVisual(index),
        }
      });
    });

    function activateVisual(activeIndex: number) {
      visuals.forEach((visual, i) => {
        if (i === activeIndex) {
          gsap.to(visual, { autoAlpha: 1, scale: 1, zIndex: 10, duration: 0.5, ease: "power2.out" });
        } else {
          gsap.to(visual, { autoAlpha: 0, scale: 0.95, zIndex: 0, duration: 0.5, ease: "power2.out" });
        }
      });
    }
  }
</script>

<svelte:head>
  <title>Watchdog | The Mission Control Standard</title>
</svelte:head>

<div class="relative z-10 w-full">
  
  <!-- 1. HERO SECTION -->
  <section class="mx-auto max-w-7xl px-4 lg:px-8">
    <div use:gsapAction={{ animation: heroAnim }} class="grid min-h-[80vh] grid-cols-1 lg:grid-cols-2 items-center gap-8 pt-8">
      
      <!-- Hero Text (Left) -->
      <div class="space-y-6 text-center lg:text-left z-20">
        <div class="hero-badge invisible inline-flex items-center gap-2 rounded-full border border-brand/40 bg-brand/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-brand shadow-[0_0_15px_rgba(139,92,246,0.3)] backdrop-blur-md">
          <Radio class="size-4 animate-pulse" />
          Edge Telemetry Monitoring
        </div>
        <div class="space-y-4">
          <h1 class="hero-title invisible text-5xl font-black tracking-tight text-ink sm:text-6xl lg:text-7xl leading-[1.05] drop-shadow-lg">
            Zero-latency <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand to-info">orbit operations.</span>
          </h1>
          <p class="hero-desc invisible text-lg leading-7 text-ink-2 md:text-xl font-medium max-w-xl mx-auto lg:mx-0">
            Mission control for your ground station. Live pass telemetry, deep ML anomaly tracking, and seamless Edge-to-Cloud architecture.
          </p>
        </div>
        <div class="hero-buttons invisible flex flex-wrap items-center justify-center gap-4 lg:justify-start pt-4">
          <a class="group flex items-center gap-2 rounded-full bg-brand px-8 py-4 text-base font-bold text-white shadow-[0_0_30px_rgba(139,92,246,0.5)] transition-all hover:scale-105 hover:bg-brand/90 hover:shadow-[0_0_40px_rgba(139,92,246,0.7)]" href="/dashboard">
            Launch Mission Control
            <ChevronRight class="size-5 transition-transform group-hover:translate-x-1" />
          </a>
        </div>
      </div>

      <!-- Hero Visual (Right) -->
      <div class="hero-visual invisible relative hidden lg:flex items-center justify-center h-full w-full">
        <div class="absolute inset-0 bg-brand/10 blur-[100px] rounded-full aspect-square w-3/4 m-auto"></div>
        <!-- Orbital Rings Animation -->
        <div class="relative flex items-center justify-center size-80">
          <!-- Center Node -->
          <div class="absolute z-10 size-14 rounded-full bg-surface border-2 border-brand shadow-[0_0_30px_rgba(139,92,246,0.8)] flex items-center justify-center">
             <Satellite class="size-6 text-brand animate-pulse" />
          </div>
          <!-- Orbit Ring 1 -->
          <div class="absolute size-full rounded-full border border-brand/30 animate-[spin_10s_linear_infinite]">
             <div class="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 size-4 rounded-full bg-info shadow-[0_0_15px_rgba(56,189,248,0.8)]"></div>
          </div>
          <!-- Orbit Ring 2 -->
          <div class="absolute size-60 rounded-full border border-info/20 animate-[spin_15s_linear_infinite_reverse]">
             <div class="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 size-3 rounded-full bg-brand shadow-[0_0_10px_rgba(139,92,246,0.8)]"></div>
          </div>
        </div>
      </div>

    </div>
  </section>

  <!-- 2. STICKY STORY SECTION -->
  <section use:gsapAction={{ animation: stickyStoryAnim }} class="mx-auto max-w-7xl px-4 lg:px-8 relative mt-12 mb-12">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 relative">
      
      <!-- LEFT COLUMN: The Scrolling Text Steps -->
      <div class="flex flex-col w-full z-20 pb-[25vh]">
        
        <!-- Step 1 -->
        <div class="story-step h-[150vh] relative pr-0 lg:pr-8">
          <div class="sticky top-[35%]">
            <div class="story-content space-y-4">
              <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-brand">
                <Satellite class="size-5" /> Phase 1: Contact
              </div>
              <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                Autonomous <br/><span class="text-ink-2 font-medium">Ground Operations</span>
              </h2>
              <p class="text-lg text-ink-3 leading-relaxed">
                Predictive pass modeling combined with real-time antenna tracking. Watchdog aligns physical servos with high-precision skyplot vectors. Plan your operations precisely with exact orbital intersections.
              </p>
            </div>
          </div>
        </div>

        <!-- Step 2 -->
        <div class="story-step h-[150vh] relative pr-0 lg:pr-8">
          <div class="sticky top-[35%]">
            <div class="story-content space-y-4">
              <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-ok">
                <Zap class="size-5" /> Phase 2: Ingress
              </div>
              <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                Duplex Edge <br/><span class="text-ink-2 font-medium">Telemetry</span>
              </h2>
              <p class="text-lg text-ink-3 leading-relaxed">
                Bypassing database polling overhead, Watchdog establishes direct WebSocket streams to the inference engine. Experience sub-second UI updates as your hardware breathes in real-time.
              </p>
              <div class="flex items-center gap-4 mt-2">
                 <div class="flex items-center gap-2 rounded-full border border-ok/20 bg-ok/10 px-4 py-2 text-sm font-semibold text-ok">
                   <Activity class="size-4" /> WebSocket Native
                 </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3 -->
        <div class="story-step h-[150vh] relative pr-0 lg:pr-8">
          <div class="sticky top-[35%]">
            <div class="story-content space-y-4">
              <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-critical">
                <BrainCircuit class="size-5" /> Phase 3: Intelligence
              </div>
              <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                The Variational <br/><span class="text-ink-2 font-medium">Autoencoder</span>
              </h2>
              <p class="text-lg text-ink-3 leading-relaxed">
                Trained offline, deployed to the edge. The VAE reconstructs incoming hardware vectors, flagging cascading faults long before traditional static Z-score bounds trip.
              </p>
            </div>
          </div>
        </div>

      </div>

      <!-- RIGHT COLUMN: The Sticky Visuals -->
      <div class="hidden lg:block relative w-full h-full">
        <!-- Sticky container stays fixed to top of viewport while scrolling the left column -->
        <div class="sticky top-0 h-screen w-full flex items-center justify-center">
          <div class="relative w-full max-w-2xl aspect-[4/3]">
            
            <!-- Visual 1: Operations -->
            <div class="story-visual absolute inset-0 w-full h-full flex flex-col justify-center">
              <div class="rounded-[2rem] border border-brand/20 bg-panel/50 p-4 backdrop-blur-md shadow-[0_0_50px_rgba(139,92,246,0.15)] pointer-events-none">
                <GroundStationMap 
                  location={{ lat: 30.0626, lon: 31.2497, label: "Cairo, Egypt", elevationM: 23 }}
                  selectedTrack={previewTrack}
                  previewMode={true}
                />
              </div>
            </div>

            <!-- Visual 2: Telemetry -->
            <div class="story-visual absolute inset-0 w-full h-full flex flex-col justify-center">
              <div class="chart-card group border-ok/20 bg-ok/5 shadow-[0_0_50px_rgba(20,184,166,0.15)] w-full">
                <div class="flex items-center justify-between mb-4">
                  <p class="chart-card-title !mb-0 flex items-center gap-2 text-ok">
                    <BrainCircuit class="size-4" /> Live Anomaly Detection
                  </p>
                  <div class="flex items-center gap-2">
                    <span class="relative flex h-2 w-2">
                      <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                    </span>
                    <span class="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">Live Sync</span>
                  </div>
                </div>
                <div class="h-80 relative overflow-hidden rounded-lg bg-surface/50 p-2">
                  <AnomalyTimelinePlot frames={mockFrames} threshold={0.45} selectedTimestamp={null} height={240} />
                </div>
              </div>
            </div>

            <!-- Visual 3: ML -->
            <div class="story-visual absolute inset-0 w-full h-full flex flex-col justify-center">
              <div class="chart-card w-full shadow-[0_0_50px_rgba(139,92,246,0.15)] border-brand/20">
                <div class="mb-4">
                  <p class="chart-card-title text-brand mb-1">Vector Reconstruction Error</p>
                  <p class="text-xs text-ink-3">Live deviation from VAE expectations</p>
                </div>
                <div class="bg-surface/50 rounded-lg p-3">
                  <AnomalyContributionChart 
                    actual={mockActual} 
                    expected={mockExpected} 
                    scaledActual={mockScaledActual} 
                    scaledExpected={mockScaledExpected} 
                  />
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  </section>

  <!-- 3. CTA SECTION (Edge to Edge Glass Parallax) -->
  <section class="relative w-full min-h-screen flex items-center justify-center overflow-hidden bg-surface/10 mt-20 border-t border-border backdrop-blur-md">
    
    <!-- Colorful floating stained glass blobs -->
    <div class="absolute inset-0 z-0 overflow-hidden pointer-events-none">
      <div class="absolute top-1/4 left-1/4 w-[40vw] aspect-square rounded-full bg-brand/15 blur-[120px]"></div>
      <div class="absolute bottom-1/4 right-1/4 w-[50vw] aspect-square rounded-full bg-info/15 blur-[150px]"></div>
      <div class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-3xl aspect-square rounded-full bg-brand/10 blur-[100px]"></div>
    </div>

    <!-- Content centered -->
    <div class="relative z-10 flex flex-col items-center justify-center space-y-8 text-center px-4 w-full max-w-4xl">
      <div class="size-20 rounded-full bg-brand/10 border border-brand/20 flex items-center justify-center shadow-[0_0_40px_rgba(139,92,246,0.3)] mb-4">
         <Radio class="size-10 text-brand animate-pulse" />
      </div>
      
      <h2 class="text-5xl lg:text-7xl font-black text-ink drop-shadow-md">
        Ready for <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand to-info">Launch.</span>
      </h2>
      
      <p class="text-xl text-ink-3 max-w-2xl font-medium leading-relaxed">
        Experience the definitive standard in Edge Operations. Combine predictive skyplot tracking with real-time hardware telemetry and machine learning anomaly detection.
      </p>
      
      <!-- Feature Mini-List -->
      <div class="flex flex-wrap justify-center gap-4 py-6">
        <div class="flex items-center gap-2 text-sm font-semibold text-ink-2 bg-panel/80 px-5 py-2.5 rounded-full border border-border backdrop-blur-md shadow-sm">
           <Zap class="size-4 text-ok" /> Live WebSockets
        </div>
        <div class="flex items-center gap-2 text-sm font-semibold text-ink-2 bg-panel/80 px-5 py-2.5 rounded-full border border-border backdrop-blur-md shadow-sm">
           <BrainCircuit class="size-4 text-brand" /> VAE ML Models
        </div>
        <div class="flex items-center gap-2 text-sm font-semibold text-ink-2 bg-panel/80 px-5 py-2.5 rounded-full border border-border backdrop-blur-md shadow-sm">
           <ShieldAlert class="size-4 text-critical" /> Auto-Alerts
        </div>
      </div>

      <div class="pt-6">
        <a class="group relative inline-flex items-center gap-3 rounded-full bg-brand px-12 py-5 text-lg font-bold text-white shadow-[0_0_40px_rgba(139,92,246,0.6)] transition-all hover:scale-110 hover:bg-brand/90 hover:shadow-[0_0_60px_rgba(139,92,246,0.8)] overflow-hidden" href="/dashboard">
          <!-- Sparkle hover effect -->
          <div class="absolute inset-0 -translate-x-full bg-white/20 skew-x-12 transition-transform duration-700 ease-out group-hover:translate-x-full"></div>
          Start Watchdog
          <ChevronRight class="size-6 transition-transform group-hover:translate-x-2" />
        </a>
      </div>
    </div>
  </section>
</div>
