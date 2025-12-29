import * as JsCookie from "js-cookie";
import Chart from 'chart.js/auto';
import { DashboardCharts as AppDashboardCharts } from './dashboard/dashboard-charts';
import { createWideTrendChart, resetChartZoom, initTrendCharts } from './dashboard/trend-charts';
import { createSparkline, initSparklines, reinitSparklines } from './dashboard/sparkline';
import { chartManager } from './dashboard/chart-manager';

export { AppDashboardCharts as DashboardCharts };
export { createWideTrendChart, resetChartZoom, initTrendCharts };
export { createSparkline, initSparklines, reinitSparklines };
export { chartManager };
export const Cookies = JsCookie.default;

// Ensure SiteJS global exists
if (typeof window.SiteJS === 'undefined') {
  window.SiteJS = {};
}

// Expose Chart.js globally for inline scripts in HTMX partials
window.Chart = Chart;

// Assign this entry's exports to SiteJS.app
window.SiteJS.app = {
  DashboardCharts: AppDashboardCharts,
  TrendCharts: { createWideTrendChart, resetChartZoom, initTrendCharts },
  Sparklines: { createSparkline, initSparklines, reinitSparklines },
  chartManager: chartManager,
  Cookies: JsCookie.default,
};

// Expose chartManager globally
window.chartManager = chartManager;

/**
 * Register all charts with ChartManager
 * Charts are registered once at module load, then initialized on demand
 */
function registerCharts() {
  // AI Adoption Chart - weekly bar chart
  chartManager.register('ai-adoption-chart', (canvas, data) => {
    if (!data || data.length === 0) return null;
    const ctx = canvas.getContext('2d');
    return AppDashboardCharts.weeklyBarChart(ctx, data, "AI Adoption %");
  }, { dataId: 'ai-adoption-data' });

  // Cycle Time Chart - weekly bar chart
  chartManager.register('cycle-time-chart', (canvas, data) => {
    if (!data || data.length === 0) return null;
    const ctx = canvas.getContext('2d');
    return AppDashboardCharts.weeklyBarChart(ctx, data, "Avg Cycle Time (hours)");
  }, { dataId: 'cycle-time-data' });

  // Review Time Chart - weekly bar chart
  chartManager.register('review-time-chart', (canvas, data) => {
    if (!data || data.length === 0) return null;
    const ctx = canvas.getContext('2d');
    return AppDashboardCharts.weeklyBarChart(ctx, data, "Avg Review Time (hours)");
  }, { dataId: 'review-time-data' });

  // Copilot Trend Chart - weekly bar chart with AI purple color
  chartManager.register('copilot-trend-chart', (canvas, data) => {
    if (!data || data.length === 0) return null;
    const ctx = canvas.getContext('2d');
    return AppDashboardCharts.weeklyBarChart(ctx, data, "Copilot Acceptance Rate (%)", { ai: true });
  }, { dataId: 'copilot-trend-data' });

  // PR Type Chart - stacked bar chart
  chartManager.register('pr-type-chart', (canvas, data) => {
    if (!data || !data.labels) return null;
    return chartManager.createStackedBarChart(canvas.getContext('2d'), data, { yAxisLabel: 'PR Count' });
  }, { dataId: 'pr-type-chart-data' });

  // Tech Chart - stacked bar chart
  chartManager.register('tech-chart', (canvas, data) => {
    if (!data || !data.labels) return null;
    return chartManager.createStackedBarChart(canvas.getContext('2d'), data, { yAxisLabel: 'PR Count' });
  }, { dataId: 'tech-chart-data' });

  // Wide Trend Chart - complex chart with multiple modes
  chartManager.register('trend-chart', (canvas) => {
    // This chart has complex initialization logic
    return initWideTrendChartInternal(canvas);
  });
}

/**
 * Internal wide trend chart initialization
 * Handles both single metric and multi-metric comparison modes
 */
function initWideTrendChartInternal(canvas) {
  if (!canvas) return null;

  const chartDataEl = document.getElementById('trend-chart-data');
  const comparisonDataEl = document.getElementById('trend-comparison-data');
  if (!chartDataEl) return null;

  // Check if chart creation functions are available
  if (!window.createWideTrendChart || !window.createMultiMetricChart) {
    // Retry after a short delay if modules not yet loaded
    setTimeout(() => chartManager.init('trend-chart'), 100);
    return null;
  }

  try {
    const chartData = JSON.parse(chartDataEl.textContent);
    const comparisonData = comparisonDataEl ? JSON.parse(comparisonDataEl.textContent) : null;
    const isMultiMetric = canvas.getAttribute('data-multi-metric') === 'true';

    let chart;
    if (isMultiMetric) {
      // Multi-metric comparison mode
      chart = window.createMultiMetricChart(canvas, chartData);
    } else {
      // Single metric mode
      const metric = canvas.getAttribute('data-metric');
      // Convert old format to new if needed
      const data = chartData.datasets ? chartData.datasets[0]?.data?.map((value, i) => ({
        month: chartData.labels[i],
        value: value
      })) : chartData;

      chart = window.createWideTrendChart(canvas, data, {
        metric: metric,
        comparisonData: comparisonData,
      });
    }

    // Store reference for zoom reset
    window.trendChart = chart;
    return chart;
  } catch (e) {
    console.error('Failed to initialize wide trend chart:', e);
    return null;
  }
}

// Register charts on module load
registerCharts();

// Initialize charts after HTMX swaps content
document.addEventListener('htmx:afterSwap', function(event) {
  // Use ChartManager to initialize all registered charts
  chartManager.initAll();

  // Also check for charts with data attributes (declarative approach)
  chartManager.initFromDataAttributes();
});

// Legacy function exports for backward compatibility
function initWideTrendChart() {
  chartManager.init('trend-chart');
}

function initPrTypeChart() {
  chartManager.init('pr-type-chart');
}

function initTechChart() {
  chartManager.init('tech-chart');
}

// Expose chart init functions globally for direct calls (backward compatibility)
window.initPrTypeChart = initPrTypeChart;
window.initTechChart = initTechChart;
window.initWideTrendChart = initWideTrendChart;
