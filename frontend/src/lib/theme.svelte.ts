import { browser } from '$app/environment';

class Theme {
  isLight = $state(false);

  constructor() {
    if (browser) {
      const stored = localStorage.getItem('theme');
      if (stored) {
        this.isLight = stored === 'light';
      } else {
        this.isLight = window.matchMedia('(prefers-color-scheme: light)').matches;
      }
      
      // Automatically sync DOM when state changes
      $effect.root(() => {
        $effect(() => {
          if (this.isLight) {
            document.documentElement.classList.add('light');
            localStorage.setItem('theme', 'light');
          } else {
            document.documentElement.classList.remove('light');
            localStorage.setItem('theme', 'dark');
          }
        });
      });
    }
  }

  toggle() {
    this.isLight = !this.isLight;
  }
}

export const themeState = new Theme();

export function toggleTheme() {
  themeState.toggle();
}
