'use strict';

/**
 * Tformance Trend Charts Module
 *
 * Provides wide trend charts with zoom/pan capabilities for long-horizon
 * trend visualization and YoY comparison.
 */

import Chart from 'chart.js/auto';
import zoomPlugin from 'chartjs-plugin-zoom';
import { TformanceChartTheme, getChartDefaults, chartColorPalette } from './chart-theme.js';

// Register zoom plugin
Chart.register(zoomPlugin);

/**
 * Metric display configuration
 */
const METRIC_CONFIG = {
  cycle_time: {
    label: 'Cycle Time',
    unit: 'hours',
    color: TformanceChartTheme.colors.primary,
    format: (v) => `${v.toFixed(1)}h`,
  },
  review_time: {
    label: 'Review Time',
    unit: 'hours',
    color: TformanceChartTheme.colors.success,
    format: (v) => `${v.toFixed(1)}h`,
  },
  pr_count: {
    label: 'PRs Merged',
    unit: 'count',
    color: TformanceChartTheme.colors.secondary,
    format: (v) => Math.round(v).toString(),
  },
  ai_adoption: {
    label: 'AI Adoption',
    unit: '%',
    color: TformanceChartTheme.colors.ai,
    format: (v) => `${v.toFixed(1)}%`,
  },
};

/**
 * Create a wide trend chart with zoom capabilities
 * @param {HTMLCanvasElement} canvas - Canvas element to render chart
 * @param {Array} data - Array of {month/week, value} objects
 * @param {Object} options - Chart options
 * @returns {Chart} Chart.js instance
 */
export function createWideTrendChart(canvas, data, options = {}) {
  const metric = options.metric || 'cycle_time';
  const config = METRIC_CONFIG[metric] || METRIC_CONFIG.cycle_time;
  const comparisonData = options.comparisonData;

  // Prepare labels and values
  const labels = data.map((d) => d.month || d.week || d.label);
  const values = data.map((d) => d.value);

  // Build datasets
  const datasets = [
    {
      label: config.label,
      data: values,
      borderColor: config.color,
      backgroundColor: `${config.color}1a`, // 10% opacity
      fill: true,
      tension: 0.3,
      pointRadius: 4,
      pointHoverRadius: 6,
      pointBackgroundColor: config.color,
      pointBorderWidth: 2,
    },
  ];

  // Add comparison dataset if provided
  if (comparisonData && Array.isArray(comparisonData)) {
    const compValues = comparisonData.map((d) => d.value);
    datasets.push({
      label: `${config.label} (Last Year)`,
      data: compValues,
      borderColor: `${TformanceChartTheme.colors.muted}b3`, // 70% opacity
      backgroundColor: `${TformanceChartTheme.colors.muted}1a`,
      fill: true,
      tension: 0.3,
      borderDash: [5, 5],
      pointRadius: 3,
      pointHoverRadius: 5,
    });
  }

  // Get base chart defaults
  const defaults = getChartDefaults();

  // Chart configuration
  const chartConfig = {
    type: 'line',
    data: { labels, datasets },
    options: {
      ...defaults,
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      scales: {
        ...defaults.scales,
        y: {
          ...defaults.scales.y,
          beginAtZero: true,
          title: {
            display: true,
            text: `${config.label} (${config.unit})`,
            ...defaults.scales.y.title,
          },
          ticks: {
            ...defaults.scales.y.ticks,
            callback: (value) => config.format(value),
          },
        },
        x: {
          ...defaults.scales.x,
          ticks: {
            ...defaults.scales.x.ticks,
            maxRotation: 45,
            autoSkip: true,
            maxTicksLimit: 12,
          },
        },
      },
      plugins: {
        ...defaults.plugins,
        legend: {
          display: datasets.length > 1,
          ...defaults.plugins.legend,
        },
        datalabels: {
          display: false, // Disable data labels for line charts (too cluttered)
        },
        tooltip: {
          ...defaults.plugins.tooltip,
          callbacks: {
            label: (context) => {
              const value = context.raw;
              return `${context.dataset.label}: ${config.format(value)}`;
            },
          },
        },
        zoom: {
          pan: {
            enabled: true,
            mode: 'x',
            modifierKey: null, // No modifier needed
          },
          zoom: {
            wheel: {
              enabled: true,
            },
            pinch: {
              enabled: true,
            },
            mode: 'x',
            onZoomComplete: ({ chart }) => {
              // Update reset button visibility
              const resetBtn = document.querySelector('[data-chart-reset]');
              if (resetBtn) {
                resetBtn.style.display = 'block';
              }
            },
          },
        },
      },
    },
  };

  return new Chart(canvas, chartConfig);
}

/**
 * Reset zoom on a chart
 * @param {Chart} chart - Chart.js instance
 */
export function resetChartZoom(chart) {
  if (chart && typeof chart.resetZoom === 'function') {
    chart.resetZoom();
  }
}

/**
 * Initialize trend charts on page load
 * Automatically finds and initializes charts with data-trend-chart attribute
 */
export function initTrendCharts() {
  const charts = document.querySelectorAll('[data-trend-chart]');

  charts.forEach((canvas) => {
    const dataAttr = canvas.getAttribute('data-chart-data');
    const metric = canvas.getAttribute('data-metric');
    const comparisonAttr = canvas.getAttribute('data-comparison');

    if (dataAttr) {
      try {
        const data = JSON.parse(dataAttr);
        const comparisonData = comparisonAttr ? JSON.parse(comparisonAttr) : null;

        createWideTrendChart(canvas, data, { metric, comparisonData });
      } catch (e) {
        console.error('Failed to initialize trend chart:', e);
      }
    }
  });
}

