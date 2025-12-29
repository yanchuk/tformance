/**
 * ChartManager - Centralized Chart Initialization Registry
 *
 * Provides a single source of truth for chart initialization, preventing
 * duplicate Chart.js instances and ensuring proper cleanup during HTMX swaps.
 *
 * Usage:
 *   // Register a chart factory
 *   chartManager.register('trend-chart', (canvas, data) => {
 *     return new Chart(canvas, { ... });
 *   });
 *
 *   // Initialize a specific chart
 *   chartManager.init('trend-chart');
 *
 *   // Initialize all registered charts (call in htmx:afterSwap)
 *   chartManager.initAll();
 */
import Chart from 'chart.js/auto';

class ChartManager {
  constructor() {
    // Registry of chart factories: canvasId -> { createFn, dataId, options }
    this.registry = new Map();
    // Active chart instances: canvasId -> Chart instance
    this.instances = new Map();
  }

  /**
   * Register a chart factory function
   * @param {string} canvasId - The ID of the canvas element
   * @param {Function} createFn - Factory function (canvas, data) => Chart
   * @param {Object} options - Optional configuration
   * @param {string} options.dataId - ID of JSON script element with chart data
   */
  register(canvasId, createFn, options = {}) {
    if (typeof createFn !== 'function') {
      console.error(`ChartManager: createFn for "${canvasId}" must be a function`);
      return;
    }
    this.registry.set(canvasId, { createFn, ...options });
  }

  /**
   * Unregister a chart
   * @param {string} canvasId - The ID of the canvas element
   */
  unregister(canvasId) {
    this.destroy(canvasId);
    this.registry.delete(canvasId);
  }

  /**
   * Initialize a single chart by canvas ID
   * @param {string} canvasId - The ID of the canvas element
   * @returns {Chart|null} The Chart instance or null if not found
   */
  init(canvasId) {
    const config = this.registry.get(canvasId);
    if (!config) {
      // Not registered - might be handled elsewhere
      return null;
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      // Canvas not in DOM - normal during HTMX partial loads
      return null;
    }

    // Destroy existing instance first
    this.destroy(canvasId);

    // Get data if dataId is specified
    let data = null;
    if (config.dataId) {
      const dataEl = document.getElementById(config.dataId);
      if (dataEl) {
        try {
          data = JSON.parse(dataEl.textContent);
        } catch (e) {
          console.error(`ChartManager: Failed to parse data for "${canvasId}":`, e);
          return null;
        }
      }
    }

    // Create the chart
    try {
      const chart = config.createFn(canvas, data);
      if (chart) {
        this.instances.set(canvasId, chart);
      }
      return chart;
    } catch (e) {
      console.error(`ChartManager: Failed to create chart "${canvasId}":`, e);
      return null;
    }
  }

  /**
   * Destroy a chart instance
   * @param {string} canvasId - The ID of the canvas element
   */
  destroy(canvasId) {
    // Check for existing Chart.js instance on canvas
    const canvas = document.getElementById(canvasId);
    if (canvas) {
      const existingChart = Chart.getChart(canvas);
      if (existingChart) {
        existingChart.destroy();
      }
    }

    // Remove from our instances map
    const instance = this.instances.get(canvasId);
    if (instance) {
      // Double-check it's destroyed
      if (instance.canvas) {
        instance.destroy();
      }
      this.instances.delete(canvasId);
    }
  }

  /**
   * Initialize all registered charts that have canvases in the DOM
   * Call this in htmx:afterSwap handler
   */
  initAll() {
    for (const canvasId of this.registry.keys()) {
      this.init(canvasId);
    }
  }

  /**
   * Destroy all chart instances
   */
  destroyAll() {
    for (const canvasId of this.instances.keys()) {
      this.destroy(canvasId);
    }
  }

  /**
   * Check if a chart is registered
   * @param {string} canvasId - The ID of the canvas element
   * @returns {boolean}
   */
  isRegistered(canvasId) {
    return this.registry.has(canvasId);
  }

  /**
   * Get a chart instance
   * @param {string} canvasId - The ID of the canvas element
   * @returns {Chart|null}
   */
  getInstance(canvasId) {
    return this.instances.get(canvasId) || null;
  }

