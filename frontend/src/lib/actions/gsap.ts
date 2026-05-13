import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/dist/ScrollTrigger';

// Register plugins once
if (typeof window !== 'undefined') {
  gsap.registerPlugin(ScrollTrigger);
}

type GsapActionOptions = {
  animation: (node: HTMLElement, context: gsap.Context) => void;
};

export function gsapAction(node: HTMLElement, options: GsapActionOptions) {
  let ctx = gsap.context(() => {
    if (options && typeof options.animation === 'function') {
      options.animation(node, ctx);
    }
  }, node);

  return {
    update(newOptions: GsapActionOptions) {
      ctx.revert();
      ctx = gsap.context(() => {
        if (newOptions && typeof newOptions.animation === 'function') {
          newOptions.animation(node, ctx);
        }
      }, node);
    },
    destroy() {
      ctx.revert();
    }
  };
}
