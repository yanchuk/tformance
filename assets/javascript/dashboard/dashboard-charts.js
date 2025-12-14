'use strict';
import Chart from 'chart.js/auto';

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
  return new Chart(ctx, {
    type: 'bar',
    data: {
      datasets: [{
        label: label,
        data: chartData,
      }]
    },
    options: {
      aspectRatio: 3,
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: label,
          }
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
  return new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [{
        label: label,
        fill: true,
        data: chartData,
      }]
    },
    options: {
      aspectRatio: 3,
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Date'
          }
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: label,
          }
        }
      }
    }
  });

}
/**
 * Bar chart for weekly/aggregated data (no daily interpolation)
 * Use this for data that already has aggregated weekly points.
 */
const weeklyBarChart = (ctx, data, label) => {
  // Convert data to Chart.js format: {labels: [], data: []}
  const chartData = data.map(item => ({
    x: item.date,
    y: item.count
  }));

  return new Chart(ctx, {
    type: 'bar',
    data: {
      datasets: [{
        label: label,
        data: chartData,
        backgroundColor: 'rgba(94, 158, 176, 0.7)',  // Softer teal
        borderColor: 'rgba(94, 158, 176, 1)',  // Softer teal
        borderWidth: 1
      }]
    },
    options: {
      aspectRatio: 3,
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Week'
          }
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: label,
          }
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
