<script lang="ts">
  import { page } from "$app/stores";
  import { themeState, toggleTheme } from "$lib/theme.svelte";
  import { slide, fade, fly } from "svelte/transition";
  import { Home, Satellite, Zap, LineChart, Activity, Menu, X, Moon, Sun, BookOpen, BrainCircuit, Search, Crosshair } from "lucide-svelte";

  let { children } = $props();

  const dashboardLinks = [
    { href: "/dashboard", label: "Dashboard Home", icon: Home },
    { href: "/dashboard/operations", label: "Operations", icon: Satellite },
    { href: "/dashboard/tracker", label: "Tracker", icon: Crosshair },
    { href: "/dashboard/live", label: "Live Watcher", icon: Zap },
    { href: "/dashboard/inspector", label: "Inspector", icon: Search },
    { href: "/dashboard/analytics", label: "Analytics", icon: LineChart },
    { href: "/dashboard/ml", label: "ML Interface", icon: Activity },
  ];

  const analysisLinks = [
    { href: "/dashboard/eda", label: "EDA Report", icon: BookOpen },
    { href: "/dashboard/ml-report", label: "Model Analysis", icon: BrainCircuit },
    { href: "/dashboard/orbit-decay", label: "Orbit Decay AI", icon: Activity },
  ];

  let desktopSidebarOpen = $state(true);
  let mobileSidebarOpen = $state(false);

  function toggleSidebar() {
    if (typeof window !== 'undefined' && window.innerWidth < 768) {
      mobileSidebarOpen = !mobileSidebarOpen;
    } else {
      desktopSidebarOpen = !desktopSidebarOpen;
    }
  }

  function handleNavClick() {
    mobileSidebarOpen = false;
  }
</script>

<div class="flex min-h-screen bg-surface text-ink transition-colors overflow-x-hidden">
  <!-- Sidebar -->
  <aside in:fly={{ x: -50, duration: 600, delay: 100 }} class="fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 flex-col border-r border-border bg-panel shadow-panel backdrop-blur transition-all duration-300 md:sticky md:top-0 md:h-screen {mobileSidebarOpen ? 'translate-x-0' : '-translate-x-full'} {desktopSidebarOpen ? 'md:translate-x-0 md:ml-0' : 'md:-translate-x-full md:-ml-64'}">
    <div class="flex h-16 items-center justify-between border-b border-border px-6">
      <a class="text-lg font-semibold tracking-[0.18em] text-brand uppercase" href="/">
        Watchdog
      </a>
      <button class="text-ink-2 hover:text-brand transition-colors p-1.5 -mr-1.5 rounded-lg hover:bg-surface hidden md:block" onclick={toggleSidebar} aria-label="Collapse sidebar">
        <Menu class="size-5" />
      </button>
      <button class="md:hidden text-ink-2 hover:text-brand transition-colors p-1.5 -mr-1.5 rounded-lg hover:bg-surface" onclick={toggleSidebar} aria-label="Close sidebar">
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
              class="group flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-300 {$page.url.pathname === link.href ? 'bg-brand/10 text-brand shadow-inner shadow-brand/5' : 'text-ink-2 hover:bg-surface/60 hover:text-ink hover:translate-x-1 hover:shadow-sm'}"
              onclick={handleNavClick}
            >
              <Icon class="size-4 opacity-80 transition-transform duration-300 {$page.url.pathname === link.href ? 'scale-110' : 'group-hover:scale-110'}" />
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
              class="group flex items-center gap-3 rounded-xl px-4 py-2.5 text-sm font-medium transition-all duration-300 {$page.url.pathname === link.href ? 'bg-brand/10 text-brand shadow-inner shadow-brand/5' : 'text-ink-2 hover:bg-surface/60 hover:text-ink hover:translate-x-1 hover:shadow-sm'}"
              onclick={handleNavClick}
            >
              <Icon class="size-4 opacity-80 transition-transform duration-300 {$page.url.pathname === link.href ? 'scale-110' : 'group-hover:scale-110'}" />
              {link.label}
            </a>
          {/each}
        </div>
      </div>
    </nav>

    <div class="border-t border-border p-4 pb-24 md:pb-4">
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
  <div class="flex flex-1 flex-col min-h-0 overflow-hidden pb-16 md:pb-0">
    <!-- Topbar -->
    <header in:fly={{ y: -20, duration: 500, delay: 200 }} class="flex h-14 shrink-0 items-center border-b border-border bg-panel/80 backdrop-blur-md px-6 sticky top-0 z-30 transition-all duration-300 {desktopSidebarOpen ? 'md:-mt-14 md:border-b-transparent md:opacity-0 pointer-events-none' : 'md:mt-0 pointer-events-auto'}">
      <!-- Mobile Center Logo -->
      <a class="text-[13px] font-bold tracking-[0.2em] text-brand uppercase md:hidden absolute left-1/2 -translate-x-1/2" href="/">
        Watchdog
      </a>
      
      <!-- Desktop Burger & Logo -->
      <div class="hidden md:flex items-center gap-4">
        <button class="text-ink-2 hover:text-brand transition-colors p-1.5 -ml-1.5 rounded-lg hover:bg-surface pointer-events-auto" onclick={toggleSidebar} aria-label="Open sidebar">
          <Menu class="size-5" />
        </button>
        <a class="text-[13px] font-bold tracking-[0.2em] text-brand uppercase" href="/">
          Watchdog
        </a>
      </div>
    </header>

    <main class="flex-1 flex flex-col min-h-0 relative">
      <div class="absolute inset-0 w-full h-full flex flex-col overflow-y-auto overflow-x-hidden p-3 sm:p-5 md:p-8 lg:p-10">
        {@render children()}
      </div>
    </main>
  </div>
  
  <!-- Premium Mobile Bottom Navigation -->
  <nav class="md:hidden fixed bottom-0 left-0 right-0 z-50 flex h-16 items-center justify-around border-t border-border bg-panel/90 backdrop-blur-xl pb-safe">
    {#each dashboardLinks.slice(0, 4) as link}
      {@const Icon = link.icon}
      {@const isActive = $page.url.pathname === link.href}
      <a
        href={link.href}
        class="flex flex-col items-center justify-center w-full h-full gap-1 transition-colors {isActive ? 'text-brand' : 'text-ink-3 hover:text-ink-2'}"
      >
        <div class="relative flex items-center justify-center {isActive ? 'scale-110' : 'scale-100'} transition-transform duration-300">
          <Icon class="size-[1.1rem]" />
          {#if isActive}
            <span class="absolute -top-1 -right-1 h-1.5 w-1.5 rounded-full bg-brand shadow-[0_0_8px_rgba(139,92,246,0.6)]"></span>
          {/if}
        </div>
        <span class="text-[9px] font-medium tracking-wide {isActive ? 'text-brand' : 'text-ink-3'}">
          {link.label.split(' ')[0]}
        </span>
      </a>
    {/each}
    <button
      onclick={toggleSidebar}
      class="flex flex-col items-center justify-center w-full h-full gap-1 transition-colors text-ink-3 hover:text-ink-2"
    >
      <Menu class="size-[1.1rem]" />
      <span class="text-[9px] font-medium tracking-wide text-ink-3">Menu</span>
    </button>
  </nav>
</div>

<!-- Backdrop -->
{#if mobileSidebarOpen}
  <button
    class="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden cursor-default"
    onclick={toggleSidebar}
    aria-label="Close sidebar overlay"
  ></button>
{/if}
