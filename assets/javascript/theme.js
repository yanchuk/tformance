/**
 * Theme management for dark/light mode toggle
 * Works with DaisyUI themes: 'tformance' (dark) and 'tformance-light' (light)
 */

function syncDarkMode() {
  const stored = localStorage.getItem('theme') || 'system';
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  let themeName;
  if (stored === 'system') {
    themeName = prefersDark ? 'tformance' : 'tformance-light';
  } else {
    themeName = stored; // Use stored theme name directly
  }

  const isDark = themeName === 'tformance';

  // Apply theme
  document.documentElement.setAttribute('data-theme', themeName);
  document.documentElement.classList.toggle('dark', isDark);
  document.documentElement.classList.toggle('light', !isDark);
}

// Apply on page load
syncDarkMode();

// Listen for system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (localStorage.getItem('theme') === 'system') syncDarkMode();
});

// Export globally for Alpine.js onclick handlers
window.syncDarkMode = syncDarkMode;
