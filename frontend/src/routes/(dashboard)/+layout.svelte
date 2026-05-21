<script lang="ts">
  import { page } from "$app/stores";
  import { themeState, toggleTheme } from "$lib/theme.svelte";
  import { slide } from "svelte/transition";
  import { Home, Satellite, Zap, LineChart, Activity, Menu, X, Moon, Sun, BookOpen, BrainCircuit, Search } from "lucide-svelte";

  let { children } = $props();

  const dashboardLinks = [
    { href: "/dashboard", label: "Dashboard Home", icon: Home },
    { href: "/dashboard/analytics", label: "Analytics", icon: LineChart },
    { href: "/dashboard/inspector", label: "Inspector", icon: Search },
    { href: "/dashboard/operations", label: "Operations", icon: Satellite },
    { href: "/dashboard/live", label: "Live Watcher", icon: Zap },
    { href: "/dashboard/ml", label: "ML Interface", icon: Activity },
  ];

  const analysisLinks = [
    { href: "/dashboard/eda", label: "EDA Report", icon: BookOpen },
    { href: "/dashboard/ml-report", label: "Model Analysis", icon: BrainCircuit },
  ];

  let sidebarOpen = $state(false);

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }
</script>

<div class="flex min-h-screen bg-surface text-ink transition-colors">
  <!-- Sidebar -->
  <aside class="fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-border bg-panel shadow-panel backdrop-blur transition-transform duration-300 md:translate-x-0 {sidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:sticky md:top-0 md:h-screen md:flex md:w-64">
    <div class="flex h-16 items-center justify-between border-b border-border px-6">
      <a class="text-lg font-semibold tracking-[0.18em] text-brand uppercase" href="/">
        Watchdog
      </a>
      <button class="md:hidden text-ink hover:text-brand transition-colors" onclick={toggleSidebar}>
        <X class="size-5" />
      </button>
    </div>
    
    <nav class="flex-1 space-y-6 overflow-y-auto p-4">
      <div>
        <p class="mb-2 px-4 text-[10px] font-semibold uppercase tracking-wider text-ink-3">Live Dashboards</p>
        <div class="space-y-1">
          {#each dashboardLinks as link}
            {@const Icon = link.icon}
            <a
              href={link.href}
              class="flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors {$page.url.pathname === link.href ? 'bg-brand/10 text-brand' : 'text-ink-2 hover:bg-surface hover:text-ink'}"
              onclick={() => sidebarOpen = false}
            >
              <Icon class="size-4 opacity-80" />
              {link.label}
            </a>
          {/each}
        </div>
      </div>

      <div>
        <p class="mb-2 px-4 text-[10px] font-semibold uppercase tracking-wider text-ink-3">Notebooks</p>
        <div class="space-y-1">
          {#each analysisLinks as link}
            {@const Icon = link.icon}
            <a
              href={link.href}
              class="flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-colors {$page.url.pathname === link.href ? 'bg-brand/10 text-brand' : 'text-ink-2 hover:bg-surface hover:text-ink'}"
              onclick={() => sidebarOpen = false}
            >
              <Icon class="size-4 opacity-80" />
              {link.label}
            </a>
          {/each}
        </div>
      </div>
    </nav>

    <div class="border-t border-border p-4">
      <button
        onclick={toggleTheme}
        class="group relative flex w-full items-center justify-between overflow-hidden rounded-xl border border-border bg-surface/50 px-4 py-3 text-sm font-medium text-ink-2 transition-all hover:border-brand/50 hover:bg-surface hover:text-ink hover:shadow-sm"
      >
        <!-- Subtle background glow on hover -->
        <div class="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-brand/5 to-transparent transition-transform duration-500 group-hover:translate-x-full"></div>
        
        <span class="relative z-10">{themeState.isLight ? 'Light Mode' : 'Dark Mode'}</span>
        <div class="relative z-10 flex h-6 w-6 items-center justify-center rounded-md bg-panel shadow-sm">
          {#if themeState.isLight}
            <Sun class="size-3.5 text-amber-500" />
          {:else}
            <Moon class="size-3.5 text-blue-400" />
          {/if}
        </div>
      </button>
    </div>
  </aside>

  <!-- Main Content -->
  <div class="flex flex-1 flex-col min-h-0 overflow-hidden">
    <!-- Topbar (mobile only) -->
    <header class="flex h-16 shrink-0 items-center justify-between border-b border-border bg-panel px-6 md:hidden">
      <button onclick={toggleSidebar} class="text-ink-2 hover:text-brand transition-colors">
        <Menu class="size-5" />
      </button>
      <a class="text-lg font-semibold tracking-[0.18em] text-brand uppercase" href="/">
        Watchdog
      </a>
      <div class="w-5"></div> <!-- Spacer for flex justify-between -->
    </header>

    <main class="flex-1 relative min-h-0">
      <div class="absolute inset-0 w-full h-full flex flex-col overflow-y-auto p-6 md:p-8 lg:p-10">
        {@render children()}
      </div>
    </main>
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
