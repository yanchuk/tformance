'use strict';

/**
 * Tformance Chart.js Theme
 * "Sunset Dashboard" warm color palette
 *
 * This theme provides consistent styling for all Chart.js charts
 * in the application, using the warm coral/orange color scheme.
 */

export const TformanceChartTheme = {
  // Chart colors - warm palette matching design-system.css
  colors: {
    primary: '#F97316',     // Coral orange - main data
    secondary: '#FDA4AF',   // Warm rose - secondary data
    success: '#2DD4BF',     // Teal - positive metrics
    warning: '#FBBF24',     // Amber - warning states
    error: '#F87171',       // Soft red - negative metrics
    ai: '#C084FC',          // Soft purple - AI-related (Copilot)
    muted: '#A3A3A3',       // Neutral gray
  },

  // Bar chart dataset styling
  bar: {
    backgroundColor: 'rgba(249, 115, 22, 0.7)',   // primary with opacity
    borderColor: '#F97316',
    borderWidth: 1,
    borderRadius: 4,
    hoverBackgroundColor: 'rgba(249, 115, 22, 0.9)',
  },

  // AI-specific bar styling (for Copilot charts)
  barAI: {
    backgroundColor: 'rgba(192, 132, 252, 0.7)',  // ai purple with opacity
    borderColor: '#C084FC',
    borderWidth: 1,
    borderRadius: 4,
    hoverBackgroundColor: 'rgba(192, 132, 252, 0.9)',
  },

  // Line chart dataset styling
  line: {
    backgroundColor: 'rgba(249, 115, 22, 0.1)',
    borderColor: '#F97316',
    borderWidth: 2,
    tension: 0.3,
    fill: true,
    pointBackgroundColor: '#F97316',
    pointBorderColor: '#171717',
    pointBorderWidth: 2,
    pointRadius: 4,
    pointHoverRadius: 6,
  },

  // Grid styling
  grid: {
    color: 'rgba(163, 163, 163, 0.1)',  // muted with low opacity
    borderColor: '#404040',              // elevated
  },

  // Axis labels
  axis: {
    color: '#A3A3A3',        // muted text
    titleColor: '#D4D4D4',   // neutral-300
  },

  // Tooltip styling
  tooltip: {
    backgroundColor: '#262626',  // surface
    borderColor: '#404040',      // elevated
    titleColor: '#FAFAFA',       // neutral-50
    bodyColor: '#D4D4D4',        // neutral-300
    borderWidth: 1,
    cornerRadius: 8,
    padding: 12,
  },

  // Legend styling
  legend: {
    color: '#D4D4D4',  // neutral-300
  },
};

// Color palette for multi-series charts
export const chartColorPalette = [
  '#F97316',  // primary - coral orange
  '#2DD4BF',  // success - teal
  '#C084FC',  // AI - purple
  '#FDA4AF',  // secondary - rose
  '#FBBF24',  // warning - amber
  '#60A5FA',  // info - blue
];

/**
 * Get Chart.js default options with theme styling
 * @returns {Object} Chart.js options object
 */
export function getChartDefaults() {
  return {
    responsive: true,
    maintainAspectRatio: true,
    plugins: {
      legend: {
        labels: {
          color: TformanceChartTheme.legend.color,
          font: {
            family: "'DM Sans', sans-serif",
          },
        },
      },
      tooltip: {
        backgroundColor: TformanceChartTheme.tooltip.backgroundColor,
        titleColor: TformanceChartTheme.tooltip.titleColor,
        bodyColor: TformanceChartTheme.tooltip.bodyColor,
        borderColor: TformanceChartTheme.tooltip.borderColor,
        borderWidth: TformanceChartTheme.tooltip.borderWidth,
        cornerRadius: TformanceChartTheme.tooltip.cornerRadius,
        padding: TformanceChartTheme.tooltip.padding,
        titleFont: {
          family: "'DM Sans', sans-serif",
          weight: 'bold',
        },
        bodyFont: {
          family: "'JetBrains Mono', monospace",
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: TformanceChartTheme.axis.color,
          font: {
            family: "'DM Sans', sans-serif",
          },
        },
        title: {
          color: TformanceChartTheme.axis.titleColor,
          font: {
            family: "'DM Sans', sans-serif",
          },
        },
        grid: {
          color: TformanceChartTheme.grid.color,
        },
        border: {
          color: TformanceChartTheme.grid.borderColor,
        },
      },
      y: {
        ticks: {
          color: TformanceChartTheme.axis.color,
          font: {
            family: "'JetBrains Mono', monospace",
          },
        },
        title: {
          color: TformanceChartTheme.axis.titleColor,
          font: {
            family: "'DM Sans', sans-serif",
          },
        },
        grid: {
          color: TformanceChartTheme.grid.color,
        },
        border: {
          color: TformanceChartTheme.grid.borderColor,
        },
      },
    },
  };
}

/**
 * Get bar chart styling based on options
 * @param {Object} options - { ai: boolean } for AI-specific styling
 * @returns {Object} Bar dataset styling
 */
export function getBarStyle(options = {}) {
  if (options.ai) {
    return { ...TformanceChartTheme.barAI };
  }
  return { ...TformanceChartTheme.bar };
}
