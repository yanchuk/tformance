import { Page } from '@playwright/test';
import { waitForHtmxComplete } from './htmx';

/**
 * Chart.js helper utilities for E2E tests.
 * Use these helpers to wait for charts to render and verify chart data.
 */

/**
 * Wait for a Chart.js chart to be fully rendered on a canvas.
 *
 * @param page - Playwright page object
 * @param chartId - ID of the chart canvas element (not container)
 * @param timeout - Maximum wait time in milliseconds (default: 10000)
 *
 * @example
 * ```ts
 * await waitForChart(page, 'ai-adoption-chart');
 * // Chart.js instance is created and rendered
 * ```
 */
export async function waitForChart(
  page: Page,
  chartId: string,
  timeout = 10000
): Promise<void> {
  await page.waitForFunction(
    (id) => {
      const canvas = document.getElementById(id) as HTMLCanvasElement;
      if (!canvas) return false;
      const Chart = (window as any).Chart;
      return Chart && Chart.getChart && Chart.getChart(canvas);
    },
    chartId,
    { timeout }
  );
}

/**
 * Check if a chart has rendered with data (has a canvas element).
 *
 * @param page - Playwright page object
 * @param chartId - ID of the chart container element
 * @returns true if chart has a visible canvas
 *
 * @example
 * ```ts
 * const hasData = await chartHasData(page, 'cycle-time-chart');
 * expect(hasData).toBe(true);
 * ```
 */
export async function chartHasData(page: Page, chartId: string): Promise<boolean> {
  const canvas = page.locator(`#${chartId} canvas`);
  return canvas.isVisible().catch(() => false);
}

/**
 * Wait for multiple charts to be loaded.
 *
 * @param page - Playwright page object
 * @param chartIds - Array of chart container IDs
 * @param timeout - Maximum wait time per chart in milliseconds (default: 5000)
 *
 * @example
 * ```ts
 * await waitForCharts(page, ['ai-adoption-chart', 'cycle-time-chart']);
 * // Both charts are loaded
 * ```
 */
export async function waitForCharts(
  page: Page,
  chartIds: string[],
  timeout = 5000
): Promise<void> {
  await Promise.all(chartIds.map(id => waitForChart(page, id, timeout)));
}

/**
 * Get the chart instance from a canvas element (if accessible).
 * Note: This may not work in all cases due to Chart.js initialization.
 *
 * @param page - Playwright page object
 * @param chartId - ID of the chart container element
 * @returns Chart configuration or null if not accessible
 */
export async function getChartConfig(
  page: Page,
  chartId: string
): Promise<unknown | null> {
  return page.evaluate((id) => {
    const canvas = document.querySelector(`#${id} canvas`) as HTMLCanvasElement;
    if (!canvas) return null;

    // Chart.js stores instance on canvas
    const chart = (window as any).Chart?.getChart?.(canvas);
    if (!chart) return null;

    return {
      type: chart.config.type,
      labels: chart.data.labels,
      datasetsCount: chart.data.datasets?.length,
    };
  }, chartId);
}
