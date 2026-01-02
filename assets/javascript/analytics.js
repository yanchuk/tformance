/**
 * PostHog Analytics Module
 *
 * Centralized frontend tracking for user interactions.
 * PostHog SDK is loaded via CDN in posthog_init.html and available as window.posthog.
 */

/**
 * Safe wrapper for PostHog capture that handles cases where PostHog isn't loaded
 * @param {string} event - Event name
 * @param {Object} properties - Event properties
 */
export function trackEvent(event, properties = {}) {
  if (typeof window.posthog !== 'undefined' && window.posthog.capture) {
    window.posthog.capture(event, properties);
  }
}

/**
 * Track chart interaction events
 * @param {string} chartType - Type of chart (e.g., 'ai-adoption', 'cycle-time')
 * @param {string} action - Interaction type (e.g., 'click', 'hover', 'zoom')
 * @param {Object} dataPoint - Data point information (optional)
 */
export function trackChartInteraction(chartType, action, dataPoint = null) {
  const properties = {
    chart_type: chartType,
    action: action,
  };

  if (dataPoint) {
    properties.data_label = dataPoint.label || null;
    properties.data_value = dataPoint.value || null;
  }

  trackEvent('chart_interaction', properties);
}

/**
 * Track navigation events
 * @param {string} fromPage - Source page/section
 * @param {string} toPage - Destination page/section
 */
export function trackNavigation(fromPage, toPage) {
  trackEvent('navigation', {
    from_page: fromPage,
    to_page: toPage,
  });
}

/**
 * Track theme switching
 * @param {string} newTheme - New theme value ('tformance', 'tformance-light', 'system')
 * @param {string} previousTheme - Previous theme value
 */
export function trackThemeSwitch(newTheme, previousTheme) {
  trackEvent('theme_switched', {
    new_theme: newTheme,
    previous_theme: previousTheme,
  });
}

/**
 * Initialize sidebar navigation tracking
 * Attaches click handlers to sidebar links
 */
export function initNavigationTracking() {
  // Track sidebar navigation clicks
  const sidebar = document.querySelector('[data-sidebar]') || document.querySelector('.sidebar');
  if (!sidebar) return;

  sidebar.addEventListener('click', (event) => {
    const link = event.target.closest('a');
    if (!link) return;

    const currentPath = window.location.pathname;
    const targetPath = link.getAttribute('href');

    if (targetPath && targetPath !== currentPath && !targetPath.startsWith('#')) {
      trackNavigation(currentPath, targetPath);
    }
  });
}

/**
 * Initialize theme tracking by wrapping the theme toggle
 * Call this after theme.js has loaded
 */
export function initThemeTracking() {
  // Store original syncDarkMode
  const originalSyncDarkMode = window.syncDarkMode;

  if (typeof originalSyncDarkMode === 'function') {
    // Wrap syncDarkMode to track theme changes
    window.syncDarkMode = function() {
      const previousTheme = localStorage.getItem('theme') || 'system';

      // Call original function
      originalSyncDarkMode();

      // Get new theme after sync
      const newTheme = localStorage.getItem('theme') || 'system';

      // Only track if there was an actual change (not just page load)
      if (window._themeInitialized && previousTheme !== newTheme) {
        trackThemeSwitch(newTheme, previousTheme);
      }
      window._themeInitialized = true;
    };
  }
}

/**
 * Add chart interaction tracking to Chart.js instances
 * @param {Chart} chart - Chart.js instance
 * @param {string} chartId - Unique identifier for the chart
 */
export function addChartTracking(chart, chartId) {
  if (!chart || !chart.canvas) return;

  const canvas = chart.canvas;

  // Track clicks on chart elements
  canvas.addEventListener('click', (event) => {
    const elements = chart.getElementsAtEventForMode(event, 'nearest', { intersect: true }, false);

    if (elements.length > 0) {
      const element = elements[0];
      const datasetIndex = element.datasetIndex;
      const index = element.index;

      const label = chart.data.labels ? chart.data.labels[index] : null;
      const value = chart.data.datasets[datasetIndex]?.data[index];

      trackChartInteraction(chartId, 'click', { label, value });
    }
  });
}

/**
 * Initialize all analytics tracking
 * Call this on page load and after HTMX swaps
 */
export function initAnalytics() {
  initNavigationTracking();
  initThemeTracking();
}

// Expose globally for use in templates
window.TformanceAnalytics = {
  trackEvent,
  trackChartInteraction,
  trackNavigation,
  trackThemeSwitch,
  addChartTracking,
  initAnalytics,
};

// Auto-initialize on DOM ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initAnalytics);
} else {
  initAnalytics();
}

// Re-initialize after HTMX content swaps
document.addEventListener('htmx:afterSwap', () => {
  initNavigationTracking();
});
