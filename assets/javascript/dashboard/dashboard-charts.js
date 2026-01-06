'use strict';
import Chart from 'chart.js/auto';
import ChartDataLabels from 'chartjs-plugin-datalabels';
import { TformanceChartTheme, getChartDefaults, getBarStyle } from './chart-theme';

// Register the datalabels plugin globally
Chart.register(ChartDataLabels);

function listToDict(list) {
  // gpt
  return list.reduce((acc, item) => {
    acc[item.date] = item.count;
    return acc;
  }, {});
}

function toDateString(dateObj) {
  return dateObj.toISOString().split('T')[0];
}

function getTimeSeriesData(start, end, data) {
  let dataDict = listToDict(data);
  let chartData = [];
  let current = new Date(start);
  while(current <= end){
    let curString = toDateString(current)
    chartData.push({
      x: curString,
      y: dataDict[curString] || 0,
    })
    current.setDate(current.getDate() + 1);
  }
  return chartData;
}

const barChartWithDates = (ctx, start, end, data, label) => {
  const chartData = getTimeSeriesData(start, end, data);
  const barStyle = getBarStyle();
  const chartDefaults = getChartDefaults();

  return new Chart(ctx, {
    type: 'bar',
    data: {
      datasets: [{
        label: label,
        data: chartData,
        backgroundColor: barStyle.backgroundColor,
        borderColor: barStyle.borderColor,
        borderWidth: barStyle.borderWidth,
        borderRadius: barStyle.borderRadius,
        hoverBackgroundColor: barStyle.hoverBackgroundColor,
      }]
    },
    options: {
      layout: {
        padding: {
          top: 20  // Space for data labels above tall bars
        }
      },
      maintainAspectRatio: false,
      responsive: true,
      plugins: {
        legend: {
          display: false
        },
        tooltip: chartDefaults.plugins.tooltip,
        datalabels: {
          anchor: 'end',
          align: 'top',
          offset: 2,
          color: TformanceChartTheme.text.primary,
          font: {
            size: 10,
            weight: 'bold',
          },
          formatter: (value) => {
            if (!value || value.y === 0) return '';
            const num = value.y;
            return Number.isInteger(num) ? num : num.toFixed(1);
          },
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Date',
            color: TformanceChartTheme.axis.titleColor,
          },
          ticks: {
            color: TformanceChartTheme.axis.color,
          },
          grid: {
            color: TformanceChartTheme.grid.color,
          },
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: label,
            color: TformanceChartTheme.axis.titleColor,
          },
          ticks: {
            color: TformanceChartTheme.axis.color,
          },
          grid: {
            color: TformanceChartTheme.grid.color,
          },
        }
      }
    }
  });
}

const cumulativeChartWithDates = (ctx, start, end, data, label, startValue) => {
  const chartData = getTimeSeriesData(start, end, data);
  let currentValue = startValue || 0;
  for (let row of chartData) {
    currentValue += row.y;
    row.y = currentValue;
  }

  const lineStyle = TformanceChartTheme.line;
  const chartDefaults = getChartDefaults();

  return new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: label,
        fill: lineStyle.fill,
        data: chartData,
        backgroundColor: lineStyle.backgroundColor,
        borderColor: lineStyle.borderColor,
        borderWidth: lineStyle.borderWidth,
        tension: lineStyle.tension,
        pointBackgroundColor: lineStyle.pointBackgroundColor,
        pointBorderColor: lineStyle.pointBorderColor,
        pointBorderWidth: lineStyle.pointBorderWidth,
        pointRadius: lineStyle.pointRadius,
        pointHoverRadius: lineStyle.pointHoverRadius,
      }]
    },
    options: {
      maintainAspectRatio: false,
      responsive: true,
      plugins: {
        legend: {
          display: false
        },
        tooltip: chartDefaults.plugins.tooltip,
        datalabels: {
          display: false, // Disable data labels for line charts (too cluttered)
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Date',
            color: TformanceChartTheme.axis.titleColor,
          },
          ticks: {
            color: TformanceChartTheme.axis.color,
          },
          grid: {
            color: TformanceChartTheme.grid.color,
          },
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: label,
            color: TformanceChartTheme.axis.titleColor,
          },
          ticks: {
            color: TformanceChartTheme.axis.color,
          },
          grid: {
            color: TformanceChartTheme.grid.color,
          },
        }
      }
    }
  });
}
/**
 * Bar chart for weekly/aggregated data (no daily interpolation)
 * Use this for data that already has aggregated weekly points.
 * @param {CanvasRenderingContext2D} ctx - Canvas context
 * @param {Array} data - Chart data [{date, count}, ...]
 * @param {string} label - Y-axis label
 * @param {Object} options - { ai: boolean } for AI-specific styling (purple)
 */
const weeklyBarChart = (ctx, data, label, options = {}) => {
  // Convert data to Chart.js format: {labels: [], data: []}
  const chartData = data.map(item => ({
    x: item.date,
    y: item.count
  }));

  // Get theme-based bar styling
  const barStyle = getBarStyle(options);
  const chartDefaults = getChartDefaults();

  return new Chart(ctx, {
    type: 'bar',
    data: {
      datasets: [{
        label: label,
        data: chartData,
        backgroundColor: barStyle.backgroundColor,
        borderColor: barStyle.borderColor,
        borderWidth: barStyle.borderWidth,
        borderRadius: barStyle.borderRadius,
        hoverBackgroundColor: barStyle.hoverBackgroundColor,
      }]
    },
    options: {
      layout: {
        padding: {
          top: 20  // Space for data labels above tall bars
        }
      },
      maintainAspectRatio: false,
      responsive: true,
      plugins: {
        legend: {
          display: false
        },
        tooltip: chartDefaults.plugins.tooltip,
        datalabels: {
          anchor: 'end',
          align: 'top',
          offset: 2,
          color: TformanceChartTheme.text.primary,
          font: {
            size: 10,
            weight: 'bold',
          },
          formatter: (value) => {
            // Don't show labels for zero or null values
            if (!value || value.y === 0) return '';
            // Format the value - show 1 decimal for floats, integer for whole numbers
            const num = value.y;
            return Number.isInteger(num) ? num : num.toFixed(1);
          },
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Week',
            color: TformanceChartTheme.axis.titleColor,
          },
          ticks: {
            color: TformanceChartTheme.axis.color,
          },
          grid: {
            color: TformanceChartTheme.grid.color,
          },
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: label,
            color: TformanceChartTheme.axis.titleColor,
          },
          ticks: {
            color: TformanceChartTheme.axis.color,
          },
          grid: {
            color: TformanceChartTheme.grid.color,
          },
        }
      }
    }
  });
};

export const DashboardCharts = {
  barChartWithDates: barChartWithDates,
  cumulativeChartWithDates: cumulativeChartWithDates,
  weeklyBarChart: weeklyBarChart,
};
