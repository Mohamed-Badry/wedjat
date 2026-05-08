export const themeState = $state({
  isLight: false,
});

export function toggleTheme() {
  themeState.isLight = !themeState.isLight;
  if (typeof document !== 'undefined') {
    document.documentElement.classList.toggle('light', themeState.isLight);
  }
}
