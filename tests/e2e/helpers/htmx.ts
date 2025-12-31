import { Page } from '@playwright/test';

/**
 * HTMX helper utilities for E2E tests.
 * Use these helpers to wait for HTMX requests and content swaps.
 */

/**
 * Wait for any pending HTMX request to complete.
 * HTMX adds 'htmx-request' class to body during requests.
 *
 * @param page - Playwright page object
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 *
 * @example
 * ```ts
 * await page.click('#submit-button');
 * await waitForHtmxComplete(page);
 * // Content has been swapped
 * ```
 */
export async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

/**
 * Wait for an HTMX swap to complete and a specific element to appear.
 *
 * @param page - Playwright page object
 * @param selector - CSS selector for element to wait for
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 *
 * @example
 * ```ts
 * await page.click('[hx-get="/api/data"]');
 * await waitForHtmxSwap(page, '.data-container');
 * // Element is now in DOM
 * ```
 */
export async function waitForHtmxSwap(page: Page, selector: string, timeout = 5000): Promise<void> {
  await page.waitForSelector(selector, { state: 'attached', timeout });
  await waitForHtmxComplete(page, timeout);
}

/**
 * Wait for HTMX content to load within a target container.
 *
 * @param page - Playwright page object
 * @param containerSelector - CSS selector for the HTMX target container
 * @param contentSelector - CSS selector for content expected after swap
 * @param timeout - Maximum wait time in milliseconds (default: 10000)
 *
 * @example
 * ```ts
 * await waitForHtmxContent(page, '#chart-container', 'canvas');
 * // Chart canvas is now loaded
 * ```
 */
export async function waitForHtmxContent(
  page: Page,
  containerSelector: string,
  contentSelector: string,
  timeout = 10000
): Promise<void> {
  const container = page.locator(containerSelector);
  await container.locator(contentSelector).waitFor({ state: 'attached', timeout });
  await waitForHtmxComplete(page, timeout);
}
