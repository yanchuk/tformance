import { test as base, expect, Page } from '@playwright/test';
import { loginAs, TestUserRole, TEST_USERS } from './test-users';

/**
 * Wait for HTMX request to complete.
 */
async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

/**
 * Extended test fixtures for common e2e test patterns.
 *
 * Usage:
 * ```ts
 * import { test, expect } from './fixtures/test-fixtures';
 *
 * test('my test', async ({ authenticatedPage }) => {
 *   // Already logged in as admin
 *   await authenticatedPage.goto('/app/');
 * });
 * ```
 */

// Define fixture types
type TestFixtures = {
  /** Page that is already authenticated as admin user */
  authenticatedPage: Page;
  /** Page navigated to team dashboard, authenticated as admin */
  dashboardPage: Page;
  /** Page navigated to Analytics dashboard, authenticated as admin */
  analyticsDashboardPage: Page;
  /** Page navigated to integrations hub, authenticated as admin */
  integrationsPage: Page;
  /** Page navigated to app home, authenticated as admin */
  appHomePage: Page;
};

/**
 * Extended test function with custom fixtures.
 */
export const test = base.extend<TestFixtures>({
  /**
   * Authenticated page fixture.
   * Logs in as admin before test and provides the page.
   */
  authenticatedPage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await use(page);
  },

  /**
   * Dashboard page fixture.
   * Logs in and navigates to team dashboard.
   */
  dashboardPage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await page.goto('/app/metrics/dashboard/team/');
    // Wait for HTMX content to load
    await page.waitForSelector('.stat', { timeout: 10000 });
    await use(page);
  },

  /**
   * Analytics dashboard page fixture.
   * Logs in and navigates to analytics overview dashboard.
   */
  analyticsDashboardPage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await page.goto('/app/metrics/analytics/');
    // Wait for HTMX content to load
    await page.waitForSelector('.stat', { timeout: 10000 });
    await use(page);
  },

  /**
   * Integrations page fixture.
   * Logs in and navigates to integrations hub.
   */
  integrationsPage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await page.goto('/app/integrations/');
    await page.waitForLoadState('networkidle');
    await use(page);
  },

  /**
   * App home page fixture.
   * Logs in and navigates to app home.
   */
  appHomePage: async ({ page }, use) => {
    await loginAs(page, 'admin');
    await page.goto('/app/');
    await page.waitForLoadState('networkidle');
    await use(page);
  },
});

// Re-export expect for convenience
export { expect };

/**
 * Helper to wait for HTMX content to load.
 * HTMX swaps content asynchronously, so we need explicit waits.
 *
 * @param page - Playwright page
 * @param selector - CSS selector to wait for
 * @param timeout - Maximum wait time in ms
 */
export async function waitForHtmxContent(
  page: Page,
  selector: string,
  timeout: number = 10000
): Promise<void> {
  await page.waitForSelector(selector, { timeout });
  // Ensure HTMX has finished processing
  await waitForHtmxComplete(page, timeout);
}

/**
 * Helper to click a date range filter button and wait for content update.
 *
 * @param page - Playwright page
 * @param range - Date range to select ('7d', '30d', '90d')
 */
export async function selectDateRange(
  page: Page,
  range: '7d' | '30d' | '90d'
): Promise<void> {
  const buttonText = {
    '7d': '7 Days',
    '30d': '30 Days',
    '90d': '90 Days',
  }[range];

  await page.getByRole('button', { name: buttonText }).click();
  // Wait for HTMX to update content
  await waitForHtmxComplete(page);
}

/**
 * Helper to extract a stat card value.
 *
 * @param page - Playwright page
 * @param cardTitle - Title of the stat card
 * @returns The value text from the card
 */
export async function getStatCardValue(
  page: Page,
  cardTitle: string
): Promise<string> {
  const card = page.locator('.stat').filter({ hasText: cardTitle });
  const value = card.locator('.stat-value');
  return value.textContent() ?? '';
}

/**
 * Helper to check if a chart has rendered with data.
 *
 * @param page - Playwright page
 * @param chartContainerId - ID or selector of chart container
 * @returns true if chart appears to have data
 */
export async function chartHasData(
  page: Page,
  chartContainerId: string
): Promise<boolean> {
  const container = page.locator(chartContainerId);
  // Chart.js renders to canvas
  const canvas = container.locator('canvas');
  return canvas.isVisible();
}

/**
 * Helper to navigate using the sidebar/nav menu.
 *
 * @param page - Playwright page
 * @param linkText - Text of the navigation link
 */
export async function navigateTo(page: Page, linkText: string): Promise<void> {
  await page.getByRole('link', { name: linkText }).click();
  await page.waitForLoadState('networkidle');
}

/**
 * Helper to open a dropdown menu.
 *
 * @param page - Playwright page
 * @param buttonText - Text of the dropdown trigger button
 */
export async function openDropdown(page: Page, buttonText: string): Promise<void> {
  await page.getByRole('button', { name: buttonText }).click();
  // Wait for dropdown to be visible
  await page.locator('[role="menu"], .dropdown-content').first().waitFor({ state: 'visible', timeout: 2000 }).catch(() => {});
}

/**
 * Helper to confirm a modal action.
 *
 * @param page - Playwright page
 * @param confirmText - Text of the confirm button (default: 'Confirm')
 */
export async function confirmModal(
  page: Page,
  confirmText: string = 'Confirm'
): Promise<void> {
  await page.getByRole('button', { name: confirmText }).click();
  // Wait for modal to close
  await page.locator('dialog[open], .modal.modal-open').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
}

/**
 * Helper to cancel/close a modal.
 *
 * @param page - Playwright page
 * @param cancelText - Text of the cancel button (default: 'Cancel')
 */
export async function cancelModal(
  page: Page,
  cancelText: string = 'Cancel'
): Promise<void> {
  await page.getByRole('button', { name: cancelText }).click();
  // Wait for modal to close
  await page.locator('dialog[open], .modal.modal-open').waitFor({ state: 'hidden', timeout: 5000 }).catch(() => {});
}
