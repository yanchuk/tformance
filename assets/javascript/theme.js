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
