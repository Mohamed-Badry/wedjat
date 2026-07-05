<script lang="ts">
  import { gsapAction } from "$lib/actions/gsap";
  import gsap from "gsap";
  import { Activity, Radio, ChevronRight, BrainCircuit, ShieldAlert, Satellite, Zap, Mouse, ChevronDown, Sparkles } from "lucide-svelte";
  
  import GroundStationMap from "$lib/components/operations/GroundStationMap.svelte";
  import AnomalyTimelinePlot from "$lib/components/charts/AnomalyTimelinePlot.svelte";
  import AnomalyContributionChart from "$lib/components/charts/AnomalyContributionChart.svelte";

  import DashboardShowcase from "$lib/components/DashboardShowcase.svelte";

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
  // Realistic 'Subtle Thermal Anomaly' scenario matching ML-Report features
  const mockExpected = { batt_voltage: 7.8, temp_batt_b: 15.0, batt_current: 1.2, temp_batt_a: 15.1 };
  const mockActual = { batt_voltage: 7.7, temp_batt_b: 14.8, batt_current: 1.3, temp_batt_a: 15.1 };
  const mockScaledExpected = { batt_voltage: -0.95, temp_batt_b: 0.1, batt_current: -0.9, temp_batt_a: 0.1 };
  const mockScaledActual = { batt_voltage: -1.1, temp_batt_b: 0.0, batt_current: -0.8, temp_batt_a: 0.1 };

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
    const contents = gsap.utils.toArray('.story-content', node) as HTMLElement[];

    // Ensure first visual is visible, others hidden
    gsap.set(visuals, { autoAlpha: 0, scale: 0.95, zIndex: 0 });
    gsap.set(visuals[0], { autoAlpha: 1, scale: 1, zIndex: 10 });

    // Hide ALL story-content elements initially — ScrollTrigger will reveal them
    gsap.set(contents, { autoAlpha: 0, y: 80 });

    steps.forEach((step, index) => {
      const content = step.querySelector('.story-content');
      
      if (content) {
        // Create a single timeline that spans the entire time this step is near the viewport
        const tl = gsap.timeline({
          scrollTrigger: {
            trigger: step,
            start: "top 85%", // Starts a bit lower to give room
            end: "bottom 15%", // Escapes a bit higher
            scrub: 1.5
          }
        });

        tl.fromTo(content, 
          { autoAlpha: 0, y: 80 },
          { autoAlpha: 1, y: 0, duration: 1, ease: "none" }
        )
        // Hold state perfectly still while the right-side visual is showcased
        .to({}, { duration: 3 })
        // Fade out smoothly as it gets pushed up by the next step
        .to(content, { autoAlpha: 0, y: -80, duration: 1, ease: "none" });
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
  <title>Wedjat | The Mission Control Standard</title>
</svelte:head>

<div class="relative z-10 w-full">
  
  <!-- 1. HERO SECTION -->
  <section id="hero" class="mx-auto max-w-7xl px-4 lg:px-8">
    <div use:gsapAction={{ animation: heroAnim }} class="grid min-h-[65vh] grid-cols-1 lg:grid-cols-2 items-center gap-8 pt-4 pb-12">
      
      <!-- Hero Text (Left) -->
      <div class="space-y-6 text-center lg:text-left z-20">
        <div class="hero-badge invisible inline-flex items-center gap-2 rounded-full border border-brand/40 bg-brand/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-brand shadow-[0_0_15px_rgba(139,92,246,0.3)] backdrop-blur-md">
          <Radio class="size-4 animate-pulse" />
          Edge Telemetry Monitoring
        </div>
        <div class="space-y-4">
          <h1 class="hero-title invisible text-5xl font-black tracking-tight text-ink sm:text-6xl lg:text-7xl leading-[1.05] drop-shadow-lg">
            Amateur satellite telemetry <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand to-info">powered by machine learning.</span>
          </h1>
          <p class="hero-desc invisible text-lg leading-7 text-ink-2 md:text-xl font-medium max-w-xl mx-auto lg:mx-0">
            Real-time telemetry decoding, orbital pass predictions, and unsupervised VAE anomaly detection for amateur CubeSat ground stations.
          </p>
        </div>
      </div>

      <!-- Hero Visual (Right) -->
      <div class="hero-visual invisible relative flex items-center justify-center h-[300px] lg:h-full w-full mt-8 lg:mt-0">
        <div class="absolute inset-0 bg-brand/10 blur-[100px] rounded-full aspect-square w-3/4 m-auto"></div>
        <!-- Orbital Rings Animation -->
        <div class="relative flex items-center justify-center size-64 lg:size-80 scale-75 sm:scale-100">
          <!-- Center Node -->
          <div class="absolute z-10 size-12 lg:size-14 rounded-full bg-surface border-2 border-brand shadow-[0_0_30px_rgba(139,92,246,0.8)] flex items-center justify-center">
             <Satellite class="size-5 lg:size-6 text-brand animate-pulse" />
          </div>
          <!-- Orbit Ring 1 -->
          <div class="absolute size-full rounded-full border border-brand/30 animate-[spin_10s_linear_infinite]">
             <div class="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 size-3 lg:size-4 rounded-full bg-info shadow-[0_0_15px_rgba(56,189,248,0.8)]"></div>
          </div>
          <!-- Orbit Ring 2 -->
          <div class="absolute size-48 lg:size-60 rounded-full border border-info/20 animate-[spin_15s_linear_infinite_reverse]">
             <div class="absolute bottom-0 left-1/2 -translate-x-1/2 translate-y-1/2 size-2.5 lg:size-3 rounded-full bg-brand shadow-[0_0_10px_rgba(139,92,246,0.8)]"></div>
          </div>
        </div>
      </div>

    </div>
  </section>

  <!-- 2. STICKY STORY SECTION -->
  <section id="story" use:gsapAction={{ animation: stickyStoryAnim }} class="mx-auto max-w-7xl px-4 lg:px-8 relative mt-12 mb-12">
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 relative">
      
      <!-- LEFT COLUMN: The Scrolling Text Steps -->
      <div class="flex flex-col w-full z-20 pb-0 lg:pb-[25vh]">
        
        <!-- Step 1 -->
        <div class="story-step min-h-[90vh] lg:h-[150vh] relative pr-0 lg:pr-8 flex flex-col justify-center lg:block">
          <div class="relative lg:sticky top-auto lg:top-[35%] w-full">
            <div class="story-content w-full flex flex-col justify-center">
              <div class="space-y-4">
                <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-brand">
                  <Satellite class="size-5" /> Phase 1: Contact
                </div>
                <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                  Orbital Pass <br/><span class="text-ink-2 font-medium">Predictions & Planning</span>
                </h2>
                <p class="text-lg text-ink-3 leading-relaxed">
                  Predict when satellites cross your local horizon. Wedjat computes high-precision skyplots, pass timelines, and visibility windows for your specific ground station coordinates.
                </p>
              </div>
              
              <!-- Mobile Visual -->
              <div class="lg:hidden mt-10 w-full aspect-[4/3] rounded-2xl border border-brand/20 bg-panel/50 p-2 shadow-[0_0_40px_rgba(139,92,246,0.1)] pointer-events-none">
                <GroundStationMap 
                  location={{ lat: 30.0626, lon: 31.2497, label: "Cairo, Egypt", elevationM: 23 }}
                  selectedTrack={previewTrack}
                  previewMode={true}
                />
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2 -->
        <div class="story-step min-h-[90vh] lg:h-[150vh] relative pr-0 lg:pr-8 flex flex-col justify-center lg:block">
          <div class="relative lg:sticky top-auto lg:top-[35%] w-full">
            <div class="story-content w-full flex flex-col justify-center">
              <div class="space-y-4">
                <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-ok">
                  <Zap class="size-5" /> Phase 2: Ingress
                </div>
                <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                  Real-Time WebSocket <br/><span class="text-ink-2 font-medium">Telemetry Ingress</span>
                </h2>
                <p class="text-lg text-ink-3 leading-relaxed">
                  Stream telemetry frames directly to your browser as they arrive. Wedjat establishes high-performance WebSockets to decode telemetry fields (battery, currents, temperature) with sub-second latency.
                </p>
                <div class="flex items-center gap-4 mt-2">
                   <div class="flex items-center gap-2 rounded-full border border-ok/20 bg-ok/10 px-4 py-2 text-sm font-semibold text-ok">
                     <Activity class="size-4" /> WebSocket Native
                   </div>
                </div>
              </div>

              <!-- Mobile Visual -->
              <div class="lg:hidden mt-10 w-full rounded-2xl border border-ok/20 bg-ok/5 p-4 shadow-[0_0_40px_rgba(20,184,166,0.1)]">
                <div class="flex items-center justify-between mb-4">
                  <p class="chart-card-title !mb-0 flex items-center gap-2 text-ok">
                    <BrainCircuit class="size-4" /> Live Anomaly Detection
                  </p>
                  <div class="flex items-center gap-2">
                    <span class="relative flex h-2 w-2">
                      <span class="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                      <span class="relative inline-flex h-2 w-2 rounded-full bg-emerald-500"></span>
                    </span>
                    <span class="text-[10px] font-bold text-emerald-500 uppercase tracking-widest hidden sm:block">Live Sync</span>
                  </div>
                </div>
                <div class="h-64 relative overflow-hidden rounded-lg bg-surface/50 p-2">
                  <AnomalyTimelinePlot frames={mockFrames} threshold={0.45} selectedTimestamp={null} height={200} />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 3 -->
        <div class="story-step min-h-[90vh] lg:h-[150vh] relative pr-0 lg:pr-8 flex flex-col justify-center lg:block">
          <div class="relative lg:sticky top-auto lg:top-[35%] w-full">
            <div class="story-content w-full flex flex-col justify-center">
              <div class="space-y-4">
                <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-critical">
                  <BrainCircuit class="size-5" /> Phase 3: Intelligence
                </div>
                <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                  Unsupervised VAE <br/><span class="text-ink-2 font-medium">Anomaly Detection</span>
                </h2>
                <p class="text-lg text-ink-3 leading-relaxed">
                  Identify complex, multivariate anomalies. Our edge-deployed Variational Autoencoder learns normal telemetry correlations, flagging subtle issues (like thermal runaway) based on reconstruction error.
                </p>
              </div>

              <!-- Mobile Visual -->
              <div class="lg:hidden mt-10 w-full rounded-2xl border border-brand/20 shadow-[0_0_40px_rgba(139,92,246,0.1)] p-4">
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

        <!-- Step 4 -->
        <div class="story-step min-h-[90vh] lg:h-[150vh] relative pr-0 lg:pr-8 flex flex-col justify-center lg:block">
          <div class="relative lg:sticky top-auto lg:top-[35%] w-full">
            <div class="story-content w-full flex flex-col justify-center">
              <div class="space-y-4">
                <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-critical">
                  <ShieldAlert class="size-5 animate-pulse" /> Phase 4: Security & Astrodynamics
                </div>
                <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                  State Vector Tracking <br/><span class="text-ink-2 font-medium">& Conjunction Risk</span>
                </h2>
                <p class="text-lg text-ink-3 leading-relaxed">
                  Real-time classical orbital elements (COE) and Cartesian state vector monitoring. Wedjat propagates orbits dynamically via SGP4, tracking satellite coordinate trends and calculating collision probabilities with the mathematically rigorous **Foster (1992)** covariance model.
                </p>
              </div>

              <!-- Mobile Visual -->
              <div class="lg:hidden mt-10 w-full rounded-2xl border border-critical/20 bg-critical/5 p-4 shadow-[0_0_40px_rgba(239,68,68,0.1)]">
                <div class="flex items-center justify-between mb-4 border-b border-border/50 pb-3">
                  <p class="chart-card-title !mb-0 flex items-center gap-2 text-critical">
                    <ShieldAlert class="size-4 animate-pulse" /> Conjunction Risk Assessment
                  </p>
                  <span class="text-[9px] font-bold text-critical uppercase tracking-widest bg-critical/10 px-2.5 py-1 rounded-full">Threat Alert</span>
                </div>
                <div class="space-y-4">
                  <div class="flex justify-between items-center bg-black/20 p-3 rounded-lg border border-border/50">
                    <div>
                      <p class="text-[10px] text-ink-3 uppercase font-bold tracking-wider">Secondary Object</p>
                      <p class="text-sm font-bold text-ink font-mono mt-0.5">NEMO-HD (46277)</p>
                    </div>
                    <div class="text-right">
                      <p class="text-[10px] text-ink-3 uppercase font-bold tracking-wider">Miss Distance</p>
                      <p class="text-sm font-bold text-ink-2 font-mono mt-0.5">10.07 km</p>
                    </div>
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div class="bg-black/10 p-3 rounded-lg border border-border/50">
                      <p class="text-[9px] text-ink-3 uppercase font-bold tracking-wider">Time to TCA</p>
                      <p class="text-sm font-mono font-bold text-brand mt-0.5">T-23:28:47</p>
                    </div>
                    <div class="bg-black/10 p-3 rounded-lg border border-border/50">
                      <p class="text-[9px] text-ink-3 uppercase font-bold tracking-wider">Collision Prob (Foster)</p>
                      <p class="text-sm font-mono font-bold text-critical mt-0.5">1.29e-6</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 5 -->
        <div class="story-step min-h-[90vh] lg:h-[150vh] relative pr-0 lg:pr-8 flex flex-col justify-center lg:block">
          <div class="relative lg:sticky top-auto lg:top-[35%] w-full">
            <div class="story-content w-full flex flex-col justify-center">
              <div class="space-y-4">
                <div class="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-info">
                  <Activity class="size-5" /> Phase 5: Space Physics & Prognostics
                </div>
                <h2 class="text-4xl lg:text-5xl font-black tracking-tight text-ink leading-tight">
                  Exospheric Density <br/><span class="text-ink-2 font-medium">& Decay Forecasting</span>
                </h2>
                <p class="text-lg text-ink-3 leading-relaxed">
                  Long-term decay prognostics under real solar weather. Wedjat models localized atmospheric drag using the **NRLMSISE-00** model, using geomagnetic indicators (F10.7, Kp) to drive machine learning ensembles forecasting 7-day and 30-day semi-major axis decay.
                </p>
              </div>

              <!-- Mobile Visual -->
              <div class="lg:hidden mt-10 w-full rounded-2xl border border-info/20 bg-info/5 p-4 shadow-[0_0_40px_rgba(56,189,248,0.1)]">
                <div class="flex items-center justify-between mb-4 border-b border-border/50 pb-3">
                  <p class="chart-card-title !mb-0 flex items-center gap-2 text-info">
                    <Activity class="size-4" /> Physics-Based Decay Forecast
                  </p>
                  <span class="text-[9px] font-bold text-info uppercase tracking-widest bg-info/10 px-2.5 py-1 rounded-full">NRLMSISE-00</span>
                </div>
                <div class="space-y-4">
                  <div class="grid grid-cols-3 gap-3">
                    <div class="bg-black/10 p-2.5 rounded-lg border border-border/50 text-center">
                      <p class="text-[8px] text-ink-3 uppercase font-bold">Solar Flux (F10.7)</p>
                      <p class="text-xs font-mono font-bold text-ink mt-0.5">116.8 sfu</p>
                    </div>
                    <div class="bg-black/10 p-2.5 rounded-lg border border-border/50 text-center">
                      <p class="text-[8px] text-ink-3 uppercase font-bold">Geomagnetic (Kp)</p>
                      <p class="text-xs font-mono font-bold text-ink mt-0.5">1.7 idx</p>
                    </div>
                    <div class="bg-black/10 p-2.5 rounded-lg border border-border/50 text-center">
                      <p class="text-[8px] text-ink-3 uppercase font-bold">Exo Temp (T_inf)</p>
                      <p class="text-xs font-mono font-bold text-ink mt-0.5">842.7 K</p>
                    </div>
                  </div>
                  <div class="bg-black/20 p-3 rounded-lg border border-border/50">
                    <div class="flex justify-between items-center mb-1">
                      <span class="text-[10px] text-ink-2 font-bold">Predicted Orbit Drop</span>
                      <span class="text-[10px] text-brand font-bold">7-Day Ensemble</span>
                    </div>
                    <div class="flex items-baseline gap-1.5">
                      <span class="text-xl font-black text-brand font-mono">0.09</span>
                      <span class="text-xs text-ink-3 uppercase">km</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- RIGHT COLUMN: The Sticky Visuals -->
      <div class="hidden lg:block relative w-full h-full">
        <!-- Sticky container stays fixed to top of viewport while scrolling the left column -->
        <div class="sticky top-0 h-screen w-full flex items-center justify-center perspective-1000">
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

            <!-- Visual 4: Astrodynamics & Conjunctions -->
            <div class="story-visual absolute inset-0 w-full h-full flex flex-col justify-center">
              <div class="chart-card w-full shadow-[0_0_50px_rgba(239,68,68,0.15)] border-critical/20 bg-critical/5">
                <div class="flex items-center justify-between mb-4 border-b border-border/50 pb-3">
                  <p class="chart-card-title !mb-0 flex items-center gap-2 text-critical">
                    <ShieldAlert class="size-4 animate-pulse" /> Conjunction Risk Assessment
                  </p>
                  <span class="text-[9px] font-bold text-critical uppercase tracking-widest bg-critical/10 px-2.5 py-1 rounded-full">Threat Alert</span>
                </div>
                <div class="space-y-4">
                  <div class="flex justify-between items-center bg-black/20 p-3 rounded-lg border border-border/50">
                    <div>
                      <p class="text-[10px] text-ink-3 uppercase font-bold tracking-wider">Secondary Object</p>
                      <p class="text-sm font-bold text-ink font-mono mt-0.5">NEMO-HD (46277)</p>
                    </div>
                    <div class="text-right">
                      <p class="text-[10px] text-ink-3 uppercase font-bold tracking-wider">Miss Distance</p>
                      <p class="text-sm font-bold text-ink-2 font-mono mt-0.5">10.07 km</p>
                    </div>
                  </div>
                  <div class="grid grid-cols-2 gap-4">
                    <div class="bg-black/10 p-3 rounded-lg border border-border/50">
                      <p class="text-[9px] text-ink-3 uppercase font-bold tracking-wider">Time to TCA</p>
                      <p class="text-sm font-mono font-bold text-brand mt-0.5">T-23:28:47</p>
                    </div>
                    <div class="bg-black/10 p-3 rounded-lg border border-border/50">
                      <p class="text-[9px] text-ink-3 uppercase font-bold tracking-wider">Collision Prob (Foster)</p>
                      <p class="text-sm font-mono font-bold text-critical mt-0.5">1.29e-6</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Visual 5: Physics Decay Forecast -->
            <div class="story-visual absolute inset-0 w-full h-full flex flex-col justify-center">
              <div class="chart-card w-full shadow-[0_0_50px_rgba(56,189,248,0.15)] border-info/20 bg-info/5">
                <div class="flex items-center justify-between mb-4 border-b border-border/50 pb-3">
                  <p class="chart-card-title !mb-0 flex items-center gap-2 text-info">
                    <Activity class="size-4" /> Physics-Based Decay Forecast
                  </p>
                  <span class="text-[9px] font-bold text-info uppercase tracking-widest bg-info/10 px-2.5 py-1 rounded-full">NRLMSISE-00</span>
                </div>
                <div class="space-y-4">
                  <div class="grid grid-cols-3 gap-3">
                    <div class="bg-black/10 p-2.5 rounded-lg border border-border/50 text-center">
                      <p class="text-[8px] text-ink-3 uppercase font-bold">Solar Flux (F10.7)</p>
                      <p class="text-xs font-mono font-bold text-ink mt-0.5">116.8 sfu</p>
                    </div>
                    <div class="bg-black/10 p-2.5 rounded-lg border border-border/50 text-center">
                      <p class="text-[8px] text-ink-3 uppercase font-bold">Geomagnetic (Kp)</p>
                      <p class="text-xs font-mono font-bold text-ink mt-0.5">1.7 idx</p>
                    </div>
                    <div class="bg-black/10 p-2.5 rounded-lg border border-border/50 text-center">
                      <p class="text-[8px] text-ink-3 uppercase font-bold">Exo Temp (T_inf)</p>
                      <p class="text-xs font-mono font-bold text-ink mt-0.5">842.7 K</p>
                    </div>
                  </div>
                  <div class="bg-black/20 p-3 rounded-lg border border-border/50">
                    <div class="flex justify-between items-center mb-1">
                      <span class="text-[10px] text-ink-2 font-bold">Predicted Orbit Drop</span>
                      <span class="text-[10px] text-brand font-bold">7-Day Ensemble</span>
                    </div>
                    <div class="flex items-baseline gap-1.5">
                      <span class="text-xl font-black text-brand font-mono">0.09</span>
                      <span class="text-xs text-ink-3 uppercase">km</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

          </div>
        </div>
      </div>

    </div>
  </section>

  <!-- 2.5 HORIZONTAL DASHBOARD SHOWCASE -->
  <DashboardShowcase />

  <!-- 3. CTA SECTION (Edge to Edge Glass Parallax) -->
  <section class="relative w-full min-h-screen flex items-center justify-center overflow-hidden bg-surface/10 border-t border-border backdrop-blur-md">
    <!-- Subtle laser line at the top -->
    <div class="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-brand/40 to-transparent"></div>

    <!-- Minimal Premium Floor Reflection -->
    <div class="absolute bottom-0 left-1/2 -translate-x-1/2 w-full max-w-3xl h-64 bg-gradient-to-t from-brand/10 to-transparent pointer-events-none opacity-50"></div>
    <!-- Very tight, intense glow exclusively anchoring the button -->
    <div class="absolute bottom-10 left-1/2 -translate-x-1/2 w-96 h-32 bg-brand/20 blur-[80px] pointer-events-none rounded-full"></div>

    <!-- Content centered -->
    <div class="relative z-10 flex flex-col items-center justify-center space-y-8 text-center px-4 w-full max-w-4xl">
      <div class="size-20 rounded-full bg-brand/10 border border-brand/20 flex items-center justify-center shadow-[0_0_40px_rgba(139,92,246,0.3)] mb-4 relative">
         <div class="absolute inset-0 rounded-full border border-brand/30 animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite]"></div>
         <Radio class="size-10 text-brand animate-pulse" />
      </div>
      
      <h2 class="text-5xl lg:text-7xl font-black text-ink drop-shadow-md flex items-center justify-center gap-4">
        Ready for <span class="text-transparent bg-clip-text bg-gradient-to-r from-brand to-info">Launch.</span> <Sparkles class="size-10 text-brand hidden sm:block" />
      </h2>
      
      <p class="text-xl text-ink-3 max-w-2xl font-medium leading-relaxed">
        A robust telemetry monitoring pipeline. Predict upcoming satellite passes, monitor live downlinks over WebSockets, and run VAE anomaly inference at the edge.
      </p>
      
      <!-- Feature Mini-List -->
      <div class="flex flex-wrap justify-center gap-4 py-6">
        <div class="flex items-center gap-2 text-sm font-semibold text-ink-2 bg-panel/80 px-5 py-2.5 rounded-full border border-border backdrop-blur-md shadow-sm transition-transform hover:-translate-y-1 cursor-default">
           <Zap class="size-4 text-ok" /> Live WebSockets
        </div>
        <div class="flex items-center gap-2 text-sm font-semibold text-ink-2 bg-panel/80 px-5 py-2.5 rounded-full border border-border backdrop-blur-md shadow-sm transition-transform hover:-translate-y-1 cursor-default">
           <BrainCircuit class="size-4 text-brand" /> VAE ML Models
        </div>
        <div class="flex items-center gap-2 text-sm font-semibold text-ink-2 bg-panel/80 px-5 py-2.5 rounded-full border border-border backdrop-blur-md shadow-sm transition-transform hover:-translate-y-1 cursor-default">
           <ShieldAlert class="size-4 text-critical" /> Auto-Alerts
        </div>
      </div>

      <div class="pt-6">
        <a class="group relative inline-flex items-center gap-3 rounded-full bg-brand px-12 py-5 text-lg font-bold text-white shadow-[0_0_40px_rgba(139,92,246,0.6)] transition-all hover:scale-110 hover:bg-brand/90 hover:shadow-[0_0_60px_rgba(139,92,246,0.8)] overflow-hidden" href="/dashboard">
          <!-- Sparkle hover effect -->
          <div class="absolute inset-0 -translate-x-full bg-white/20 skew-x-12 transition-transform duration-700 ease-out group-hover:translate-x-full"></div>
          Start Wedjat
          <ChevronRight class="size-6 transition-transform group-hover:translate-x-2" />
        </a>
      </div>
    </div>
  </section>
</div>
