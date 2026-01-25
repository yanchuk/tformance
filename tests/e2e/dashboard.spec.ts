import { test, expect, Page } from '@playwright/test';

/**
 * Dashboard Tests
 * Run with: npx playwright test dashboard.spec.ts
 * Tag: @dashboard
 *
 * These tests require a logged-in session.
 */

/**
 * Wait for HTMX request to complete.
 */
async function waitForHtmxComplete(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

test.describe('Dashboard Tests @dashboard', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('App Home Page (Unified Dashboard)', () => {
    test('home page loads with dashboard heading', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Should have Dashboard heading (unified dashboard)
      await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    });

    test('key metrics cards load via HTMX', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check for metric labels (lazy-loaded via HTMX)
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
      await expect(page.getByText('Avg Cycle Time').first()).toBeVisible();
    });

    test('needs attention section displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check for Needs Attention heading (new dashboard section)
      await expect(page.getByRole('heading', { name: 'Needs Attention' })).toBeVisible();
    });

    test('AI impact section displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check for AI Impact heading (new dashboard section)
      await expect(page.getByRole('heading', { name: 'AI Impact' })).toBeVisible();
    });

    test('top contributors section displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check for Top Contributors heading (new dashboard section)
      await expect(page.getByRole('heading', { name: 'Top Contributors' })).toBeVisible();
    });

    test('review distribution section displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check for Review Distribution heading
      await expect(page.getByRole('heading', { name: 'Review Distribution' })).toBeVisible();
    });

    test('integration status footer link displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Check for Manage Integrations link in footer
      await expect(page.getByRole('link', { name: /Manage Integrations/ })).toBeVisible();

      // Check for GitHub badge (should be connected in demo data)
      await expect(page.getByText('GitHub').first()).toBeVisible();
    });

    test('time range selector works', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Click 7d filter and verify URL changes
      await page.getByRole('link', { name: '7d' }).click();
      await expect(page).toHaveURL(/\?days=7/);

      // Click 90d filter
      await page.getByRole('link', { name: '90d' }).click();
      await expect(page).toHaveURL(/\?days=90/);
    });

    test('HTMX sections have correct containers', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Verify HTMX container IDs exist for lazy loading
      await expect(page.locator('#key-metrics-container')).toBeVisible();
      await expect(page.locator('#needs-attention-container')).toBeVisible();
      await expect(page.locator('#ai-impact-container')).toBeVisible();
      await expect(page.locator('#team-velocity-container')).toBeVisible();
      await expect(page.locator('#review-distribution-container')).toBeVisible();
    });
  });

  test.describe('Team Dashboard (Deprecated - Redirects to Unified Dashboard)', () => {
    test('team dashboard URL redirects to unified dashboard', async ({ page }) => {
      // The old team_dashboard URL (/app/metrics/dashboard/team/) is deprecated
      // and now redirects to the unified dashboard at /app/
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Should redirect to /app/ (unified dashboard)
      await expect(page).toHaveURL(/\/app\/$/);
      // Should show unified dashboard heading
      await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    });

    test('team dashboard preserves days param in redirect', async ({ page }) => {
      // Days parameter should be preserved when redirecting
      await page.goto('/app/metrics/dashboard/team/?days=7');
      await page.waitForLoadState('domcontentloaded');

      // Should redirect to /app/?days=7
      await expect(page).toHaveURL(/\/app\/\?days=7/);
    });
  });

  // NOTE: CTO Dashboard tests removed - the /app/metrics/dashboard/cto/ URL is obsolete.
  // CTO dashboard functionality is now covered by analytics.spec.ts which tests:
  // - /app/metrics/analytics/ (Analytics Overview - replaces CTO Dashboard)
  // - /app/metrics/analytics/* (new tabbed analytics pages)
  // See analytics.spec.ts for comprehensive coverage of analytics features.

  test.describe('Navigation', () => {
    test('can navigate to integrations page', async ({ page }) => {
      await page.goto('/app/');

      // Use first() to avoid strict mode violation (multiple Integrations links)
      await page.getByRole('link', { name: /Integrations/ }).first().click();

      await expect(page).toHaveURL(/\/integrations/);
      await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible();
    });

    test('can navigate to team settings', async ({ page }) => {
      await page.goto('/app/');

      await page.getByRole('link', { name: /Team Settings/ }).click();

      await expect(page).toHaveURL(/\/team/);
      await expect(page.getByRole('heading', { name: 'Team Details' })).toBeVisible();
    });

    test('can navigate to profile', async ({ page }) => {
      await page.goto('/app/');

      await page.getByRole('link', { name: /Profile/ }).click();

      await expect(page).toHaveURL(/\/users\/profile/);
      await expect(page.getByRole('heading', { name: 'My Details' })).toBeVisible();
    });
  });
});
