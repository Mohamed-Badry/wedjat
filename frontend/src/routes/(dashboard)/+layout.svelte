<script lang="ts">
  import { page } from "$app/stores";
  import { themeState, toggleTheme } from "$lib/theme.svelte";

  let { children } = $props();

  const sidebarLinks = [
    { href: "/dashboard", label: "Dashboard Home", icon: "⌂" },
    { href: "/dashboard/operations", label: "Operations", icon: "⎈" },
    { href: "/dashboard/live", label: "Live Watcher", icon: "⚡" },
    { href: "/dashboard/insights", label: "EDA & Insights", icon: "⚲" },
    { href: "/dashboard/ml", label: "ML Lab", icon: "⚛" },
  ];

  let sidebarOpen = $state(false);

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }
</script>

<div class="flex min-h-screen bg-surface text-ink transition-colors">
  <!-- Sidebar -->
  <aside class="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-panel shadow-panel backdrop-blur transition-transform md:translate-x-0 {sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:static md:flex md:w-64">
    <div class="flex h-16 items-center justify-between border-b border-border px-6">
      <a class="text-lg font-semibold tracking-[0.18em] text-brand uppercase" href="/">
        Watchdog
      </a>
      <button class="md:hidden text-ink hover:text-brand transition-colors" onclick={toggleSidebar}>✕</button>
    </div>
    
    <nav class="flex-1 space-y-1 p-4">
      {#each sidebarLinks as link}
        <a
          href={link.href}
          class="flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-medium transition-colors {$page.url.pathname === link.href ? 'bg-brand/10 text-brand' : 'text-ink-2 hover:bg-surface hover:text-ink'}"
          onclick={() => sidebarOpen = false}
        >
          <span class="text-lg opacity-80">{link.icon}</span>
          {link.label}
        </a>
      {/each}
    </nav>

    <div class="border-t border-border p-4">
      <button
        onclick={toggleTheme}
        class="flex w-full items-center justify-between rounded-xl px-4 py-3 text-sm font-medium text-ink-2 hover:bg-surface hover:text-ink transition-colors"
      >
        <span>Theme</span>
        <span class="text-lg">{themeState.isLight ? "☽" : "☀"}</span>
      </button>
    </div>
  </aside>

  <!-- Main Content -->
  <div class="flex flex-1 flex-col overflow-hidden">
    <!-- Topbar (mobile only) -->
    <header class="flex h-16 shrink-0 items-center justify-between border-b border-border bg-panel px-6 md:hidden">
      <button onclick={toggleSidebar} class="text-ink-2 hover:text-brand transition-colors">☰ Menu</button>
      <a class="text-lg font-semibold tracking-[0.18em] text-brand uppercase" href="/">
        Watchdog
      </a>
      <div class="w-16"></div> <!-- Spacer for flex justify-between -->
    </header>

    <main class="flex-1 overflow-auto p-6 md:p-8 lg:p-10">
      <div class="mx-auto max-w-6xl">
        {@render children()}
      </div>
    </main>

    <!-- Footer -->
    <footer class="mt-auto border-t border-border bg-panel px-6 py-4 text-center text-sm text-ink-3">
      <div class="flex justify-center gap-6">
        <a href="/" class="hover:text-brand transition-colors">Overview</a>
        <a href="/team" class="hover:text-brand transition-colors">Team</a>
        <a href="https://github.com" target="_blank" rel="noreferrer" class="hover:text-brand transition-colors">GitHub</a>
      </div>
      <p class="mt-2 text-xs opacity-60">gr_sat Watchdog Dashboard • Built with Svelte 5</p>
    </footer>
  </div>
</div>

<!-- Backdrop -->
{#if sidebarOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div
    class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
    onclick={toggleSidebar}
  ></div>
{/if}
