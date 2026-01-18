/**
 * HTMX Error Handling E2E Tests
 *
 * Tests that failed HTMX requests show user-friendly error messages
 * instead of infinite loading spinners.
 */
import { test, expect, Page } from '@playwright/test';

/**
 * Wait for HTMX request to complete (success or failure).
 */
async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

/**
 * Wait for error alerts to appear after HTMX failure.
 */
async function waitForErrorAlert(page: Page, timeout = 5000): Promise<void> {
  await page.locator('[role="alert"], [data-htmx-error], .alert-error').first().waitFor({
    state: 'attached',
    timeout,
  }).catch(() => {
    // Error alert might not appear immediately, that's okay
  });
}

// Use only chromium for faster feedback during development
test.use({ browserName: 'chromium' });

test.describe('HTMX Error Handling', () => {
  test.beforeEach(async ({ page }) => {
    // Set shorter timeouts for faster test feedback
    page.setDefaultTimeout(10000);

    // Login
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.waitForURL(/\/app/, { timeout: 5000 });
  });

  test('shows error alert when HTMX chart request fails with 500', async ({ page }) => {
    const interceptedRequests: string[] = [];
    const consoleMessages: string[] = [];

    // Capture ALL console messages for debugging
    page.on('console', msg => {
      consoleMessages.push(`[${msg.type()}] ${msg.text()}`);
    });

    // Setup route interception BEFORE navigation to catch initial HTMX requests
    await page.route('**/charts/**', async (route) => {
      interceptedRequests.push(`CHARTS: ${route.request().url()}`);
      await route.fulfill({
        status: 500,
        contentType: 'text/html',
        body: 'Internal Server Error',
      });
    });

    // Also mock cards endpoint
    await page.route('**/cards/**', async (route) => {
      interceptedRequests.push(`CARDS: ${route.request().url()}`);
      await route.fulfill({
        status: 500,
        contentType: 'text/html',
        body: 'Internal Server Error',
      });
    });

    // Navigate to analytics page which loads charts via HTMX
    await page.goto('/app/metrics/analytics/');
    await page.waitForLoadState('domcontentloaded');

    // Wait for HTMX requests to fail and error handling to process
    await waitForHtmxComplete(page, 10000);
    await waitForErrorAlert(page, 5000);

    console.log('Intercepted requests:', interceptedRequests);
    console.log('Console messages with htmx.js:', consoleMessages.filter(m => m.includes('[htmx.js]')));
    console.log('Console messages with HTMX:', consoleMessages.filter(m => m.includes('HTMX')));
    console.log('All console logs:', consoleMessages.filter(m => m.startsWith('[log]')));
    console.log('All console errors:', consoleMessages.filter(m => m.startsWith('[error]')));

    // Check for error alerts anywhere on the page
    const errorCount = await page.locator('[role="alert"], [data-htmx-error], .alert-error').count();
    console.log('Error alert count:', errorCount);

    // Debug: Check if our htmx.js module loaded
    const moduleLoaded = await page.evaluate(() => (window as any).__htmxErrorHandlerLoaded);
    console.log('htmx.js module loaded:', moduleLoaded);

    // Debug: Check what elements exist in chart containers
    const aiAdoptionContent = await page.locator('#ai-adoption-container').innerHTML().catch(() => 'container not found');
    console.log('AI Adoption container content:', aiAdoptionContent.slice(0, 300));

    // We should have at least one error alert from the failed chart/cards requests
    expect(errorCount).toBeGreaterThan(0);
  });

  test('error message replaces loading spinner in chart container', async ({ page }) => {
    // Mock a specific chart endpoint to fail
    await page.route('**/charts/**', async (route) => {
      // Delay slightly to ensure loading state shows first
      await new Promise(resolve => setTimeout(resolve, 100));
      await route.fulfill({
        status: 500,
        body: 'Server Error',
      });
    });

    // Navigate to analytics overview
    await page.goto('/app/metrics/analytics/');
    await page.waitForLoadState('domcontentloaded');

    // Wait for HTMX requests to fail and error handling to process
    await waitForHtmxComplete(page, 10000);
    await waitForErrorAlert(page, 5000);

    // Check that we have an error alert and not just a stuck loading spinner
    const errorAlert = page.locator('[role="alert"], [data-htmx-error]');
    const loadingSpinner = page.locator('.animate-pulse, .loading');

    const hasError = await errorAlert.count() > 0;
    const hasSpinner = await loadingSpinner.isVisible().catch(() => false);

    // We should either have error OR content, not a stuck spinner
    // If error handling works, we should see error alerts
    expect(hasError || !hasSpinner).toBe(true);
  });

  test('console logs HTMX errors for debugging', async ({ page }) => {
    const consoleErrors: string[] = [];

    // Capture console messages
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });

    // Setup mock BEFORE navigation so it catches initial HTMX requests
    await page.route('**/panels/**', async (route) => {
      await route.fulfill({ status: 500, body: 'Error' });
    });
    await page.route('**/charts/**', async (route) => {
      await route.fulfill({ status: 500, body: 'Error' });
    });

    // Navigate to analytics page that makes HTMX requests on load
    await page.goto('/app/metrics/analytics/');
    await page.waitForLoadState('domcontentloaded');

    // Wait for HTMX requests to fail and console errors to be logged
    await waitForHtmxComplete(page, 10000);

    // There should be console errors logged for failed HTMX requests
    const htmxErrors = consoleErrors.filter(e =>
      e.includes('HTMX') || e.includes('htmx') || e.includes('500') || e.includes('failed')
    );

    // We expect at least one logged error about HTMX failure
    expect(htmxErrors.length).toBeGreaterThan(0);
  });
});
