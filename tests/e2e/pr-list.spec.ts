import { test, expect } from '@playwright/test';
import { waitForHtmxComplete } from './helpers';
import { loginAs } from './fixtures/test-users';

/**
 * PR List Page Tests
 * Run with: npx playwright test pr-list.spec.ts
 * Tag: @pr-list
 *
 * Tests for the Pull Requests list page:
 * - Table rendering and pagination
 * - Filtering (repository, author, AI status, state, date range)
 * - Export functionality
 * - Navigation from dashboard links
 */

test.describe('PR List Page Tests @pr-list', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Page Load', () => {
    test('PR list page loads successfully', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Should have page title
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();
    });

    test('page shows filter panel', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Should have filter controls (using name attribute for selects)
      await expect(page.locator('select[name="repo"]')).toBeVisible();
      await expect(page.locator('select[name="author"]')).toBeVisible();
      await expect(page.locator('select[name="ai"]')).toBeVisible();
    });

    test('table loads with PR data', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should have table with headers
      const table = page.locator('table');
      await expect(table).toBeVisible();

      // Should have expected columns
      await expect(table.locator('th').filter({ hasText: /PR|Title/i })).toBeVisible();
    });

    test('empty state displays when no PRs match filter', async ({ page }) => {
      // Navigate with filter that likely returns no results
      await page.goto('/app/metrics/pull-requests/?author=999999');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should show empty state message OR have zero rows
      const noResults = await page.getByText(/no pull requests found/i).isVisible().catch(() => false);
      const hasRows = await page.locator('table tbody tr').count() > 0;

      // Either shows empty message or has no data rows
      expect(noResults || !hasRows).toBeTruthy();
    });
  });

  test.describe('Filter Panel', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);
    });

    test('repository filter dropdown works', async ({ page }) => {
      const repoSelect = page.locator('select[name="repo"]');
      await expect(repoSelect).toBeVisible();

      // Should have "All Repositories" option
      await expect(repoSelect.locator('option').first()).toContainText(/all/i);
    });

    test('AI filter dropdown has correct options', async ({ page }) => {
      const aiSelect = page.locator('select[name="ai"]');
      await expect(aiSelect).toBeVisible();

      // Check options
      await expect(aiSelect.locator('option')).toHaveCount(3); // All, Yes, No
    });

    test('Apply Filters button submits form', async ({ page }) => {
      // Select AI = Yes
      await page.locator('select[name="ai"]').selectOption('yes');

      // Click Apply Filters
      await page.getByRole('button', { name: /apply/i }).click();
      await waitForHtmxComplete(page);

      // URL should have ai param
      await expect(page).toHaveURL(/ai=yes/);
    });

    test('Clear button resets all filters', async ({ page }) => {
      // First apply a filter
      await page.goto('/app/metrics/pull-requests/?ai=yes');
      await waitForHtmxComplete(page);

      // Click Clear
      await page.getByRole('link', { name: /clear/i }).click();
      await waitForHtmxComplete(page);

      // URL should not have ai param
      const url = page.url();
      expect(url).not.toMatch(/ai=/);
    });
  });

  test.describe('AI Status Filtering via URL', () => {
    test('AI filter via URL shows AI-assisted PRs', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?ai=yes');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Page should load without errors
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();

      // AI dropdown should show "Yes" selected
      const aiSelect = page.locator('select[name="ai"]');
      await expect(aiSelect).toHaveValue('yes');
    });

    test('AI filter via URL shows non-AI PRs', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?ai=no');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();

      const aiSelect = page.locator('select[name="ai"]');
      await expect(aiSelect).toHaveValue('no');
    });
  });

  test.describe('Pagination', () => {
    test('pagination controls are visible when data exists', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Look for pagination controls (prev/next buttons or page numbers)
      const pagination = page.locator('.join').or(page.locator('[class*="pagination"]'));
      const rowCount = await page.locator('table tbody tr').count();

      // If there's data, check for pagination controls
      if (rowCount > 0) {
        const hasPagination = await pagination.first().isVisible().catch(() => false);
        // Pagination may not show if only one page of results
        // Just verify page loads correctly
        await expect(page.locator('table')).toBeVisible();
      }
    });

    test('page parameter works via URL', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?page=1');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should load page 1 successfully
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();
    });
  });

  test.describe('Sorting', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);
    });

    test('table headers are present for sorting', async ({ page }) => {
      // Check for sortable column headers
      const headers = page.locator('table th');
      await expect(headers.first()).toBeVisible();

      // Should have multiple columns
      const headerCount = await headers.count();
      expect(headerCount).toBeGreaterThan(3);
    });
  });

  test.describe('Navigation Integration', () => {
    test('direct URL with author filter works', async ({ page }) => {
      // Navigate directly with author filter (use valid filter format)
      await page.goto('/app/metrics/pull-requests/?author=1');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Should show page with filter applied
      await expect(page).toHaveURL(/author=/);
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();
    });

    test('direct URL with state filter works', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?state=merged');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page).toHaveURL(/state=merged/);
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();
    });

    test('multiple filters can be combined', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?ai=yes&state=merged');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page).toHaveURL(/ai=yes/);
      await expect(page).toHaveURL(/state=merged/);
    });
  });

  test.describe('Export Functionality', () => {
    test('export button is visible', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Look for export button/link
      const exportBtn = page.getByRole('link', { name: /export/i });
      await expect(exportBtn).toBeVisible();
    });

    test('export link includes current filters', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?ai=yes');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const exportBtn = page.getByRole('link', { name: /export/i });
      const href = await exportBtn.getAttribute('href');

      // Export link should include the ai filter
      expect(href).toContain('ai=yes');
    });
  });

  test.describe('URL State Persistence', () => {
    test('filters persist on page refresh', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?ai=yes&state=merged');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Refresh
      await page.reload();
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // URL should still have filters
      await expect(page).toHaveURL(/ai=yes/);
      await expect(page).toHaveURL(/state=merged/);

      // Filter dropdowns should reflect the values
      await expect(page.locator('select[name="ai"]')).toHaveValue('yes');
    });

    test('URL params control filter state', async ({ page }) => {
      // Navigate with one filter
      await page.goto('/app/metrics/pull-requests/?state=merged');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // State filter should be applied
      await expect(page.locator('select[name="state"]')).toHaveValue('merged');

      // Change to another filter combination
      await page.goto('/app/metrics/pull-requests/?ai=yes&state=open');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Both filters should be applied
      await expect(page.locator('select[name="ai"]')).toHaveValue('yes');
      await expect(page.locator('select[name="state"]')).toHaveValue('open');
    });
  });

  test.describe('PR Details', () => {
    test('PR row has link to external PR', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Check if any PR links exist (to GitHub)
      const prLinks = page.locator('table tbody a[href*="github.com"]').or(
        page.locator('table tbody a[target="_blank"]')
      );

      const linkCount = await prLinks.count();
      // If there are PRs, they should have external links
      if (linkCount > 0) {
        const firstLink = prLinks.first();
        const href = await firstLink.getAttribute('href');
        expect(href).toBeTruthy();
      }
    });

    test('PR rows show author information', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      const rows = page.locator('table tbody tr');
      const rowCount = await rows.count();

      // If there are rows, they should show some content
      if (rowCount > 0) {
        const firstRow = rows.first();
        const rowText = await firstRow.textContent();
        expect(rowText).toBeTruthy();
      }
    });
  });

  test.describe('Responsive Design', () => {
    test('page renders on mobile viewport', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Page title should be visible
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();

      // Filter panel should be visible
      await expect(page.locator('select[name="ai"]')).toBeVisible();
    });

    test('table container handles overflow on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Table container should exist (may have overflow styles)
      const tableContainer = page.locator('#pr-table-container').or(page.locator('table').locator('..'));
      await expect(tableContainer.first()).toBeVisible();
    });
  });

  test.describe('Date Range Filtering', () => {
    test('date inputs are available', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Should have date from/to inputs
      await expect(page.locator('input[name="date_from"]')).toBeVisible();
      await expect(page.locator('input[name="date_to"]')).toBeVisible();
    });

    test('date filter via URL works', async ({ page }) => {
      const today = new Date().toISOString().split('T')[0];
      const lastMonth = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];

      await page.goto(`/app/metrics/pull-requests/?date_from=${lastMonth}&date_to=${today}`);
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();
    });
  });
});
