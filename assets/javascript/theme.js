/**
 * Theme management for dark/light toggle
 * Works with DaisyUI themes defined in site-tailwind.css
 *
 * Valid theme values:
 *   - 'tformance' (Easy Eyes dark theme - default)
 *   - 'tformance-light' (light theme)
 *   - 'system' (follows OS preference, uses dark/light)
 */

// Theme name constants - must match CSS theme definitions in site-tailwind.css
const THEME_DARK = 'tformance';
const THEME_LIGHT = 'tformance-light';

// Track if this is the initial page load (don't track on load, only on user action)
let _themeInitialized = false;

function syncDarkMode() {
  const previousTheme = localStorage.getItem('theme') || 'system';
  let stored = previousTheme;
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

  // Track theme switch (only after initial load and if theme actually changed)
  const newTheme = localStorage.getItem('theme') || 'system';
  if (_themeInitialized && previousTheme !== newTheme) {
    // Use global analytics if available
    if (window.TformanceAnalytics && window.TformanceAnalytics.trackThemeSwitch) {
      window.TformanceAnalytics.trackThemeSwitch(newTheme, previousTheme);
    }
  }
  _themeInitialized = true;
}

// Apply on page load
syncDarkMode();

// Listen for system preference changes
window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  if (localStorage.getItem('theme') === 'system') syncDarkMode();
});

// Export globally for Alpine.js onclick handlers
window.syncDarkMode = syncDarkMode;
