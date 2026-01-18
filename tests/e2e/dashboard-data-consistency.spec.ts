import { test, expect, Page } from '@playwright/test';

/**
 * Dashboard Data Consistency Tests
 *
 * These tests verify that counts shown on the dashboard match
 * the actual data when clicking through to PR list pages.
 *
 * Run with: npx playwright test dashboard-data-consistency.spec.ts
 * Tag: @data-consistency
 */

/**
 * Wait for HTMX request to complete.
 */
async function waitForHtmxComplete(page: Page, timeout = 10000): Promise<void> {
  await page.waitForFunction(
    () => !document.body.classList.contains('htmx-request'),
    { timeout }
  );
}

/**
 * Extract number from text like "33 PRs" or "Total: 33"
 */
function extractNumber(text: string | null): number {
  if (!text) return 0;
  const match = text.match(/(\d+)/);
  return match ? parseInt(match[1], 10) : 0;
}

test.describe('Dashboard Data Consistency Tests @data-consistency', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('Review Distribution Data Consistency', () => {
    test('clicking reviewer shows matching PR count in list', async ({ page }) => {
      // Go to dashboard with 30d filter
      await page.goto('/app/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Wait for Review Distribution section to load
      const reviewDistSection = page.locator('#review-distribution-container');
      await expect(reviewDistSection).toBeVisible();
      await waitForHtmxComplete(page);

      // Find the first reviewer link with their PR count
      const reviewerLinks = reviewDistSection.locator('a[href*="reviewer="]');
      const firstReviewer = reviewerLinks.first();

      // Skip if no reviewers exist
      const reviewerCount = await reviewerLinks.count();
      if (reviewerCount === 0) {
        test.skip(true, 'No reviewers in Review Distribution section');
        return;
      }

      // Get reviewer name and PR count from dashboard
      const reviewerText = await firstReviewer.textContent();
      const prCountText = await firstReviewer.locator('.text-base-content\\/80').textContent();
      const dashboardCount = extractNumber(prCountText);

      // Click on the reviewer
      await firstReviewer.click();
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Verify we're on PR list page with reviewer filter
      await expect(page).toHaveURL(/\/metrics\/pull-requests\/\?/);
      await expect(page).toHaveURL(/reviewer=/);

      // Get the PR count from the list page
      // Look for "Showing X of Y" or just count the rows
      const prListTotal = page.locator('text=/Showing \\d+ of (\\d+)/').first();
      const totalRows = page.locator('tbody tr');

      let prListCount: number;
      const showingText = await prListTotal.textContent().catch((): null => null);
      if (showingText) {
        const match = showingText.match(/of (\d+)/);
        prListCount = match ? parseInt(match[1], 10) : await totalRows.count();
      } else {
        prListCount = await totalRows.count();
      }

      // The counts should match
      expect(prListCount).toBe(dashboardCount);
    });

    test('reviewer PR counts use unique PRs, not review submissions', async ({ page }) => {
      // This test verifies the fix for the review count mismatch bug
      await page.goto('/app/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const reviewDistSection = page.locator('#review-distribution-container');
      await expect(reviewDistSection).toBeVisible();
      await waitForHtmxComplete(page);

      // Check if there are any reviewers in the section
      const reviewerLinks = reviewDistSection.locator('a[href*="reviewer="]');
      const linkCount = await reviewerLinks.count();

      if (linkCount === 0) {
        test.skip(true, 'No reviewers in Review Distribution section');
        return;
      }

      // The label should say "PRs" not "reviews"
      // Look for text containing "PRs" in the section
      const sectionHtml = await reviewDistSection.innerHTML();
      const hasPRsLabel = sectionHtml.includes('PRs');
      const hasReviewsLabel = sectionHtml.toLowerCase().includes('reviews') && !sectionHtml.includes('reviewers');

      // Expect "PRs" labels, not "reviews" labels (fixed bug)
      expect(hasPRsLabel).toBe(true);
      expect(hasReviewsLabel).toBe(false);
    });
  });

  test.describe('Needs Attention Data Consistency', () => {
    test('clicking issue type shows matching PRs in list', async ({ page }) => {
      await page.goto('/app/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const needsAttentionSection = page.locator('#needs-attention-container');
      await expect(needsAttentionSection).toBeVisible();
      await waitForHtmxComplete(page);

      // Find issue type links in the legend (e.g., "Hotfix 5")
      const issueLinks = needsAttentionSection.locator('a[href*="issue_type="]');
      const linkCount = await issueLinks.count();

      if (linkCount === 0) {
        test.skip(true, 'No issues in Needs Attention section');
        return;
      }

      // Get the first issue type and its count
      const firstIssueLink = issueLinks.first();
      const issueText = await firstIssueLink.textContent();
      const dashboardCount = extractNumber(issueText);

      // Click on the issue type
      await firstIssueLink.click();
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Verify we're on PR list page with issue_type filter
      await expect(page).toHaveURL(/\/metrics\/pull-requests\/\?/);
      await expect(page).toHaveURL(/issue_type=/);

      // Get total from PR list
      const prListTotal = page.locator('text=/Showing \\d+ of (\\d+)/').first();
      const totalRows = page.locator('tbody tr');

      let prListCount: number;
      const showingText = await prListTotal.textContent().catch((): null => null);
      if (showingText) {
        const match = showingText.match(/of (\d+)/);
        prListCount = match ? parseInt(match[1], 10) : await totalRows.count();
      } else {
        prListCount = await totalRows.count();
      }

      // Counts should match
      expect(prListCount).toBe(dashboardCount);
    });

    test('total count matches sum of issue types', async ({ page }) => {
      await page.goto('/app/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const needsAttentionSection = page.locator('#needs-attention-container');
      await expect(needsAttentionSection).toBeVisible();
      await waitForHtmxComplete(page);

      // Get total count from the section
      const totalText = await needsAttentionSection.locator('text=/Total[:\\s]*\\d+/').textContent().catch((): null => null);
      if (!totalText) {
        test.skip(true, 'No total count in Needs Attention section');
        return;
      }
      const totalCount = extractNumber(totalText);

      // Get individual issue type counts
      const issueLinks = needsAttentionSection.locator('a[href*="issue_type="] .font-bold');
      const linkCount = await issueLinks.count();

      let sumOfIssues = 0;
      for (let i = 0; i < linkCount; i++) {
        const countText = await issueLinks.nth(i).textContent();
        sumOfIssues += extractNumber(countText);
      }

      // Total should equal sum of individual issue types
      expect(sumOfIssues).toBe(totalCount);
    });
  });

  test.describe('Top Contributors Data Consistency', () => {
    test('clicking contributor shows matching PR count in list', async ({ page }) => {
      await page.goto('/app/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const velocitySection = page.locator('#team-velocity-container');
      await expect(velocitySection).toBeVisible();
      await waitForHtmxComplete(page);

      // Find contributor links
      const contributorLinks = velocitySection.locator('a[href*="author="]');
      const linkCount = await contributorLinks.count();

      if (linkCount === 0) {
        test.skip(true, 'No contributors in Top Contributors section');
        return;
      }

      // Get the first contributor and their PR count
      const firstContributor = contributorLinks.first();
      const prCountText = await firstContributor.locator('text=/\\d+ PRs/').textContent();
      const dashboardCount = extractNumber(prCountText);

      // Click on the contributor
      await firstContributor.click();
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Verify we're on PR list page with author filter
      await expect(page).toHaveURL(/\/metrics\/pull-requests\/\?/);
      await expect(page).toHaveURL(/author=/);

      // Get total from PR list
      const prListTotal = page.locator('text=/Showing \\d+ of (\\d+)/').first();
      const totalRows = page.locator('tbody tr');

      let prListCount: number;
      const showingText = await prListTotal.textContent().catch((): null => null);
      if (showingText) {
        const match = showingText.match(/of (\d+)/);
        prListCount = match ? parseInt(match[1], 10) : await totalRows.count();
      } else {
        prListCount = await totalRows.count();
      }

      // Counts should match
      expect(prListCount).toBe(dashboardCount);
    });
  });

  test.describe('Key Metrics Data Consistency', () => {
    test('PRs Merged count matches total in PR list', async ({ page }) => {
      await page.goto('/app/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const keyMetricsSection = page.locator('#key-metrics-container');
      await expect(keyMetricsSection).toBeVisible();
      await waitForHtmxComplete(page);

      // Wait for PRs merged value to be loaded (not skeleton)
      const prsMergedValue = page.locator('#prs_merged-value');
      await expect(prsMergedValue).toBeVisible();
      const dashboardCountText = await prsMergedValue.textContent();
      const dashboardCount = extractNumber(dashboardCountText);

      // Navigate to PR list with same date filter
      await page.goto('/app/metrics/pull-requests/?days=30');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // Wait for the PR list to load
      await page.waitForSelector('tbody', { timeout: 10000 }).catch((): null => null);

      // Get total from PR list - look for "Total PRs" stat
      // The page shows a stat card with "Total PRs" label and a number value
      const totalPrsLabel = page.locator('text=Total PRs');
      await expect(totalPrsLabel).toBeVisible();

      // Get the value next to "Total PRs" label
      const totalPrsValue = totalPrsLabel.locator('..').locator('div').filter({ hasText: /^\d+$/ }).first();
      const prListCountText = await totalPrsValue.textContent();
      const prListCount = extractNumber(prListCountText);

      // If dashboard shows 0, skip comparison as there's no data
      if (dashboardCount === 0) {
        test.skip(true, 'No PRs merged in this time period');
        return;
      }

      // Counts should match
      expect(prListCount).toBe(dashboardCount);
    });
  });

  test.describe('Time Range Consistency', () => {
    test('changing time range updates all sections consistently', async ({ page }) => {
      // Test 7-day filter
      await page.goto('/app/?days=7');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      // All HTMX containers should reload with new data
      await expect(page.locator('#key-metrics-container')).toBeVisible();
      await expect(page.locator('#needs-attention-container')).toBeVisible();
      await expect(page.locator('#ai-impact-container')).toBeVisible();
      await expect(page.locator('#team-velocity-container')).toBeVisible();
      await expect(page.locator('#review-distribution-container')).toBeVisible();

      // Verify 7d is active
      await expect(page.getByRole('link', { name: '7d' })).toHaveClass(/btn-primary|btn-active/);

      // Click 90d and verify
      await page.getByRole('link', { name: '90d' }).click();
      await expect(page).toHaveURL(/\?days=90/);
      await waitForHtmxComplete(page);

      // 90d should now be active
      await expect(page.getByRole('link', { name: '90d' })).toHaveClass(/btn-primary|btn-active/);
    });

    test('click-through links preserve time range filter', async ({ page }) => {
      // Use 90-day filter
      await page.goto('/app/?days=90');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page);

      const reviewDistSection = page.locator('#review-distribution-container');
      await expect(reviewDistSection).toBeVisible();
      await waitForHtmxComplete(page);

      // Find a reviewer link
      const reviewerLinks = reviewDistSection.locator('a[href*="reviewer="]');
      const linkCount = await reviewerLinks.count();

      if (linkCount === 0) {
        test.skip(true, 'No reviewers to click');
        return;
      }

      // Click on first reviewer
      await reviewerLinks.first().click();
      await page.waitForLoadState('domcontentloaded');

      // URL should have days=90 preserved
      await expect(page).toHaveURL(/days=90/);
    });
  });
});
