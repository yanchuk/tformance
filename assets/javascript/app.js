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

  // PR Type Chart - 100% stacked area chart (shows composition trend)
  chartManager.register('pr-type-chart', (canvas, data) => {
    if (!data || !data.labels) return null;
    return chartManager.createStackedAreaChart(canvas.getContext('2d'), data, { yAxisLabel: 'PR Type Share %' });
  }, { dataId: 'pr-type-chart-data' });

  // Tech Chart - 100% stacked area chart (shows composition trend)
  chartManager.register('tech-chart', (canvas, data) => {
    if (!data || !data.labels) return null;
    return chartManager.createStackedAreaChart(canvas.getContext('2d'), data, { yAxisLabel: 'Tech Share %' });
  }, { dataId: 'tech-chart-data' });

  // Jira Linkage Chart - doughnut chart showing PR-Jira linkage
  chartManager.register('jira-linkage-chart', (canvas, data) => {
    if (!data) return null;
    const ctx = canvas.getContext('2d');
    return new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: ['Linked', 'Unlinked'],
        datasets: [{
          data: [data.linked_count || 0, data.unlinked_count || 0],
          backgroundColor: ['rgba(16, 185, 129, 0.8)', 'rgba(156, 163, 175, 0.3)'],  // success green, muted gray
          borderColor: ['#10B981', '#9CA3AF'],
          borderWidth: 2,
        }]
      },
      options: {
        cutout: '70%',
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: (context) => {
                const total = data.linked_count + data.unlinked_count;
                const pct = total > 0 ? Math.round((context.raw / total) * 100) : 0;
                return `${context.label}: ${context.raw} (${pct}%)`;
              }
            }
          }
        }
      }
    });
  }, { dataId: 'jira-linkage-data' });

  // SP Correlation Chart - grouped bar chart showing expected vs actual hours by bucket
  chartManager.register('sp-correlation-chart', (canvas, data) => {
    if (!data || !data.buckets || data.buckets.length === 0) return null;
    const ctx = canvas.getContext('2d');
    const labels = data.buckets.map(b => b.sp_range);
    const expectedHours = data.buckets.map(b => b.expected_hours);
    const actualHours = data.buckets.map(b => b.avg_hours);
    return new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Expected Hours',
            data: expectedHours,
            backgroundColor: 'rgba(90, 153, 151, 0.7)',  // accent teal
            borderColor: '#5a9997',
            borderWidth: 1,
          },
          {
            label: 'Actual Hours',
            data: actualHours,
            backgroundColor: 'rgba(249, 115, 22, 0.7)',  // primary orange
            borderColor: '#F97316',
            borderWidth: 1,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            title: {
              display: true,
              text: 'Story Points',
              color: '#9CA3AF',
            },
            ticks: { color: '#9CA3AF' },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
          },
          y: {
            title: {
              display: true,
              text: 'Hours',
              color: '#9CA3AF',
            },
            ticks: { color: '#9CA3AF' },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
            beginAtZero: true,
          }
        },
        plugins: {
          legend: {
            display: true,
            position: 'top',
            labels: { color: '#9CA3AF' },
          },
          tooltip: {
            callbacks: {
              afterBody: (context) => {
                const idx = context[0].dataIndex;
                const bucket = data.buckets[idx];
                return bucket ? `PRs: ${bucket.pr_count}` : '';
              }
            }
          }
        }
      }
    });
  }, { dataId: 'sp-correlation-data' });

  // Velocity Trend Chart - line chart showing story points over time
  chartManager.register('velocity-trend-chart', (canvas, data) => {
    if (!data || !data.periods || data.periods.length === 0) return null;
    const ctx = canvas.getContext('2d');
    const labels = data.periods.map(p => p.period_name);
    const storyPoints = data.periods.map(p => p.story_points);
    return new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Story Points',
            data: storyPoints,
            borderColor: '#F97316',  // primary orange
            backgroundColor: 'rgba(249, 115, 22, 0.1)',
            borderWidth: 2,
            fill: true,
            tension: 0.3,
            pointRadius: 4,
            pointBackgroundColor: '#F97316',
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: { color: '#9CA3AF' },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
          },
          y: {
            title: {
              display: true,
              text: 'Story Points',
              color: '#9CA3AF',
            },
            ticks: { color: '#9CA3AF' },
            grid: { color: 'rgba(156, 163, 175, 0.1)' },
            beginAtZero: true,
          }
        },
        plugins: {
          legend: {
            display: false,
          },
          tooltip: {
            callbacks: {
              afterBody: (context) => {
                const idx = context[0].dataIndex;
                const period = data.periods[idx];
                return period ? `Issues: ${period.issues_resolved}` : '';
              }
            }
          }
        }
      }
    });
  }, { dataId: 'velocity-trend-data' });

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
// Use requestAnimationFrame to ensure DOM is fully settled before initializing charts
document.addEventListener('htmx:afterSwap', function(event) {
  requestAnimationFrame(() => {
    // Use ChartManager to initialize all registered charts
    chartManager.initAll();

    // Also check for charts with data attributes (declarative approach)
    chartManager.initFromDataAttributes();
  });
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
