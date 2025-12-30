/**
 * Metric Toggle Tests
 *
 * Tests for the metric selection checkboxes on the Trends & Comparison page.
 * Verifies that toggle state is properly maintained after multiple interactions.
 */
import { test, expect, Page } from '@playwright/test';

test.use({ browserName: 'chromium' });

/**
 * Wait for Alpine.js to be fully initialized.
 */
async function waitForAlpine(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => {
      const Alpine = (window as any).Alpine;
      return Alpine && Alpine.version;
    },
    { timeout }
  );
}

/**
 * Wait for HTMX swap to complete.
 */
async function waitForHtmxSwap(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

test.describe('Metric Toggle on Trends Page', () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(15000);

    // Login
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.waitForURL(/\/app/, { timeout: 5000 });
  });

  test.describe('Checkbox Visual State', () => {
    test('metric checkbox shows checked state after selection', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      // Find the Review Time label and checkbox
      const reviewTimeLabel = page.locator('label').filter({ hasText: 'Review Time' });
      const reviewTimeCheckbox = reviewTimeLabel.locator('input[type="checkbox"]');

      // Should start unchecked
      await expect(reviewTimeCheckbox).not.toBeChecked();

      // Click label to select (handler is on label)
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);

      // Should now be checked
      await expect(reviewTimeCheckbox).toBeChecked();
    });

    test('metric checkbox shows unchecked state after deselection', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/?metrics=cycle_time,review_time');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      // Find the Review Time label and checkbox
      const reviewTimeLabel = page.locator('label').filter({ hasText: 'Review Time' });
      const reviewTimeCheckbox = reviewTimeLabel.locator('input[type="checkbox"]');

      // Should start checked
      await expect(reviewTimeCheckbox).toBeChecked();

      // Click label to deselect (handler is on label)
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);

      // Should now be unchecked
      await expect(reviewTimeCheckbox).not.toBeChecked();
    });

    test('metric checkbox shows checked state after re-selection (the bug)', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      // Find the Review Time label and checkbox
      const reviewTimeLabel = page.locator('label').filter({ hasText: 'Review Time' });
      const reviewTimeCheckbox = reviewTimeLabel.locator('input[type="checkbox"]');

      // Step 1: Should start unchecked
      await expect(reviewTimeCheckbox).not.toBeChecked();

      // Step 2: Click label to select (handler is on label)
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);
      await expect(reviewTimeCheckbox).toBeChecked();

      // Step 3: Click label to deselect
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);
      await expect(reviewTimeCheckbox).not.toBeChecked();

      // Step 4: Click label to re-select - THIS WAS THE BUG
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);

      // This assertion should pass now
      await expect(reviewTimeCheckbox).toBeChecked();
    });

    test('multiple toggle cycles maintain correct state', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      const reviewTimeLabel = page.locator('label').filter({ hasText: 'Review Time' });
      const reviewTimeCheckbox = reviewTimeLabel.locator('input[type="checkbox"]');

      // Perform 3 complete toggle cycles
      for (let i = 0; i < 3; i++) {
        // Select (click label)
        await reviewTimeLabel.click();
        await waitForHtmxSwap(page);
        await expect(reviewTimeCheckbox).toBeChecked({ timeout: 2000 });

        // Deselect (click label)
        await reviewTimeLabel.click();
        await waitForHtmxSwap(page);
        await expect(reviewTimeCheckbox).not.toBeChecked({ timeout: 2000 });
      }

      // Final select should work
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);
      await expect(reviewTimeCheckbox).toBeChecked();
    });
  });

  test.describe('Selection Constraints', () => {
    test('at least one metric must remain selected', async ({ page }) => {
      // Start with only cycle_time selected
      await page.goto('/app/metrics/analytics/trends/?metrics=cycle_time');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      const cycleTimeLabel = page.locator('label').filter({ hasText: 'Cycle Time' });
      const cycleTimeCheckbox = cycleTimeLabel.locator('input[type="checkbox"]');

      // Should be checked
      await expect(cycleTimeCheckbox).toBeChecked();

      // Try to deselect the only metric (click label) - should not uncheck
      await cycleTimeLabel.click();
      await waitForAlpine(page); // Wait for Alpine to process click

      // Should still be checked (can't deselect the last metric)
      await expect(cycleTimeCheckbox).toBeChecked();
    });

    test('maximum 3 metrics can be selected', async ({ page }) => {
      // Start with 3 metrics already selected (cycle_time, review_time, pr_count)
      await page.goto('/app/metrics/analytics/trends/?metrics=cycle_time,review_time,pr_count');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      // Find the 4th metric label and checkbox (AI Adoption)
      const aiAdoptionLabel = page.locator('label').filter({ hasText: 'AI Adoption' });
      const aiAdoptionCheckbox = aiAdoptionLabel.locator('input[type="checkbox"]');

      // Should be unchecked (not in URL - only 3 metrics selected)
      await expect(aiAdoptionCheckbox).not.toBeChecked();

      // Try to select a 4th metric (click label) - should not check
      await aiAdoptionLabel.click();
      await waitForAlpine(page); // Wait for Alpine to process click

      // Should still be unchecked (max 3 reached)
      await expect(aiAdoptionCheckbox).not.toBeChecked();

      // Verify "(max 3)" text is visible
      await expect(page.locator('text=(max 3)')).toBeVisible();
    });
  });

  test.describe('URL and Chart Sync', () => {
    test('URL updates when metric is toggled', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      // Initial URL should have default metric
      expect(page.url()).not.toContain('review_time');

      // Select Review Time (click label)
      const reviewTimeLabel = page.locator('label').filter({ hasText: 'Review Time' });
      await reviewTimeLabel.click();
      await waitForHtmxSwap(page);

      // URL should now include review_time
      await page.waitForURL(/metrics=.*review_time/, { timeout: 5000 });
    });

    test('chart updates when metric is toggled', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await waitForAlpine(page);

      // Wait for initial chart to load
      await page.waitForSelector('#wide-chart-container canvas', { timeout: 10000 });

      // Get initial chart state (number of datasets or similar)
      const initialChartExists = await page.locator('#wide-chart-container canvas').isVisible();
      expect(initialChartExists).toBe(true);

      // Toggle a metric (click label)
      const reviewTimeLabel = page.locator('label').filter({ hasText: 'Review Time' });
      await reviewTimeLabel.click();

      // Wait for chart to update (HTMX swap)
      await waitForHtmxSwap(page);
      await page.waitForSelector('#wide-chart-container canvas', { timeout: 10000 });

      // Chart should still be visible (indicating successful update)
      const updatedChartExists = await page.locator('#wide-chart-container canvas').isVisible();
      expect(updatedChartExists).toBe(true);
    });
  });
});
