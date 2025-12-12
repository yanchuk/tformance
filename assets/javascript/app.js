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
  // AI Adoption Chart
  const aiAdoptionData = document.getElementById('ai-adoption-data');
  const aiAdoptionChart = document.getElementById('ai-adoption-chart');
  if (aiAdoptionData && aiAdoptionChart) {
    destroyChartIfExists(aiAdoptionChart);
    const data = JSON.parse(aiAdoptionData.textContent);
    if (data && data.length > 0) {
      const ctx = aiAdoptionChart.getContext('2d');
      const start = new Date(data[0].date);
      const end = new Date(data[data.length - 1].date);
      AppDashboardCharts.barChartWithDates(ctx, start, end, data, "AI Adoption %");
    }
  }

  // Cycle Time Chart
  const cycleTimeData = document.getElementById('cycle-time-data');
  const cycleTimeChart = document.getElementById('cycle-time-chart');
  if (cycleTimeData && cycleTimeChart) {
    destroyChartIfExists(cycleTimeChart);
    const data = JSON.parse(cycleTimeData.textContent);
    if (data && data.length > 0) {
      const ctx = cycleTimeChart.getContext('2d');
      const start = new Date(data[data.length - 1].date);
      const end = new Date(data[0].date);
      AppDashboardCharts.barChartWithDates(ctx, start, end, data, "Avg Cycle Time (hours)");
    }
  }
});
