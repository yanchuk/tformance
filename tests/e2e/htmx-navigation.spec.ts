/**
 * HTMX Navigation Tests
 *
 * Tests that state persists correctly after HTMX navigation:
 * - Time range button highlighting
 * - Tab navigation
 * - Browser back/forward
 */
import { test, expect, Page } from '@playwright/test';

test.use({ browserName: 'chromium' });

/**
 * Wait for Alpine.js dateRange store to be initialized.
 */
async function waitForAlpineStore(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => {
      const Alpine = (window as any).Alpine;
      return Alpine && Alpine.store && Alpine.store('dateRange') !== undefined;
    },
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

test.describe('HTMX Navigation State', () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(15000);

    // Login
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.waitForURL(/\/app/, { timeout: 5000 });
  });

  test.describe('Time Range Button Highlighting', () => {
    test('90d button stays highlighted after tab navigation', async ({ page }) => {
      // Navigate to analytics overview
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Click 90d button to select it
      const btn90d = page.locator('button:has-text("90d"), a:has-text("90d")').first();
      await btn90d.click();
      await waitForHtmxComplete(page);

      // Verify 90d is highlighted (has btn-primary class)
      const is90dActive = await btn90d.evaluate((el) => {
        return el.classList.contains('btn-primary') || el.className.includes('btn-primary');
      });
      expect(is90dActive).toBe(true);

      // Now click on Quality tab (HTMX navigation)
      const qualityTab = page.getByRole('tab', { name: 'Quality' });
      await qualityTab.click();
      await page.waitForURL(/\/quality/);
      await waitForHtmxComplete(page);

      // After HTMX swap, 90d should still be highlighted
      const btn90dAfterSwap = page.locator('button:has-text("90d"), a:has-text("90d")').first();
      const is90dActiveAfterSwap = await btn90dAfterSwap.evaluate((el) => {
        return el.classList.contains('btn-primary') || el.className.includes('btn-primary');
      });
      expect(is90dActiveAfterSwap).toBe(true);
    });

    test('7d button stays highlighted after tab navigation', async ({ page }) => {
      // Navigate to analytics and select 7d
      await page.goto('/app/metrics/analytics/?days=7');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Verify 7d is highlighted
      const btn7d = page.locator('button:has-text("7d"), a:has-text("7d")').first();
      const is7dActive = await btn7d.evaluate((el) => {
        return el.classList.contains('btn-primary') || el.className.includes('btn-primary');
      });
      expect(is7dActive).toBe(true);

      // Click on AI Adoption tab
      const aiTab = page.getByRole('tab', { name: 'AI Adoption' });
      await aiTab.click();
      await page.waitForURL(/\/ai-adoption/);
      await waitForHtmxComplete(page);

      // 7d should still be highlighted after swap
      const btn7dAfterSwap = page.locator('button:has-text("7d"), a:has-text("7d")').first();
      const is7dActiveAfterSwap = await btn7dAfterSwap.evaluate((el) => {
        return el.classList.contains('btn-primary') || el.className.includes('btn-primary');
      });
      expect(is7dActiveAfterSwap).toBe(true);
    });

    test('URL params preserved after tab navigation', async ({ page }) => {
      // Start with 90d param
      await page.goto('/app/metrics/analytics/?days=90');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Verify URL has days=90
      expect(page.url()).toContain('days=90');

      // Click on Delivery tab
      const deliveryTab = page.getByRole('tab', { name: 'Delivery' });
      await deliveryTab.click();
      await page.waitForURL(/days=90/);

      // URL should still have days=90
      expect(page.url()).toContain('days=90');
    });
  });

  test.describe('Browser History', () => {
    test('time range preserved on browser back', async ({ page }) => {
      // Start at analytics overview with 7d
      await page.goto('/app/metrics/analytics/?days=7');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Verify 7d is highlighted
      const btn7dInitial = page.locator('button:has-text("7d"), a:has-text("7d")').first();
      await expect(btn7dInitial).toBeVisible();

      // Click AI Adoption tab (pushes new URL to history)
      const aiTab = page.getByRole('tab', { name: 'AI Adoption' });
      await aiTab.click();
      await page.waitForURL(/ai-adoption/);

      // URL should have days=7 on AI Adoption page
      expect(page.url()).toContain('days=7');
      expect(page.url()).toContain('ai-adoption');

      // Go back to overview
      await page.goBack();
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Should be back at overview with days=7
      expect(page.url()).toContain('days=7');

      // 7d button should be visible and active after back navigation
      const btn7dAfterBack = page.locator('button:has-text("7d"), a:has-text("7d")').first();
      await expect(btn7dAfterBack).toBeVisible({ timeout: 5000 });

      const isActiveAfterBack = await btn7dAfterBack.evaluate((el) => {
        return el.classList.contains('btn-primary') || el.className.includes('btn-primary');
      });
      expect(isActiveAfterBack).toBe(true);
    });
  });

  test.describe('Tab Navigation', () => {
    test('active tab updates after HTMX navigation', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Overview tab should be active initially
      const overviewTab = page.getByRole('tab', { name: 'Overview' });
      const isOverviewActive = await overviewTab.evaluate((el) => {
        return el.classList.contains('tab-active');
      });
      expect(isOverviewActive).toBe(true);

      // Click on Team tab
      const teamTab = page.getByRole('tab', { name: 'Team' });
      await teamTab.click();
      await page.waitForURL(/\/team/);
      await waitForHtmxComplete(page);

      // Team tab should now be active
      const isTeamActive = await teamTab.evaluate((el) => {
        return el.classList.contains('tab-active');
      });
      expect(isTeamActive).toBe(true);

      // Overview should no longer be active
      const isOverviewStillActive = await overviewTab.evaluate((el) => {
        return el.classList.contains('tab-active');
      });
      expect(isOverviewStillActive).toBe(false);
    });
  });

  test.describe('Date Range State Persistence', () => {
    test('date range passes to PR list when clicking "All Pull Requests" link', async ({ page }) => {
      // Navigate to Delivery page with 90d date range
      await page.goto('/app/metrics/analytics/delivery/?days=90');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Verify we're on Delivery page with 90d
      expect(page.url()).toContain('days=90');

      // Click "All Pull Requests" link
      const prLink = page.getByRole('link', { name: 'All Pull Requests' });
      await prLink.click();
      await page.waitForURL(/pull-requests/);

      // PR list URL should include days=90
      expect(page.url()).toContain('pull-requests');
      expect(page.url()).toContain('days=90');
    });

    test('date range passes to PR list when clicking "AI-Assisted PRs" link', async ({ page }) => {
      // Navigate to Overview page with 7d date range
      await page.goto('/app/metrics/analytics/?days=7');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Click "AI-Assisted PRs" link
      const aiPrLink = page.getByRole('link', { name: 'AI-Assisted PRs' });
      await aiPrLink.click();
      await page.waitForURL(/pull-requests.*ai=yes/);

      // PR list URL should include days=7 and ai=yes
      expect(page.url()).toContain('pull-requests');
      expect(page.url()).toContain('ai=yes');
      expect(page.url()).toContain('days=7');
    });

    test('preset passes to PR list when using preset date range', async ({ page }) => {
      // Navigate to Delivery page with preset=12_months
      await page.goto('/app/metrics/analytics/delivery/?preset=12_months');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Click "All Pull Requests" link
      const prLink = page.getByRole('link', { name: 'All Pull Requests' });
      await prLink.click();
      await page.waitForURL(/pull-requests/);

      // PR list URL should include days parameter (12_months = 365 days)
      expect(page.url()).toContain('pull-requests');
      // Should pass either days=365 or the actual date range
      const url = page.url();
      const hasDateRange = url.includes('days=') || (url.includes('date_from=') && url.includes('date_to='));
      expect(hasDateRange).toBe(true);
    });
  });

  test.describe('Date Range Picker Visibility', () => {
    test('date range picker appears when navigating from Pull Requests to Delivery', async ({ page }) => {
      // Navigate to Pull Requests page (which doesn't show date range picker)
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Verify date range picker is NOT visible on Pull Requests page
      const timeRangeLabelBefore = page.locator('text=Time range:');
      await expect(timeRangeLabelBefore).not.toBeVisible();

      // Click on Delivery tab (HTMX navigation)
      const deliveryTab = page.getByRole('tab', { name: 'Delivery' });
      await deliveryTab.click();
      await page.waitForURL(/\/delivery/);
      await waitForHtmxComplete(page);

      // After HTMX navigation, date range picker SHOULD be visible
      const timeRangeLabel = page.locator('text=Time range:');
      await expect(timeRangeLabel).toBeVisible({ timeout: 5000 });

      // Also verify the time buttons are present
      const btn7d = page.locator('button:has-text("7d"), a:has-text("7d")').first();
      await expect(btn7d).toBeVisible();

      const btn30d = page.locator('button:has-text("30d"), a:has-text("30d")').first();
      await expect(btn30d).toBeVisible();
    });

    test('date range picker appears when navigating from Pull Requests to Overview', async ({ page }) => {
      // Navigate to Pull Requests page
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Click on Overview tab (HTMX navigation)
      const overviewTab = page.getByRole('tab', { name: 'Overview' });
      await overviewTab.click();
      await page.waitForURL(/\/analytics/);
      await waitForHtmxComplete(page);

      // Date range picker SHOULD be visible after navigation
      const timeRangeLabel = page.locator('text=Time range:');
      await expect(timeRangeLabel).toBeVisible({ timeout: 5000 });
    });

    test('date range picker stays visible when navigating between analytics pages', async ({ page }) => {
      // Start at Delivery page (has date range picker)
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpineStore(page);

      // Verify date range picker is visible
      const timeRangeLabelBefore = page.locator('text=Time range:');
      await expect(timeRangeLabelBefore).toBeVisible();

      // Navigate to Quality tab
      const qualityTab = page.getByRole('tab', { name: 'Quality' });
      await qualityTab.click();
      await page.waitForURL(/\/quality/);
      await waitForHtmxComplete(page);

      // Date range picker should still be visible
      const timeRangeLabelAfter = page.locator('text=Time range:');
      await expect(timeRangeLabelAfter).toBeVisible();
    });
  });
});
