<script lang="ts">
  import { gsapAction } from "$lib/actions/gsap";
  import gsap from "gsap";
  import { Activity, Radio, LineChart, ChevronRight } from "lucide-svelte";
  
  // Variables for easy customization
  const TITLE = "Edge Telemetry Monitoring";
  const SUBTITLE = "Real-time satellite health, built on the core used for offline ML analysis.";
  const DESCRIPTION = "This dashboard offers live pass monitoring, historical anomaly tracking via VAE, and predictive operations.";
  const DASHBOARD_LINK = "/dashboard";
  const TEAM_LINK = "/team";

  // GSAP Animation Functions
  function staggerFeatures(node: HTMLElement, ctx: gsap.Context) {
    gsap.from(node.children, {
      y: 40,
      opacity: 0,
      duration: 0.8,
      stagger: 0.15,
      ease: "power3.out",
      scrollTrigger: {
        trigger: node,
        start: "top 85%",
      }
    });
  }

  function heroAnim(node: HTMLElement, ctx: gsap.Context) {
    gsap.from(node.children, {
      y: 30,
      opacity: 0,
      duration: 1,
      stagger: 0.1,
      ease: "power2.out",
    });
  }
</script>

<section class="mx-auto max-w-7xl space-y-24 py-16 lg:py-24">
  <!-- Hero Section -->
  <div use:gsapAction={{ animation: heroAnim }} class="space-y-8 text-center md:text-left">
    <div class="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-brand shadow-sm">
      <Radio class="size-4" />
      {TITLE}
    </div>

    <div class="space-y-6">
      <h1 class="max-w-4xl text-5xl font-semibold tracking-tight text-ink sm:text-7xl">
        {SUBTITLE}
      </h1>
      <p class="max-w-2xl text-lg leading-8 text-ink-2 md:text-xl">
        {DESCRIPTION}
      </p>
    </div>

    <div class="flex flex-wrap items-center justify-center gap-4 md:justify-start">
      <a
        class="group flex items-center gap-2 rounded-full bg-brand px-6 py-3.5 text-sm font-semibold text-white shadow-md shadow-brand/20 transition hover:-translate-y-0.5 hover:bg-brand/90 hover:shadow-lg hover:shadow-brand/30"
        href={DASHBOARD_LINK}
      >
        Enter Dashboard
        <ChevronRight class="size-4 transition-transform group-hover:translate-x-1" />
      </a>
      <a
        class="rounded-full border border-border bg-surface px-6 py-3.5 text-sm font-semibold text-ink shadow-sm transition hover:-translate-y-0.5 hover:border-brand hover:text-brand"
        href={TEAM_LINK}
      >
        Meet the Team
      </a>
    </div>
  </div>

  <!-- Feature Highlights -->
  <div class="space-y-16">
    <div class="text-center md:text-left">
      <h2 class="text-3xl font-semibold tracking-tight text-ink md:text-4xl">Platform Capabilities</h2>
      <p class="mt-4 text-ink-2">Powerful tools derived from the offline machine learning lab, now streaming at the edge.</p>
    </div>

    <div use:gsapAction={{ animation: staggerFeatures }} class="grid gap-8 md:grid-cols-3">
      <!-- Feature 1 -->
      <div class="group rounded-3xl border border-border bg-panel p-8 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-md">
        <div class="mb-6 flex size-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
          <Activity class="size-6" />
        </div>
        <h3 class="mb-3 text-xl font-semibold text-ink">Live Telemetry</h3>
        <p class="text-sm leading-relaxed text-ink-2">
          Real-time decoding and monitoring. Connect directly to your local MQTT broker and watch frames arrive and parse into actionable metrics instantly.
        </p>
      </div>

      <!-- Feature 2 -->
      <div class="group rounded-3xl border border-border bg-panel p-8 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-md">
        <div class="mb-6 flex size-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
          <LineChart class="size-6" />
        </div>
        <h3 class="mb-3 text-xl font-semibold text-ink">Machine Learning Insights</h3>
        <p class="text-sm leading-relaxed text-ink-2">
          VAE anomaly detection and feature correlation. Visualize the reconstruction loss timeline and explore deep correlations across subsystems.
        </p>
      </div>

      <!-- Feature 3 -->
      <div class="group rounded-3xl border border-border bg-panel p-8 shadow-sm backdrop-blur transition duration-300 hover:-translate-y-1 hover:border-brand/30 hover:shadow-md">
        <div class="mb-6 flex size-12 items-center justify-center rounded-2xl bg-brand/10 text-brand">
          <Radio class="size-6" />
        </div>
        <h3 class="mb-3 text-xl font-semibold text-ink">Pass Operations</h3>
        <p class="text-sm leading-relaxed text-ink-2">
          Predictive tracking and skyplot visualizations. Plan your recording windows and track satellite dynamics against your exact ground station location.
        </p>
      </div>
    </div>
  </div>
</section>
