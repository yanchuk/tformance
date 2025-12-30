import { test, expect, Page } from '@playwright/test';

/**
 * AI Feedback E2E Tests
 * Run with: npx playwright test feedback.spec.ts
 * Tag: @feedback
 *
 * Tests for the AI Code Feedback feature allowing users to report
 * issues with AI-generated code.
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

/**
 * Wait for modal dialog to be visible.
 */
async function waitForModal(page: Page, timeout = 5000): Promise<void> {
  await page.locator('dialog[open]').or(page.locator('.modal.modal-open')).waitFor({ state: 'visible', timeout });
}

/**
 * Wait for modal dialog to close.
 */
async function waitForModalClose(page: Page, timeout = 5000): Promise<void> {
  await page.locator('dialog[open]').or(page.locator('.modal.modal-open')).waitFor({ state: 'hidden', timeout });
}

test.describe('AI Feedback Tests @feedback', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('Feedback Dashboard', () => {
    test('feedback dashboard is accessible', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Should have page title
      await expect(page.getByRole('heading', { name: 'AI Feedback' })).toBeVisible();
    });

    test('dashboard shows stats cards', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Should have stat cards with Total, Open Issues, and Resolved
      await expect(page.locator('.stat-title').filter({ hasText: 'Total Feedback' })).toBeVisible();
      await expect(page.locator('.stat-title').filter({ hasText: 'Open Issues' })).toBeVisible();
      await expect(page.locator('.stat-title').filter({ hasText: 'Resolved' })).toBeVisible();
    });

    test('report issue button is visible', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Should have report issue button
      await expect(page.getByRole('button', { name: /Report Issue/i })).toBeVisible();
    });

    test('filter dropdowns are visible', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Category and status filter dropdowns should be visible
      const categoryFilter = page.locator('select[name="category"]');
      const statusFilter = page.locator('select[name="status"]');

      await expect(categoryFilter).toBeVisible();
      await expect(statusFilter).toBeVisible();
    });

    test('category filter has all options', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      const categoryFilter = page.locator('select[name="category"]');

      // Verify key category options exist
      await expect(categoryFilter.locator('option[value="wrong_code"]')).toHaveCount(1);
      await expect(categoryFilter.locator('option[value="security"]')).toHaveCount(1);
    });
  });

  test.describe('Create Feedback Modal', () => {
    test('report issue button opens modal', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Click report issue button
      await page.getByRole('button', { name: /Report Issue/i }).click();

      // Wait for modal to appear
      await waitForModal(page);

      // Modal should be visible with form
      await expect(page.getByRole('heading', { name: 'Report AI Issue' })).toBeVisible();
    });

    test('modal has required form fields', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Open modal
      await page.getByRole('button', { name: /Report Issue/i }).click();
      await waitForModal(page);

      // Check for form elements
      await expect(page.getByText('Category')).toBeVisible();
      await expect(page.getByText('Description')).toBeVisible();
    });

    test('cancel button closes modal', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Open modal
      await page.getByRole('button', { name: /Report Issue/i }).click();
      await waitForModal(page);

      // Click cancel
      await page.getByRole('button', { name: 'Cancel' }).click();
      await waitForModalClose(page);

      // Modal should be closed
      await expect(page.getByRole('heading', { name: 'Report AI Issue' })).not.toBeVisible();
    });

    test('submit feedback with valid data', async ({ page }) => {
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Open modal
      await page.getByRole('button', { name: /Report Issue/i }).click();
      await waitForModal(page);

      // Fill form - the modal should be visible
      await expect(page.getByRole('heading', { name: 'Report AI Issue' })).toBeVisible();

      // Select category in the modal dialog
      const modal = page.locator('dialog');
      await modal.locator('select[name="category"]').selectOption('wrong_code');
      await modal.locator('textarea[name="description"]').fill('Test feedback submission');

      // Submit
      await modal.getByRole('button', { name: 'Submit' }).click();

      // Wait for modal to close (indicating success)
      await waitForModalClose(page, 10000);

      // Should be back on the dashboard
      const isOnDashboard = page.url().includes('/feedback/');
      expect(isOnDashboard).toBeTruthy();
    });
  });

  test.describe('CTO Dashboard Integration', () => {
    test('AI Feedback card appears on CTO dashboard', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Should have AI Code Feedback heading
      await expect(page.getByRole('heading', { name: 'AI Code Feedback' })).toBeVisible();
    });

    test('feedback summary loads via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Should show feedback container with content
      const feedbackContainer = page.locator('#ai-feedback-container');
      await expect(feedbackContainer).toBeVisible({ timeout: 10000 });

      // Should have open/resolved stats
      await expect(feedbackContainer.getByText('Open Issues')).toBeVisible();
      await expect(feedbackContainer.getByText('Resolved')).toBeVisible();
    });

    test('View All Feedback link works', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Click View All Feedback link
      await page.getByRole('link', { name: 'View All Feedback' }).click();

      // Should navigate to feedback dashboard
      await expect(page).toHaveURL(/\/app\/feedback\//);
    });
  });

  test.describe('PR Table Integration', () => {
    test('recent PRs table has report button column', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check if any PRs are in the table (may not have data)
      const prRows = page.locator('table tbody tr');
      const count = await prRows.count();

      if (count > 0) {
        // First row should have the report button
        const reportButton = prRows.first().locator('button[title="Report AI Issue"]');
        await expect(reportButton).toBeVisible();
      }
    });

    test('clicking report button on PR opens modal with PR context', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Check if any PRs are in the table
      const prRows = page.locator('table tbody tr');
      const count = await prRows.count();

      if (count > 0) {
        // Click report button on first PR
        const reportButton = prRows.first().locator('button[title="Report AI Issue"]');
        await reportButton.click();
        await waitForModal(page);

        // Modal should open
        await expect(page.getByRole('heading', { name: 'Report AI Issue' })).toBeVisible();

        // Should indicate PR context
        await expect(page.getByText('Reporting issue for selected PR')).toBeVisible();
      }
    });
  });

  test.describe('Feedback Detail', () => {
    test('clicking View link shows detail page', async ({ page }) => {
      // First create a feedback item
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Open modal and submit
      await page.getByRole('button', { name: /Report Issue/i }).click();
      await waitForModal(page);

      const modal = page.locator('dialog');
      await modal.locator('select[name="category"]').selectOption('security');
      await modal.locator('textarea[name="description"]').fill('Security test case for detail');
      await modal.getByRole('button', { name: 'Submit' }).click();
      await waitForModalClose(page, 10000);

      // Reload dashboard
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Click on the View link for a feedback card
      const viewLink = page.getByRole('link', { name: 'View' }).first();
      if (await viewLink.isVisible()) {
        await viewLink.click();
        await page.waitForLoadState('domcontentloaded');

        // Should be on detail page
        expect(page.url()).toMatch(/\/app\/feedback\/\d+\//);
      }
    });
  });

  test.describe('Resolve Feedback', () => {
    test('resolve button marks feedback as resolved', async ({ page }) => {
      // First create a feedback item
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');

      // Open modal and submit
      await page.getByRole('button', { name: /Report Issue/i }).click();
      await waitForModal(page);

      const modal = page.locator('dialog');
      await modal.locator('select[name="category"]').selectOption('style_issue');
      await modal.locator('textarea[name="description"]').fill('Style issue to resolve');
      await modal.getByRole('button', { name: 'Submit' }).click();
      await waitForModalClose(page, 10000);

      // Reload dashboard
      await page.goto('/app/feedback/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Find a resolve button (only visible on open feedback)
      const resolveButton = page.getByRole('button', { name: 'Resolve' }).first();
      if (await resolveButton.isVisible()) {
        await resolveButton.click();
        await waitForHtmxComplete(page);

        // Card should now show "Resolved" status badge
        await expect(page.locator('.badge-success').first()).toBeVisible();
      }
    });
  });
});