// Auto-initialize on DOMContentLoaded
if (typeof document !== 'undefined') {
  document.addEventListener('DOMContentLoaded', initTrendCharts);

  // Re-initialize after HTMX content swap
  document.addEventListener('htmx:afterSwap', initTrendCharts);
}

/**
 * Format a metric value based on its unit
 * @param {number} value - The numeric value
 * @param {string} unit - Unit type: 'hours', '%', 'count', or undefined
 * @returns {string} Formatted value with unit suffix
 */
export function formatMetricValue(value, unit) {
  if (value === null || value === undefined) return '--';
  if (unit === 'hours') return `${value.toFixed(1)}h`;
  if (unit === '%') return `${value.toFixed(1)}%`;
  if (unit === 'count') return Math.round(value).toLocaleString();
  return typeof value === 'number' ? value.toFixed(1) : String(value);
}

/**
 * Create a multi-metric comparison chart with dual Y-axes
 * @param {HTMLCanvasElement} canvas - Canvas element to render chart
 * @param {Object} chartData - Chart data with labels, datasets, and hasY2Axis
 * @returns {Chart} Chart.js instance
 */
export function createMultiMetricChart(canvas, chartData) {
  // Defensive checks
  if (!chartData) {
    console.warn('createMultiMetricChart: No chartData provided');
    return null;
  }

  const { labels, datasets, hasY2Axis } = chartData;

  if (!labels || !Array.isArray(labels) || labels.length === 0) {
    console.warn('createMultiMetricChart: No labels provided');
    return null;
  }

  if (!datasets || !Array.isArray(datasets) || datasets.length === 0) {
    console.warn('createMultiMetricChart: No datasets provided');
    return null;
  }

  // Filter out datasets with no data
  const validDatasets = datasets.filter(ds => {
    if (!ds.data || !Array.isArray(ds.data)) {
      console.warn(`createMultiMetricChart: Dataset "${ds.label}" has no data array`);
      return false;
    }
    // Check if has at least some non-null values
    const hasValues = ds.data.some(v => v !== null && v !== undefined);
    if (!hasValues) {
      console.warn(`createMultiMetricChart: Dataset "${ds.label}" has all null values`);
      return false;
    }
    return true;
  });

  if (validDatasets.length === 0) {
    console.warn('createMultiMetricChart: No valid datasets after filtering');
    return null;
  }

  // Build Chart.js datasets from our format (use validDatasets)
  const chartDatasets = validDatasets.map((ds) => ({
    label: ds.label,
    data: ds.data,
    borderColor: ds.color,
    backgroundColor: `${ds.color}1a`, // 10% opacity
    fill: false, // No fill for multi-line clarity
    tension: 0.3,
    pointRadius: 4,
    pointHoverRadius: 6,
    pointBackgroundColor: ds.color,
    pointBorderWidth: 2,
    yAxisID: ds.yAxisID || 'y',
    // Store unit for tooltip access
    unit: ds.unit,
  }));

  // Get base chart defaults
  const defaults = getChartDefaults();

  // Recalculate hasY2Axis based on validDatasets (some might have been filtered)
  const needsY2Axis = hasY2Axis && validDatasets.some(ds => ds.yAxisID === 'y2');

  // Build scales configuration
  const scales = {
    ...defaults.scales,
    x: {
      ...defaults.scales.x,
      ticks: {
        ...defaults.scales.x.ticks,
        maxRotation: 45,
        autoSkip: true,
        maxTicksLimit: 12,
      },
    },
    y: {
      ...defaults.scales.y,
      type: 'linear',
      display: true,
      position: 'left',
      beginAtZero: true,
      title: {
        display: true,
        text: 'Hours',
        ...defaults.scales.y.title,
      },
      ticks: {
        ...defaults.scales.y.ticks,
        callback: (value) => formatMetricValue(value, 'hours'),
      },
    },
  };

  // Add secondary Y axis if needed
  if (needsY2Axis) {
    scales.y2 = {
      ...defaults.scales.y,
      type: 'linear',
      display: true,
      position: 'right',
      beginAtZero: true,
      grid: {
        drawOnChartArea: false, // Only show grid for primary axis
      },
      title: {
        display: true,
        text: 'Count / %',
        ...defaults.scales.y.title,
      },
    };
  }

  // Chart configuration
  const chartConfig = {
    type: 'line',
    data: { labels, datasets: chartDatasets },
    options: {
      ...defaults,
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: 'index',
        intersect: false,
      },
      scales,
      plugins: {
        ...defaults.plugins,
        legend: {
          display: true,
          position: 'top',
          ...defaults.plugins.legend,
        },
        datalabels: {
          display: false,
        },
        tooltip: {
          ...defaults.plugins.tooltip,
          callbacks: {
            label: (context) => {
              // Use the unit stored on the Chart.js dataset (not the original data)
              const unit = context.dataset.unit;
              const value = context.raw;
              const formatted = formatMetricValue(value, unit);
              return `${context.dataset.label}: ${formatted}`;
            },
          },
        },
        // Zoom disabled for comparison chart per user request
        zoom: {
          pan: {
            enabled: false,
          },
          zoom: {
            wheel: {
              enabled: false,
            },
            pinch: {
              enabled: false,
            },
          },
        },
      },
    },
  };

  return new Chart(canvas, chartConfig);
}

// Export for global access
window.createWideTrendChart = createWideTrendChart;
window.createMultiMetricChart = createMultiMetricChart;
window.resetChartZoom = resetChartZoom;
window.formatMetricValue = formatMetricValue;
