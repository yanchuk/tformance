'use strict';

/**
 * Tformance Sparkline Charts Module
 *
 * Provides minimal inline charts for key metric cards showing
 * 12-week trend data without axes or legends.
 */

import Chart from 'chart.js/auto';
import { TformanceChartTheme } from './chart-theme.js';

/**
 * Get color based on trend direction
 * @param {string} trend - 'up', 'down', or 'flat'
 * @param {string} metric - Metric name to determine if lower is better
 * @returns {string} Hex color code
 */
function getTrendColor(trend, metric) {
  // For cycle_time and review_time, lower is better (so up = bad, down = good)
  const lowerIsBetter = metric === 'cycle_time' || metric === 'review_time';

  if (trend === 'flat') {
    return TformanceChartTheme.colors.muted;
  }

  if (lowerIsBetter) {
    // Lower is better: down = green, up = red
    return trend === 'down' ? TformanceChartTheme.colors.success : TformanceChartTheme.colors.error;
  } else {
    // Higher is better: up = green, down = red
    return trend === 'up' ? TformanceChartTheme.colors.success : TformanceChartTheme.colors.error;
  }
}

/**
 * Create a sparkline chart
 * @param {HTMLCanvasElement} canvas - Canvas element to render chart
 * @param {Array<number>} values - Array of data values
 * @param {Object} options - Chart options
 * @param {string} options.trend - Trend direction ('up', 'down', 'flat')
 * @param {string} options.metric - Metric name for color logic
 * @returns {Chart} Chart.js instance
 */
export function createSparkline(canvas, values, options = {}) {
  const trend = options.trend || 'flat';
  const metric = options.metric || '';
  const color = getTrendColor(trend, metric);

  // Generate labels (just indices, not displayed)
  const labels = values.map((_, i) => i.toString());

  const chartConfig = {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          data: values,
          borderColor: color,
          backgroundColor: `${color}1a`, // 10% opacity fill
          fill: true,
          tension: 0.4,
          borderWidth: 1.5,
          pointRadius: 0,
          pointHoverRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        tooltip: {
          enabled: false,
        },
      },
      scales: {
        x: {
          display: false,
        },
        y: {
          display: false,
          // Add small padding so line doesn't touch edges
          grace: '10%',
        },
      },
      elements: {
        line: {
          capBezierPoints: true,
        },
      },
      animation: {
        duration: 300,
      },
    },
  };

  return new Chart(canvas, chartConfig);
}

/**
 * Initialize all sparkline charts on the page
 * Finds elements with data-sparkline attribute and initializes them
 */
export function initSparklines() {
  const sparklines = document.querySelectorAll('[data-sparkline]');

  sparklines.forEach((canvas) => {
    // Skip if already initialized
    if (Chart.getChart(canvas)) {
      return;
    }

    const valuesAttr = canvas.getAttribute('data-sparkline-values');
    const trend = canvas.getAttribute('data-sparkline-trend') || 'flat';
    const metric = canvas.getAttribute('data-sparkline-metric') || '';

    if (valuesAttr) {
      try {
        const values = JSON.parse(valuesAttr);
        if (Array.isArray(values) && values.length > 0) {
          createSparkline(canvas, values, { trend, metric });
        }
      } catch (e) {
        console.error('Failed to initialize sparkline:', e);
      }
    }
  });
}

/**
 * Destroy and reinitialize sparklines (useful after HTMX swap)
 */
export function reinitSparklines() {
  const sparklines = document.querySelectorAll('[data-sparkline]');

  sparklines.forEach((canvas) => {
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
      existingChart.destroy();
    }
  });

  initSparklines();
}

// Auto-initialize on DOMContentLoaded
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', initSparklines);

  // Re-initialize after HTMX content swap
  document.addEventListener('htmx:afterSwap', (event) => {
    // Only reinit if the swapped content might contain sparklines
    if (event.detail.target.querySelector('[data-sparkline]')) {
      reinitSparklines();
    } else {
      // Try to init any new sparklines
      initSparklines();
    }
  });
}

// Export for global access
window.createSparkline = createSparkline;
window.initSparklines = initSparklines;
window.reinitSparklines = reinitSparklines;
