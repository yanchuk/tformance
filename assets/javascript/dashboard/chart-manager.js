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
   * @param {number} retryCount - Current retry attempt (internal use)
   * @returns {Chart|null} The Chart instance or null if not found
   */
  init(canvasId, retryCount = 0) {
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 100;

    const config = this.registry.get(canvasId);
    if (!config) {
      // Not registered - might be handled elsewhere
      return null;
    }

    const canvas = document.getElementById(canvasId);
    if (!canvas) {
      // Canvas not in DOM - retry if we haven't exceeded max retries
      if (retryCount < MAX_RETRIES) {
        setTimeout(() => this.init(canvasId, retryCount + 1), RETRY_DELAY);
      }
      return null;
    }

    // Check if already initialized (prevent double-init)
    if (canvas.dataset.chartInitialized === 'true') {
      return this.instances.get(canvasId) || null;
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
      } else if (retryCount < MAX_RETRIES) {
        // Data element not found yet, retry
        setTimeout(() => this.init(canvasId, retryCount + 1), RETRY_DELAY);
        return null;
      }
    }

    // Create the chart
    try {
      const chart = config.createFn(canvas, data);
      if (chart) {
        this.instances.set(canvasId, chart);
        // Mark canvas as initialized to prevent double-init
        canvas.dataset.chartInitialized = 'true';
        // Force resize after creation - fixes HTMX swap sizing issue
        // where canvas stays at default 300x150 dimensions.
        // Use nested RAF to ensure layout is fully complete before resize.
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            if (chart && typeof chart.resize === 'function') {
              chart.resize();
            }
          });
        });
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
      // Clear the initialized flag
      delete canvas.dataset.chartInitialized;
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
      case 'combined-trend':
        chart = this.createCombinedTrendChart(ctx, data, options);
        break;
      case 'correlation-scatter':
        chart = this.createCorrelationScatterChart(ctx, data, options);
        break;
      case 'benchmark-scatter':
        chart = this.createBenchmarkScatterChart(ctx, data, options);
        break;
      case 'industry-benchmark':
        chart = this.createIndustryBenchmarkChart(ctx, data, options);
        break;
      default:
        console.warn(`ChartManager: Unknown chart type "${chartType}"`);
        return null;
    }

    if (chart) {
      this.instances.set(canvasId, chart);
      // Mark canvas as initialized
      canvas.dataset.chartInitialized = 'true';
      // Force resize after creation - fixes HTMX swap sizing issue.
      // Use nested RAF to ensure layout is fully complete before resize.
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          const liveCanvas = chart?.canvas;
          if (
            chart &&
            typeof chart.resize === 'function' &&
            liveCanvas &&
            liveCanvas.isConnected &&
            liveCanvas.ownerDocument
          ) {
            chart.resize();
          }
        });
      });
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

  /**
   * Create a dual-axis line chart for combined trend (AI adoption + delivery metric)
   * Data format: { labels, datasets: { ai_adoption: {values, label, yAxisID}, <secondary>: {values, label, yAxisID} } }
   */
  createCombinedTrendChart(ctx, data, options = {}) {
    if (!data || !data.labels || !data.datasets) return null;

    const dsKeys = Object.keys(data.datasets);
    const colors = [
      { line: 'rgba(168, 85, 247, 1)', fill: 'rgba(168, 85, 247, 0.1)' },   // purple for AI
      { line: 'rgba(249, 115, 22, 1)', fill: 'rgba(249, 115, 22, 0.1)' },    // orange for delivery
    ];

    const datasets = dsKeys.map((key, i) => {
      const ds = data.datasets[key];
      const c = colors[i % colors.length];
      return {
        label: ds.label,
        data: ds.values,
        borderColor: c.line,
        backgroundColor: c.fill,
        borderWidth: 2,
        fill: false,
        tension: 0.3,
        pointRadius: 2,
        pointHoverRadius: 5,
        yAxisID: ds.yAxisID || (i === 0 ? 'y' : 'y1'),
      };
    });

    const secondaryDs = data.datasets[dsKeys[1]];

    return new Chart(ctx, {
      type: 'line',
      data: { labels: data.labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: { boxWidth: 12, padding: 10, font: { family: "'DM Sans', sans-serif", size: 11 } },
          },
          tooltip: { mode: 'index', intersect: false },
          datalabels: { display: false },
        },
        scales: {
          x: {
            ticks: { font: { family: "'DM Sans', sans-serif" }, maxRotation: 45, autoSkip: true, maxTicksLimit: 12 },
            grid: { display: false },
          },
          y: {
            type: 'linear',
            position: 'left',
            min: 0,
            max: 100,
            ticks: { font: { family: "'JetBrains Mono', monospace" }, callback: (v) => `${v}%` },
            title: { display: true, text: 'AI Adoption %', font: { family: "'DM Sans', sans-serif" } },
          },
          y1: {
            type: 'linear',
            position: 'right',
            beginAtZero: true,
            ticks: { font: { family: "'JetBrains Mono', monospace" } },
            title: { display: true, text: secondaryDs ? secondaryDs.label : 'Hours', font: { family: "'DM Sans', sans-serif" } },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  }

  /**
   * Create a scatter chart for correlation (AI adoption vs delivery metric)
   * Data format: { points: [{x, y, week}], r_value, classification }
   */
  createCorrelationScatterChart(ctx, data, options = {}) {
    if (!data || !data.points || data.points.length === 0) return null;

    return new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Weekly Data',
          data: data.points,
          backgroundColor: 'rgba(168, 85, 247, 0.6)',
          borderColor: 'rgba(168, 85, 247, 1)',
          borderWidth: 1,
          pointRadius: 5,
          pointHoverRadius: 7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const pt = context.raw;
                return [
                  `AI: ${pt.x?.toFixed(1)}%`,
                  `Cycle Time: ${pt.y?.toFixed(1)}h`,
                  pt.week ? `Week: ${pt.week}` : '',
                ].filter(Boolean);
              },
            },
          },
          datalabels: { display: false },
        },
        scales: {
          x: {
            title: { display: true, text: 'AI Adoption %', font: { family: "'DM Sans', sans-serif" } },
            ticks: { font: { family: "'JetBrains Mono', monospace" }, callback: (v) => `${v}%` },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
          },
          y: {
            title: { display: true, text: options.yAxisLabel || 'Cycle Time (h)', font: { family: "'DM Sans', sans-serif" } },
            ticks: { font: { family: "'JetBrains Mono', monospace" } },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
            beginAtZero: true,
          },
        },
      },
    });
  }

  /**
   * Create a scatter chart for org benchmarks (flat array of {x, y, label} points)
   * Data format: [{x, y, label, prs, industry}, ...]
   */
  createBenchmarkScatterChart(ctx, data, options = {}) {
    if (!data || !Array.isArray(data) || data.length === 0) return null;

    return new Chart(ctx, {
      type: 'scatter',
      data: {
        datasets: [{
          label: 'Organizations',
          data: data,
          backgroundColor: 'rgba(249, 115, 22, 0.6)',
          borderColor: 'rgba(249, 115, 22, 1)',
          borderWidth: 1,
          pointRadius: 6,
          pointHoverRadius: 9,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const pt = context.raw;
                return [
                  pt.label || '',
                  `AI: ${pt.x?.toFixed(1)}%`,
                  `Cycle Time: ${pt.y?.toFixed(1)}h`,
                  pt.prs ? `PRs: ${pt.prs}` : '',
                ].filter(Boolean);
              },
            },
          },
          datalabels: { display: false },
        },
        scales: {
          x: {
            title: { display: true, text: 'AI Adoption %', font: { family: "'DM Sans', sans-serif" } },
            ticks: { font: { family: "'JetBrains Mono', monospace" }, callback: (v) => `${v}%` },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
          },
          y: {
            title: { display: true, text: 'Median Cycle Time (h)', font: { family: "'DM Sans', sans-serif" } },
            ticks: { font: { family: "'JetBrains Mono', monospace" } },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
            beginAtZero: true,
          },
        },
      },
    });
  }

  /**
   * Create a grouped bar chart for industry benchmarks
   * Data format: [{industry_display, avg_ai_pct, avg_cycle_time, avg_review_time, org_count}, ...]
   */
  createIndustryBenchmarkChart(ctx, data, options = {}) {
    if (!data || !Array.isArray(data) || data.length === 0) return null;

    const labels = data.map(d => d.industry_display || d.industry);
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: 'AI Adoption %',
            data: data.map(d => d.avg_ai_pct),
            backgroundColor: 'rgba(168, 85, 247, 0.7)',
            borderColor: 'rgba(168, 85, 247, 1)',
            borderWidth: 1,
            yAxisID: 'y',
          },
          {
            label: 'Avg Cycle Time (h)',
            data: data.map(d => d.avg_cycle_time),
            backgroundColor: 'rgba(249, 115, 22, 0.7)',
            borderColor: 'rgba(249, 115, 22, 1)',
            borderWidth: 1,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: true, position: 'top', labels: { boxWidth: 12, font: { family: "'DM Sans', sans-serif", size: 11 } } },
          tooltip: {
            callbacks: {
              afterBody: (context) => {
                const idx = context[0].dataIndex;
                const d = data[idx];
                return d ? `Organizations: ${d.org_count}` : '';
              },
            },
          },
          datalabels: { display: false },
        },
        scales: {
          x: { ticks: { font: { family: "'DM Sans', sans-serif" } }, grid: { display: false } },
          y: {
            type: 'linear', position: 'left', beginAtZero: true,
            ticks: { font: { family: "'JetBrains Mono', monospace" }, callback: (v) => `${v}%` },
            title: { display: true, text: 'AI Adoption %', font: { family: "'DM Sans', sans-serif" } },
          },
          y1: {
            type: 'linear', position: 'right', beginAtZero: true,
            ticks: { font: { family: "'JetBrains Mono', monospace" } },
            title: { display: true, text: 'Cycle Time (h)', font: { family: "'DM Sans', sans-serif" } },
            grid: { drawOnChartArea: false },
          },
        },
      },
    });
  }

  /**
   * Normalize datasets to percentages (each time point sums to 100%)
   * @param {Array} datasets - Array of {label, data, color, ...}
   * @param {number} labelCount - Number of labels/time points
   * @returns {Array} Normalized datasets with percentage values
   */
  normalizeToPercentages(datasets, labelCount) {
    // Calculate totals for each time point
    const totals = Array(labelCount).fill(0);
    datasets.forEach(ds => {
      if (ds.data) {
        ds.data.forEach((v, i) => {
          totals[i] += (v || 0);
        });
      }
    });

    // Convert each dataset to percentages
    return datasets.map(ds => ({
      ...ds,
      data: ds.data ? ds.data.map((v, i) => {
        const total = totals[i];
        return total > 0 ? ((v || 0) / total) * 100 : 0;
      }) : [],
    }));
  }

  /**
   * Create a 100% stacked area chart (for composition trends)
   * Shows how percentages of each category change over time
   * @param {CanvasRenderingContext2D} ctx - Canvas context
   * @param {Object} chartData - { labels, datasets: [{label, data, color}] }
   * @param {Object} options - Additional options
   * @returns {Chart} Chart.js instance
   */
  createStackedAreaChart(ctx, chartData, options = {}) {
    if (!chartData || !chartData.labels || !chartData.datasets) {
      console.warn('createStackedAreaChart: Invalid chart data');
      return null;
    }

    // Filter out datasets with no data
    const validDatasets = chartData.datasets.filter(ds =>
      ds.data && Array.isArray(ds.data) && ds.data.some(v => v !== null && v !== undefined)
    );

    if (validDatasets.length === 0) {
      console.warn('createStackedAreaChart: No valid datasets');
      return null;
    }

    // Normalize to percentages
    const normalizedDatasets = this.normalizeToPercentages(validDatasets, chartData.labels.length);

    // Build Chart.js datasets with stacked area configuration
    const datasets = normalizedDatasets.map((ds, index) => ({
      label: ds.label,
      data: ds.data,
      backgroundColor: ds.color + '99', // 60% opacity
      borderColor: ds.color,
      borderWidth: 1,
      fill: index === 0 ? 'origin' : '-1', // Stack on previous
      tension: 0.3, // Smooth curves
      pointRadius: 0, // No points for cleaner look
      pointHoverRadius: 4,
    }));

    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: chartData.labels,
        datasets: datasets,
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
          mode: 'index',
          intersect: false,
        },
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
            callbacks: {
              label: (context) => {
                const value = context.raw;
                return `${context.dataset.label}: ${value.toFixed(1)}%`;
              },
              footer: (tooltipItems) => {
                // Show total percentage (should always be ~100%)
                const total = tooltipItems.reduce((sum, item) => sum + item.raw, 0);
                return `Total: ${total.toFixed(1)}%`;
              },
            },
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
              maxTicksLimit: 12,
            },
            grid: {
              display: false,
            },
          },
          y: {
            stacked: true,
            min: 0,
            max: 100,
            ticks: {
              font: { family: "'JetBrains Mono', monospace" },
              callback: (value) => `${value}%`,
            },
            title: {
              display: true,
              text: options.yAxisLabel || 'Share %',
              font: { family: "'DM Sans', sans-serif" },
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