  /**
   * Auto-detect charts via data attributes and initialize them
   * Looks for canvases with data-chart-type attribute
   */
  initFromDataAttributes() {
    const chartCanvases = document.querySelectorAll('canvas[data-chart-type]');
    for (const canvas of chartCanvases) {
      const canvasId = canvas.id;
      if (!canvasId) continue;

      // Skip if already registered with a factory
      if (this.registry.has(canvasId)) {
        this.init(canvasId);
        continue;
      }

      // Get configuration from data attributes
      const chartType = canvas.dataset.chartType;
      const dataId = canvas.dataset.chartDataId;
      let options = {};

      if (canvas.dataset.chartOptions) {
        try {
          options = JSON.parse(canvas.dataset.chartOptions);
        } catch (e) {
          console.warn(`ChartManager: Invalid chartOptions JSON for "${canvasId}"`);
        }
      }

      // Create chart based on type
      this.initByType(canvasId, chartType, dataId, options);
    }
  }

  /**
   * Initialize a chart by type name
   * @param {string} canvasId - Canvas element ID
   * @param {string} chartType - Type identifier (e.g., 'bar', 'line', 'weekly-bar')
   * @param {string} dataId - ID of data script element
   * @param {Object} options - Additional chart options
   */
  initByType(canvasId, chartType, dataId, options = {}) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    const dataEl = dataId ? document.getElementById(dataId) : null;
    let data = null;

    if (dataEl) {
      try {
        data = JSON.parse(dataEl.textContent);
      } catch (e) {
        console.error(`ChartManager: Failed to parse data for "${canvasId}"`);
        return null;
      }
    }

    if (!data) return null;

    // Destroy existing
    this.destroy(canvasId);

    // Create based on type
    let chart = null;
    const ctx = canvas.getContext('2d');

    switch (chartType) {
      case 'stacked-bar':
        chart = this.createStackedBarChart(ctx, data, options);
        break;
      case 'weekly-bar':
        chart = this.createWeeklyBarChart(ctx, data, options);
        break;
      default:
        console.warn(`ChartManager: Unknown chart type "${chartType}"`);
        return null;
    }

    if (chart) {
      this.instances.set(canvasId, chart);
    }
    return chart;
  }

  /**
   * Create a stacked bar chart (for PR type, tech breakdown)
   */
  createStackedBarChart(ctx, chartData, options = {}) {
    if (!chartData || !chartData.labels) return null;

    const datasets = chartData.datasets.map(ds => ({
      label: ds.label,
      data: ds.data,
      backgroundColor: ds.color,
      borderColor: ds.color,
      borderWidth: 1,
      borderRadius: 2,
    }));

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: chartData.labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: {
              boxWidth: 12,
              padding: 10,
              font: { family: "'DM Sans', sans-serif", size: 11 },
            },
          },
          tooltip: {
            mode: 'index',
            intersect: false,
          },
          datalabels: {
            display: false,
          },
        },
        scales: {
          x: {
            stacked: true,
            ticks: {
              font: { family: "'DM Sans', sans-serif" },
              maxRotation: 45,
              autoSkip: true,
            },
            grid: {
              display: false,
            },
          },
          y: {
            stacked: true,
            beginAtZero: true,
            ticks: {
              font: { family: "'JetBrains Mono', monospace" },
              precision: 0,
            },
            title: {
              display: true,
              text: options.yAxisLabel || 'Count',
              font: { family: "'DM Sans', sans-serif" },
            },
          },
        },
      },
    });
  }

  /**
   * Create a weekly bar chart (for AI adoption, cycle time, etc.)
   */
  createWeeklyBarChart(ctx, data, options = {}) {
    if (!data || data.length === 0) return null;

    // Theme-aware colors
    const isAI = options.ai === true;
    const primaryColor = isAI ? 'rgba(168, 85, 247, 0.8)' : 'rgba(249, 115, 22, 0.8)';
    const borderColor = isAI ? 'rgba(168, 85, 247, 1)' : 'rgba(249, 115, 22, 1)';

    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.map(d => d.week || d.label),
        datasets: [{
          label: options.label || 'Value',
          data: data.map(d => d.value),
          backgroundColor: primaryColor,
          borderColor: borderColor,
          borderWidth: 1,
          borderRadius: 4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              label: (context) => {
                const value = context.parsed.y;
                if (options.format === 'percent') {
                  return `${value.toFixed(1)}%`;
                }
                if (options.format === 'hours') {
                  return `${value.toFixed(1)} hours`;
                }
                return value.toString();
              }
            }
          },
          datalabels: {
            display: false,
          },
        },
        scales: {
          x: {
            ticks: {
              font: { family: "'DM Sans', sans-serif" },
              maxRotation: 45,
              autoSkip: true,
            },
            grid: {
              display: false,
            },
          },
          y: {
            beginAtZero: true,
            ticks: {
              font: { family: "'JetBrains Mono', monospace" },
            },
          },
        },
      },
    });
  }
}

// Export singleton instance
export const chartManager = new ChartManager();

// Also export class for testing
export { ChartManager };
