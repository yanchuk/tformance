import * as JsCookie from "js-cookie";
import Chart from 'chart.js/auto';
import { DashboardCharts as AppDashboardCharts } from './dashboard/dashboard-charts';
export { AppDashboardCharts as DashboardCharts };
export const Cookies = JsCookie.default;

// Ensure SiteJS global exists
if (typeof window.SiteJS === 'undefined') {
  window.SiteJS = {};
}

// Assign this entry's exports to SiteJS.app
window.SiteJS.app = {
  DashboardCharts: AppDashboardCharts,
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

  // Copilot Trend Chart - uses weekly aggregated data
  const copilotTrendData = document.getElementById('copilot-trend-data');
  const copilotTrendChart = document.getElementById('copilot-trend-chart');
  if (copilotTrendData && copilotTrendChart) {
    destroyChartIfExists(copilotTrendChart);
    const data = JSON.parse(copilotTrendData.textContent);
    if (data && data.length > 0) {
      const ctx = copilotTrendChart.getContext('2d');
      AppDashboardCharts.weeklyBarChart(ctx, data, "Copilot Acceptance Rate (%)");
    }
  }
});
