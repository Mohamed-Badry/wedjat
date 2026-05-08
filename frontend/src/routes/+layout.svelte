<script lang="ts">
  import "../app.css";
  let { children } = $props();
</script>

<svelte:head>
  <title>Project Watchdog</title>
  <meta
    name="description"
    content="Project Watchdog is a Bun-powered SvelteKit interface for real-time amateur satellite telemetry monitoring."
  />
</svelte:head>

{@render children()}
