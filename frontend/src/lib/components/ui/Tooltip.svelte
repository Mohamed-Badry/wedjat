<script lang="ts">
  import { Info } from "lucide-svelte";
  
  let { text, class: className = "", align = "center" } = $props<{ 
    text: string; 
    class?: string;
    align?: "left" | "center" | "right";
  }>();
</script>

<!-- A pure CSS tooltip using group-hover. No JS state required. -->
<div class="group relative flex items-center {className}">
  <Info class="size-3 text-ink-3 hover:text-brand transition-colors cursor-pointer" />
  
  <!-- Tooltip Bubble -->
  <div class="pointer-events-none absolute top-full z-50 mt-2 opacity-0 transition-opacity duration-200 group-hover:opacity-100
    {align === 'center' ? 'left-1/2 -translate-x-1/2' : ''}
    {align === 'left' ? 'left-0' : ''}
    {align === 'right' ? 'right-0' : ''}
  ">
    <div class="w-max max-w-[250px] rounded-lg border border-border bg-panel px-3 py-2 text-[11px] leading-relaxed text-ink shadow-lg backdrop-blur-md">
      {text}
      <!-- Triangle Pointer -->
      <div class="absolute -top-1 h-2 w-2 rotate-45 border-l border-t border-border bg-panel
        {align === 'center' ? 'left-1/2 -translate-x-1/2' : ''}
        {align === 'left' ? 'left-3' : ''}
        {align === 'right' ? 'right-3' : ''}
      "></div>
    </div>
  </div>
</div>