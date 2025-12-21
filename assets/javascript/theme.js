/**
 * Theme management for dark/light mode toggle
 * Works with DaisyUI themes: 'tformance' (dark) and 'tformance-light' (light)
 *
 * IMPORTANT: Valid theme values are:
 *   - 'tformance' (dark theme)
 *   - 'tformance-light' (light theme)
 *   - 'system' (follows OS preference)
 */

// Theme name constants - must match CSS theme definitions in site-tailwind.css
const THEME_DARK = 'tformance';
const THEME_LIGHT = 'tformance-light';

function syncDarkMode() {
  let stored = localStorage.getItem('theme') || 'system';
  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

  // Migrate legacy values (in case old 'light'/'dark' values are stored)
  if (stored === 'light') {
    stored = THEME_LIGHT;
    localStorage.setItem('theme', THEME_LIGHT);
  } else if (stored === 'dark') {
    stored = THEME_DARK;
    localStorage.setItem('theme', THEME_DARK);
  }

  let themeName;
  if (stored === 'system') {
    themeName = prefersDark ? THEME_DARK : THEME_LIGHT;
  } else {
    themeName = stored;
  }

  const isDark = themeName === THEME_DARK;

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
