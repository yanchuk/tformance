import { test, expect, Page } from '@playwright/test';

/**
 * Smoke Tests - Critical Path Verification
 * Run with: npx playwright test smoke.spec.ts
 * Tag: @smoke
 *
 * These tests verify the critical path of the application:
 * - Infrastructure (health, static assets, 404)
 * - Frontend libraries (HTMX, Alpine.js)
 * - Authenticated user flow (login → dashboard → logout)
 */

/**
 * Wait for initial JS to be loaded.
 */
async function waitForJsInit(page: Page, timeout = 2000): Promise<void> {
  await page.waitForFunction(
    () => typeof window !== 'undefined' && document.readyState === 'complete',
    { timeout }
  );
}

/**
 * Wait for HTMX request to complete.
 */
async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

test.describe('Smoke Tests @smoke', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    // Either shows landing page or redirects to app (if logged in)
    await expect(page).toHaveTitle(/tformance/i);
  });

  test('login page loads', async ({ page }) => {
    await page.goto('/accounts/login/');
    // Should show login form or redirect if already logged in
    const title = await page.title();
    expect(title.toLowerCase()).toContain('tformance');
  });

  test('signup page loads', async ({ page }) => {
    await page.goto('/accounts/signup/');
    await expect(page).toHaveTitle(/tformance/i);
  });

  test('health endpoint responds', async ({ request }) => {
    const response = await request.get('/health/');
    // Health may return 500 if Celery is not running, but page should load
    // Accept 200 (all healthy) or 500 (degraded but server running)
    expect([200, 500]).toContain(response.status());
  });

  test('404 page renders for invalid URL', async ({ page }) => {
    const response = await page.goto('/nonexistent-page-12345/');
    expect(response?.status()).toBe(404);
  });

  test('static assets load without errors', async ({ page }) => {
    // Track failed requests
    const failedRequests: string[] = [];
    page.on('requestfailed', request => {
      const url = request.url();
      // Only track critical app assets, ignore:
      // - favicon
      // - external third-party scripts (PostHog, analytics, etc.)
      const isAppAsset = url.includes('localhost') || url.includes('127.0.0.1');
      const isCritical = url.includes('.js') || url.includes('.css');
      const isIgnored = url.includes('favicon') || url.includes('posthog') ||
                        url.includes('analytics') || url.includes('gtag');

      if (isAppAsset && isCritical && !isIgnored) {
        failedRequests.push(url);
      }
    });

    await page.goto('/');
    // Use domcontentloaded instead of networkidle (faster, more reliable in dev)
    await page.waitForLoadState('domcontentloaded');
    // Wait for initial JS to be loaded
    await waitForJsInit(page);

    // No critical app asset failures
    expect(failedRequests).toHaveLength(0);
  });

  test('HTMX library is loaded', async ({ page }) => {
    await page.goto('/');
    await waitForJsInit(page);

    const htmxLoaded = await page.evaluate(() => typeof (window as any).htmx !== 'undefined');
    expect(htmxLoaded).toBeTruthy();
  });

  test('Alpine.js library is loaded', async ({ page }) => {
    await page.goto('/');
    await waitForJsInit(page);

    const alpineLoaded = await page.evaluate(() => typeof (window as any).Alpine !== 'undefined');
    expect(alpineLoaded).toBeTruthy();
  });
});

test.describe('Critical Path @smoke', () => {
  test('authenticated user can access dashboard', async ({ page }) => {
    // Login
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();

    // Verify dashboard loads
    await expect(page).toHaveURL(/\/app/);
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('dashboard key sections load via HTMX', async ({ page }) => {
    // Login
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);

    // Wait for HTMX content to load
    await waitForHtmxComplete(page);

    // Verify key HTMX containers are populated
    await expect(page.locator('#key-metrics-container')).toBeVisible();
    await expect(page.locator('#ai-impact-container')).toBeVisible();

    // Verify actual content loaded (not just containers)
    await expect(page.getByText('PRs Merged').first()).toBeVisible();
  });

  test('logout redirects to home', async ({ page }) => {
    // Login first
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);

    // Navigate to logout page and confirm (use exact match to avoid sidebar button)
    await page.goto('/accounts/logout/');
    await page.getByRole('button', { name: 'Sign Out', exact: true }).click();

    // Should redirect to homepage after logout
    await expect(page).toHaveURL('/');

    // Verify can't access protected page anymore
    await page.goto('/app/');
    await expect(page).toHaveURL(/\/accounts\/login/);
  });
});
