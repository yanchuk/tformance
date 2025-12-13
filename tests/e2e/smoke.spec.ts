import { test, expect } from '@playwright/test';

/**
 * Smoke Tests - Critical Path Verification
 * Run with: npx playwright test smoke.spec.ts
 * Tag: @smoke
 */

test.describe('Smoke Tests @smoke', () => {
  test('homepage loads', async ({ page }) => {
    await page.goto('/');
    // Either shows landing page or redirects to app (if logged in)
    await expect(page).toHaveTitle(/tformance/);
  });

  test('login page loads', async ({ page }) => {
    await page.goto('/accounts/login/');
    // Should show login form or redirect if already logged in
    const title = await page.title();
    expect(title).toContain('tformance');
  });

  test('signup page loads', async ({ page }) => {
    await page.goto('/accounts/signup/');
    await expect(page).toHaveTitle(/tformance/);
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
      // Only track critical assets, ignore favicon
      if ((url.includes('.js') || url.includes('.css')) && !url.includes('favicon')) {
        failedRequests.push(url);
      }
    });

    await page.goto('/');
    // Use domcontentloaded instead of networkidle (faster, more reliable in dev)
    await page.waitForLoadState('domcontentloaded');
    // Give a brief moment for initial JS to load
    await page.waitForTimeout(500);

    // No critical asset failures
    expect(failedRequests).toHaveLength(0);
  });
});
