import * as JsCookie from "js-cookie";
import Chart from 'chart.js/auto';
import { DashboardCharts as AppDashboardCharts } from './dashboard/dashboard-charts';
import { createWideTrendChart, resetChartZoom, initTrendCharts } from './dashboard/trend-charts';
import { createSparkline, initSparklines, reinitSparklines } from './dashboard/sparkline';
export { AppDashboardCharts as DashboardCharts };
export { createWideTrendChart, resetChartZoom, initTrendCharts };
export { createSparkline, initSparklines, reinitSparklines };
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
  Cookies: JsCookie.default,
};

// Helper to destroy existing Chart.js instance on a canvas
function destroyChartIfExists(canvas) {
  if (canvas) {
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
      existingChart.destroy();
    }
  }
}

// Initialize charts after HTMX swaps content
document.addEventListener('htmx:afterSwap', function(event) {
  // AI Adoption Chart - uses weekly aggregated data
  const aiAdoptionData = document.getElementById('ai-adoption-data');
  const aiAdoptionChart = document.getElementById('ai-adoption-chart');
  if (aiAdoptionData && aiAdoptionChart) {
    destroyChartIfExists(aiAdoptionChart);
    const data = JSON.parse(aiAdoptionData.textContent);
    if (data && data.length > 0) {
      const ctx = aiAdoptionChart.getContext('2d');
      AppDashboardCharts.weeklyBarChart(ctx, data, "AI Adoption %");
    }
  }

  // Cycle Time Chart - uses weekly aggregated data
  const cycleTimeData = document.getElementById('cycle-time-data');
  const cycleTimeChart = document.getElementById('cycle-time-chart');
  if (cycleTimeData && cycleTimeChart) {
    destroyChartIfExists(cycleTimeChart);
    const data = JSON.parse(cycleTimeData.textContent);
    if (data && data.length > 0) {
      const ctx = cycleTimeChart.getContext('2d');
      AppDashboardCharts.weeklyBarChart(ctx, data, "Avg Cycle Time (hours)");
    }
  }

  // Review Time Chart - uses weekly aggregated data
  const reviewTimeData = document.getElementById('review-time-data');
  const reviewTimeChart = document.getElementById('review-time-chart');
  if (reviewTimeData && reviewTimeChart) {
    destroyChartIfExists(reviewTimeChart);
    const data = JSON.parse(reviewTimeData.textContent);
    if (data && data.length > 0) {
      const ctx = reviewTimeChart.getContext('2d');
      AppDashboardCharts.weeklyBarChart(ctx, data, "Avg Review Time (hours)");
    }
  }

  // Copilot Trend Chart - uses weekly aggregated data
  // Uses AI purple color to differentiate from standard metrics
  const copilotTrendData = document.getElementById('copilot-trend-data');
  const copilotTrendChart = document.getElementById('copilot-trend-chart');
  if (copilotTrendData && copilotTrendChart) {
    destroyChartIfExists(copilotTrendChart);
    const data = JSON.parse(copilotTrendData.textContent);
    if (data && data.length > 0) {
      const ctx = copilotTrendChart.getContext('2d');
      AppDashboardCharts.weeklyBarChart(ctx, data, "Copilot Acceptance Rate (%)", { ai: true });
    }
  }

  // PR Type Breakdown Chart - stacked bar chart
  initPrTypeChart();

  // Technology Breakdown Chart - stacked bar chart
  initTechChart();

  // Wide Trend Chart (main analytics chart)
  initWideTrendChart();
});

/**
 * Initialize PR Type breakdown stacked bar chart
 * Used on the Trends page to show PR types over time
 */
function initPrTypeChart() {
  const canvas = document.getElementById('pr-type-chart');
  if (!canvas) return;

  const chartDataEl = document.getElementById('pr-type-chart-data');
  if (!chartDataEl) return;

  try {
    const chartData = JSON.parse(chartDataEl.textContent);
    if (!chartData || !chartData.labels) return;

    // Destroy existing chart if any
    destroyChartIfExists(canvas);

    // Build Chart.js datasets
    const datasets = chartData.datasets.map(ds => ({
      label: ds.label,
      data: ds.data,
      backgroundColor: ds.color,
      borderColor: ds.color,
      borderWidth: 1,
      borderRadius: 2,
    }));

    new Chart(canvas, {
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
              text: 'PR Count',
              font: { family: "'DM Sans', sans-serif" },
            },
          },
        },
      },
    });
  } catch (e) {
    console.error('Failed to initialize PR type chart:', e);
  }
}

/**
 * Initialize Technology breakdown stacked bar chart
 * Used on the Trends page to show tech categories over time
 */
function initTechChart() {
  const canvas = document.getElementById('tech-chart');
  if (!canvas) return;

  const chartDataEl = document.getElementById('tech-chart-data');
  if (!chartDataEl) return;

  try {
    const chartData = JSON.parse(chartDataEl.textContent);
    if (!chartData || !chartData.labels) return;

    // Destroy existing chart if any
    destroyChartIfExists(canvas);

    // Build Chart.js datasets
    const datasets = chartData.datasets.map(ds => ({
      label: ds.label,
      data: ds.data,
      backgroundColor: ds.color,
      borderColor: ds.color,
      borderWidth: 1,
      borderRadius: 2,
    }));

    new Chart(canvas, {
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
              text: 'PR Count',
              font: { family: "'DM Sans', sans-serif" },
            },
          },
        },
      },
    });
  } catch (e) {
    console.error('Failed to initialize Tech chart:', e);
  }
}

/**
 * Initialize Wide Trend Chart (main analytics chart)
 * Reads data from json_script tags and creates chart
 * Supports both single metric and multi-metric comparison modes
 */
function initWideTrendChart() {
  const canvas = document.getElementById('trend-chart');
  if (!canvas) return;

  const chartDataEl = document.getElementById('trend-chart-data');
  const comparisonDataEl = document.getElementById('trend-comparison-data');
  if (!chartDataEl) return;

  // Check if chart creation functions are available
  if (!window.createWideTrendChart || !window.createMultiMetricChart) {
    // Retry after a short delay if modules not yet loaded
    setTimeout(initWideTrendChart, 100);
    return;
  }

  try {
    const chartData = JSON.parse(chartDataEl.textContent);
    const comparisonData = comparisonDataEl ? JSON.parse(comparisonDataEl.textContent) : null;
    const isMultiMetric = canvas.getAttribute('data-multi-metric') === 'true';

    // Destroy existing chart if any
    destroyChartIfExists(canvas);

    if (isMultiMetric) {
      // Multi-metric comparison mode
      window.trendChart = window.createMultiMetricChart(canvas, chartData);
    } else {
      // Single metric mode
      const metric = canvas.getAttribute('data-metric');
      // Convert old format to new if needed
      const data = chartData.datasets ? chartData.datasets[0]?.data?.map((value, i) => ({
        month: chartData.labels[i],
        value: value
      })) : chartData;

      window.trendChart = window.createWideTrendChart(canvas, data, {
        metric: metric,
        comparisonData: comparisonData,
      });
    }
  } catch (e) {
    console.error('Failed to initialize wide trend chart:', e);
  }
}

// Expose chart init functions globally for direct calls
window.initPrTypeChart = initPrTypeChart;
window.initTechChart = initTechChart;
window.initWideTrendChart = initWideTrendChart;
