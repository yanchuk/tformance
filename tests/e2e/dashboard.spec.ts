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

  test.describe('App Home Page', () => {
    test('home page loads with welcome message', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Should have welcome heading
      await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
    });

    test('quick stats cards display', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Check for stat card labels
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
      await expect(page.getByText('Avg Cycle Time').first()).toBeVisible();
    });

    test('recent activity section displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Check for Recent Activity heading
      await expect(page.getByRole('heading', { name: 'Recent Activity' })).toBeVisible();
    });

    test('integration status section displays', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Check for Integrations heading in sidebar
      await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible();

      // Check for integration names
      await expect(page.getByText('GitHub').first()).toBeVisible();
      await expect(page.getByText('Jira').first()).toBeVisible();
      await expect(page.getByText('Slack').first()).toBeVisible();
    });

    test('view analytics button navigates to team dashboard', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('link', { name: 'View Analytics' }).click();

      await expect(page).toHaveURL(/\/app\/metrics\/dashboard\/team/);
      await expect(page.getByRole('heading', { name: 'Team Dashboard' })).toBeVisible();
    });
  });

  test.describe('Team Dashboard', () => {
    test('team dashboard page loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Team Dashboard' })).toBeVisible();
    });

    test('key metrics cards load via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check for metric labels
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
      await expect(page.getByText('Avg Cycle Time').first()).toBeVisible();
      await expect(page.getByText('AI-Assisted').first()).toBeVisible();
    });

    test('cycle time trend chart section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Cycle Time Trend' })).toBeVisible();
    });

    test('review distribution section loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page.getByRole('heading', { name: 'Review Distribution' })).toBeVisible();
    });

    test('AI detective leaderboard section loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();
    });

    test('recent pull requests table loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page.getByRole('heading', { name: 'Recent Pull Requests' })).toBeVisible();

      // Check for table headers (use container to avoid strict mode violation)
      const recentPrsSection = page.locator('#recent-prs-container');
      await expect(recentPrsSection.getByRole('columnheader', { name: 'Pull Request' })).toBeVisible();
      await expect(recentPrsSection.getByRole('columnheader', { name: 'Author' })).toBeVisible();
    });

    test('date range filter works', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Click 30d filter and verify URL changes
      await page.getByRole('link', { name: '30d' }).click();
      await expect(page).toHaveURL(/\?days=30/);
      // Verify the 30d button becomes active after HTMX swap
      await expect(page.locator('a[href="?days=30"].btn-primary')).toBeVisible();
    });

    test('date range filter does not duplicate navigation (HTMX partial swap)', async ({ page }) => {
      // This test ensures the HTMX partial swap fix is working correctly
      // Bug: Prior to fix, clicking filter buttons would nest the entire page inside content
      await page.goto('/app/metrics/dashboard/team/?days=7');
      await page.waitForLoadState('domcontentloaded');

      // Count initial navigation elements
      const initialNavCount = await page.locator('nav[aria-label="Main navigation"]').count();
      expect(initialNavCount).toBe(1);

      // Count Team Dashboard headings (should only be 1)
      const initialHeadingCount = await page.getByRole('heading', { name: 'Team Dashboard' }).count();
      expect(initialHeadingCount).toBe(1);

      // Click 30d filter (triggers HTMX request)
      await page.getByRole('link', { name: '30d' }).click();
      await page.waitForURL(/\?days=30/);
      await waitForHtmxComplete(page);

      // Verify navigation is NOT duplicated after HTMX swap
      const afterSwapNavCount = await page.locator('nav[aria-label="Main navigation"]').count();
      expect(afterSwapNavCount).toBe(1);

      // Verify Team Dashboard heading is still unique (not duplicated)
      const afterSwapHeadingCount = await page.getByRole('heading', { name: 'Team Dashboard' }).count();
      expect(afterSwapHeadingCount).toBe(1);

      // Verify content updated (30d should show more data than 7d)
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
    });

    test('multiple sequential filter clicks work without page reload', async ({ page }) => {
      // This test ensures HTMX target element is preserved after partial swaps
      // Bug: id="page-content" was outside partialdef, causing outerHTML swap to remove target
      await page.goto('/app/metrics/dashboard/team/?days=7');
      await page.waitForLoadState('domcontentloaded');

      // First click: 7d -> 30d
      await page.getByRole('link', { name: '30d' }).click();
      await expect(page).toHaveURL(/\?days=30/);
      await waitForHtmxComplete(page);

      // Second click: 30d -> 90d (this would fail before the fix)
      await page.getByRole('link', { name: '90d' }).click();
      await expect(page).toHaveURL(/\?days=90/);
      await waitForHtmxComplete(page);

      // Third click: 90d -> 7d (verify it still works)
      await page.getByRole('link', { name: '7d' }).click();
      await expect(page).toHaveURL(/\?days=7/);

      // Verify page content is still intact
      await expect(page.getByRole('heading', { name: 'Team Dashboard' })).toBeVisible();
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
    });

    // New high-value reports tests
    test('review time trend section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Review Time Trend' })).toBeVisible();
    });

    test('PR size distribution section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'PR Size Distribution' })).toBeVisible();
    });

    test('quality indicators section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Quality Indicators' })).toBeVisible();
    });

    test('reviewer workload section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Reviewer Workload' })).toBeVisible();
    });

    test('unlinked PRs section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'PRs Missing Jira Links' })).toBeVisible();
    });
  });

  // NOTE: CTO Dashboard tests removed - the /app/metrics/dashboard/cto/ URL is obsolete.
  // CTO dashboard functionality is now covered by analytics.spec.ts which tests:
  // - /app/metrics/overview/ (Analytics Overview - replaces CTO Dashboard)
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
