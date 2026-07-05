<script lang="ts">
  import "../app.css";
  import { page } from "$app/stores";
  let { children } = $props();
</script>

<svelte:head>
  <title>Wedjat | AI-Powered Satellite Analytics</title>
  <meta name="description" content="Real-time anomaly detection, telemetry monitoring, and orbital decay intelligence for amateur CubeSats." />
  
  <meta property="og:type" content="website" />
  <meta property="og:title" content="Wedjat | AI-Powered Satellite Analytics" />
  <meta property="og:description" content="Real-time anomaly detection, telemetry monitoring, and orbital decay intelligence for amateur CubeSats." />
  <meta property="og:image" content={`${$page.url.origin}/og_image.png`} />
  <meta property="og:image:width" content="1200" />
  <meta property="og:image:height" content="630" />

  <meta name="twitter:card" content="summary_large_image" />
  <meta name="twitter:title" content="Wedjat | AI-Powered Satellite Analytics" />
  <meta name="twitter:description" content="Real-time anomaly detection, telemetry monitoring, and orbital decay intelligence for amateur CubeSats." />
  <meta name="twitter:image" content={`${$page.url.origin}/og_image.png`} />
  <meta name="theme-color" content="#8B5CF6" />
</svelte:head>

{@render children()}
