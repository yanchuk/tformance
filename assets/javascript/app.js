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
});
