<script lang="ts">
  import { fade } from "svelte/transition";
  import gsap from "gsap";
  import { ScrollToPlugin } from "gsap/dist/ScrollToPlugin";

  let scrollY = $state(0);
  let isBottom = $state(false);

  $effect(() => {
    gsap.registerPlugin(ScrollToPlugin);
    
    const checkBottom = () => {
      isBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 50;
    };
    window.addEventListener('scroll', checkBottom);
    window.addEventListener('resize', checkBottom);
    checkBottom();
    return () => {
      window.removeEventListener('scroll', checkBottom);
      window.removeEventListener('resize', checkBottom);
    };
  });

  function scrollDown() {
    const targets = Array.from(document.querySelectorAll('.story-step, section:not(#story, #hero)'));
    let targetY = window.scrollY + window.innerHeight;
    
    for (const target of targets) {
      const rect = target.getBoundingClientRect();
      // If the top of the target is below the current viewport top (with a 10px buffer)
      if (rect.top > 10) {
        targetY = window.scrollY + rect.top;
        break;
      }
    }

    gsap.to(window, { 
      duration: 1.0, 
      scrollTo: targetY, 
      ease: "power2.inOut" 
    });
  }
</script>

<svelte:window bind:scrollY={scrollY} />

{#if !isBottom}
  <button 
    onclick={scrollDown}
    in:fade={{ duration: 800, delay: 1000 }}
    out:fade={{ duration: 300 }}
    class="fixed bottom-8 left-1/2 -translate-x-1/2 z-50 flex flex-col items-center opacity-60 hover:opacity-100 transition-opacity cursor-pointer group animate-bounce"
    aria-label="Scroll down"
  >
    <!-- Minimalist mouse silhouette -->
    <div class="w-5 h-8 rounded-full border border-ink-3 group-hover:border-brand transition-colors flex justify-center pt-1.5 shadow-sm backdrop-blur-sm bg-surface/30">
      <div class="w-1 h-1.5 bg-ink-3 group-hover:bg-brand rounded-full animate-[bounce_2s_infinite] transition-colors"></div>
    </div>
  </button>
{/if}
