import { test, expect, ConsoleMessage } from '@playwright/test';
import { waitForHtmxComplete } from './helpers';
import { loginAs } from './fixtures/test-users';

/**
 * PR List Accordion & UX Tests
 * Run with: npx playwright test pr-list-accordion.spec.ts
 * Tag: @pr-list-accordion
 *
 * Tests for:
 * - No Alpine.js console errors
 * - Accordion behavior (only one PR expanded at a time)
 * - Visual indicators on expanded rows
 */

test.describe('PR List Accordion Tests @pr-list-accordion', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Console Errors', () => {
    test('PR list page has no Alpine expression errors', async ({ page }) => {
      const consoleErrors: ConsoleMessage[] = [];

      // Collect console errors
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg);
        }
      });

      await page.goto('/app/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Filter for Alpine-specific errors
      const alpineErrors = consoleErrors.filter(
        (msg) =>
          msg.text().includes('Alpine') ||
          msg.text().includes('Unexpected token') ||
          msg.text().includes('expression')
      );

      // Should have ZERO Alpine expression errors
      expect(alpineErrors.length).toBe(0);

      // If there are errors, log them for debugging
      if (alpineErrors.length > 0) {
        console.log('Alpine errors found:');
        alpineErrors.forEach((err) => console.log(`  - ${err.text()}`));
      }
    });

    test('PR list page has no JavaScript errors', async ({ page }) => {
      const jsErrors: string[] = [];

      page.on('pageerror', (error) => {
        jsErrors.push(error.message);
      });

      await page.goto('/app/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should have no JS errors
      expect(jsErrors.length).toBe(0);
    });
  });

  test.describe('Accordion Behavior', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);
    });

    test('clicking a PR row expands its details', async ({ page }) => {
      // Find clickable PR rows (data rows, not header or empty state)
      const prRows = page.locator('table tbody tr').filter({
        has: page.locator('a[href*="github.com"], a[target="_blank"]'),
      });

      const rowCount = await prRows.count();
      test.skip(rowCount === 0, 'No PR rows available for testing');

      // Click first PR row
      await prRows.first().click();

      // Wait for expansion animation
      await page.waitForTimeout(300);

      // Should show expanded content (check for expanded row with colspan)
      // The expanded row contains a td with colspan attribute
      const expandedContent = page.locator('tr td[colspan="11"]');

      await expect(expandedContent.first()).toBeVisible();
    });

    test('only one PR can be expanded at a time (accordion)', async ({ page }) => {
      // Find clickable PR rows
      const prRows = page.locator('table tbody tr').filter({
        has: page.locator('a[href*="github.com"], a[target="_blank"]'),
      });

      const rowCount = await prRows.count();
      test.skip(rowCount < 2, 'Need at least 2 PR rows for accordion test');

      // Expand first PR row
      await prRows.first().click();
      await page.waitForTimeout(300);

      // Verify first row is expanded
      let expandedRows = page.locator('tr[x-show*="expanded"]:visible, tr:has(td[colspan]):visible');
      await expect(expandedRows).toHaveCount(1);

      // Now click second PR row
      await prRows.nth(1).click();
      await page.waitForTimeout(300);

      // Only ONE row should be expanded (accordion behavior)
      // Count visible expanded content rows
      const visibleExpandedContent = page.locator(
        'tr:has(td[colspan]) >> visible=true'
      );

      // Should still be exactly 1 expanded row
      const expandedCount = await visibleExpandedContent.count();
      expect(expandedCount).toBe(1);
    });

    test('clicking expanded row collapses it', async ({ page }) => {
      // Find clickable PR rows
      const prRows = page.locator('table tbody tr').filter({
        has: page.locator('a[href*="github.com"], a[target="_blank"]'),
      });

      const rowCount = await prRows.count();
      test.skip(rowCount === 0, 'No PR rows available for testing');

      // Click to expand
      await prRows.first().click();
      await page.waitForTimeout(300);

      // Verify expanded - look for the colspan=11 cell
      const expandedContent = page.locator('tr td[colspan="11"]');
      await expect(expandedContent.first()).toBeVisible();

      // Click again to collapse
      await prRows.first().click();
      await page.waitForTimeout(300);

      // Should be collapsed (not visible)
      await expect(expandedContent.first()).not.toBeVisible();
    });
  });

  test.describe('Visual Indicators', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);
    });

    test('expanded row has visual highlight (left border)', async ({ page }) => {
      // Find clickable PR rows
      const prRows = page.locator('table tbody tr').filter({
        has: page.locator('a[href*="github.com"], a[target="_blank"]'),
      });

      const rowCount = await prRows.count();
      test.skip(rowCount === 0, 'No PR rows available for testing');

      // Click to expand
      await prRows.first().click();
      await page.waitForTimeout(300);

      // The expanded row should have primary-colored left border
      // Check for border-l-primary class
      const rowWithBorder = page.locator('tr.border-l-primary, tr.border-l-4');

      await expect(rowWithBorder.first()).toBeVisible();
    });

    test('expanded row has stronger background', async ({ page }) => {
      // Find clickable PR rows
      const prRows = page.locator('table tbody tr').filter({
        has: page.locator('a[href*="github.com"], a[target="_blank"]'),
      });

      const rowCount = await prRows.count();
      test.skip(rowCount === 0, 'No PR rows available for testing');

      // Click to expand
      await prRows.first().click();
      await page.waitForTimeout(300);

      // Check for bg-base-200/50 class (or stronger background)
      const rowWithBg = page.locator('tr').filter({
        has: page.locator('td[colspan]'),
      });

      // Verify expanded content row has background styling
      const classes = await rowWithBg.first().getAttribute('class');
      expect(classes).toMatch(/bg-base-200/);
    });

    test('chevron rotates and changes color when expanded', async ({ page }) => {
      // Find clickable PR rows
      const prRows = page.locator('table tbody tr').filter({
        has: page.locator('a[href*="github.com"], a[target="_blank"]'),
      });

      const rowCount = await prRows.count();
      test.skip(rowCount === 0, 'No PR rows available for testing');

      // Find chevron button in first row - it has transition-all class (note icon has -ml-1)
      const chevron = prRows.first().locator('button.transition-all:has(svg)').first();

      // Before click - should not have rotate or primary classes
      let chevronClasses = await chevron.getAttribute('class');
      expect(chevronClasses).not.toContain('rotate-90');

      // Click to expand
      await prRows.first().click();
      await page.waitForTimeout(300);

      // After click - chevron should have rotate-90 and text-primary classes
      chevronClasses = await chevron.getAttribute('class');
      expect(chevronClasses).toContain('rotate-90');
      expect(chevronClasses).toContain('text-primary');
    });
  });

  test.describe('Layout Spacing', () => {
    test('page has reduced margins for more content width', async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Check the section element has reduced margin
      const section = page.locator('section.section');

      // Get computed styles
      const marginStyles = await section.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          marginTop: styles.marginTop,
          marginRight: styles.marginRight,
          marginBottom: styles.marginBottom,
          marginLeft: styles.marginLeft,
        };
      });

      // Margin should be 8px (m-2) instead of 16px (m-4)
      expect(parseInt(marginStyles.marginTop)).toBeLessThanOrEqual(8);
      expect(parseInt(marginStyles.marginLeft)).toBeLessThanOrEqual(8);
    });

    test('app-card has reduced padding', async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Check the app-card element
      const appCard = page.locator('.app-card').first();

      // Get computed padding on large screens
      const paddingStyles = await appCard.evaluate((el) => {
        const styles = window.getComputedStyle(el);
        return {
          paddingTop: styles.paddingTop,
          paddingRight: styles.paddingRight,
          paddingBottom: styles.paddingBottom,
          paddingLeft: styles.paddingLeft,
        };
      });

      // Padding should be 20px (p-5) instead of 32px (p-8) on large screens
      // Or 12px (p-3) on mobile
      expect(parseInt(paddingStyles.paddingTop)).toBeLessThanOrEqual(20);
      expect(parseInt(paddingStyles.paddingLeft)).toBeLessThanOrEqual(20);
    });
  });
});
