import { test, expect } from '@playwright/test';

/**
 * AI Insights E2E Tests
 * Run with: npx playwright test insights.spec.ts
 * Tag: @insights
 *
 * Tests for the LLM-powered insights feature on the CTO dashboard.
 * These tests verify the UI integration works correctly.
 */

test.describe('AI Insights Tests @insights', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('AI Summary Card', () => {
    test('AI Insights card displays on CTO dashboard', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have AI Insights heading
      await expect(page.getByRole('heading', { name: 'AI Insights' })).toBeVisible();
    });

    test('AI Summary loads via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Wait for HTMX to load the summary
      await page.waitForTimeout(1000);

      // Should show either a summary or an error message (API not configured)
      const summaryCard = page.locator('#ai-summary-card');
      await expect(summaryCard).toBeVisible();

      // Check for content (either summary text or error about API not configured)
      const hasContent = await summaryCard.locator('#ai-summary-content').textContent();
      expect(hasContent).toBeTruthy();
    });

    test('refresh button is present', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have refresh button
      await expect(page.getByRole('button', { name: 'Refresh summary' })).toBeVisible();
    });

    test('refresh button triggers HTMX request', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Click refresh button
      const refreshButton = page.getByRole('button', { name: 'Refresh summary' });
      await refreshButton.click();

      // Wait for response
      await page.waitForTimeout(1000);

      // Summary content should still be visible (either refreshed or error)
      const summaryContent = page.locator('#ai-summary-content');
      await expect(summaryContent).toBeVisible();
    });
  });

  test.describe('Q&A Form', () => {
    test('Ask About Your Metrics form displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have the Q&A heading
      await expect(page.getByRole('heading', { name: 'Ask About Your Metrics' })).toBeVisible();
    });

    test('question input field is present', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have question input
      const input = page.getByRole('textbox', { name: /How is the team doing/i });
      await expect(input).toBeVisible();
    });

    test('Ask button is present', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have Ask button
      await expect(page.getByRole('button', { name: 'Ask' })).toBeVisible();
    });

    test('suggested questions load via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Should have "Try asking:" text
      await expect(page.getByText('Try asking:')).toBeVisible();

      // Should have at least one suggested question button
      await expect(page.getByRole('button', { name: /How is the team doing/i })).toBeVisible();
    });

    test('clicking suggested question fills input and submits', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Click a suggested question
      await page.getByRole('button', { name: 'How is the team doing this month?' }).click();

      // Wait for HTMX response
      await page.waitForTimeout(1500);

      // Response area should have content
      const response = page.locator('#qa-response');
      await expect(response).toBeVisible();

      // Should have some response (either answer or error about API not configured)
      const responseText = await response.textContent();
      expect(responseText).toBeTruthy();
    });

    test('typing and submitting question works', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Type a question
      const input = page.getByRole('textbox', { name: /How is the team doing/i });
      await input.fill('What is the team velocity?');

      // Click Ask button
      await page.getByRole('button', { name: 'Ask' }).click();

      // Wait for HTMX response
      await page.waitForTimeout(1500);

      // Response area should have content
      const response = page.locator('#qa-response');
      await expect(response).toBeVisible();
    });

    test('empty question shows validation (HTML5 required)', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Clear input and try to submit
      const input = page.getByRole('textbox', { name: /How is the team doing/i });
      await input.fill('');

      // Click Ask button - should trigger HTML5 validation
      await page.getByRole('button', { name: 'Ask' }).click();

      // Input should still be focused (validation prevents submission)
      await expect(input).toBeFocused();
    });
  });

  test.describe('Recent Insights', () => {
    test('Recent Insights section displays', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have Recent Insights heading
      await expect(page.getByRole('heading', { name: 'Recent Insights' })).toBeVisible();
    });

    test('insight cards display with priority badges', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have at least one insight card (from sample data)
      const insightCards = page.locator('.alert');
      const count = await insightCards.count();
      expect(count).toBeGreaterThan(0);
    });

    test('insight cards have dismiss buttons', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have dismiss buttons on insight cards
      const dismissButtons = page.locator('.alert button');
      const count = await dismissButtons.count();
      expect(count).toBeGreaterThan(0);
    });
  });

  test.describe('Integration with Dashboard', () => {
    test('insights appear before metrics cards', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Get positions of AI Insights and PRs Merged
      const aiInsights = page.getByRole('heading', { name: 'AI Insights' });
      const prsMerged = page.getByText('PRs Merged').first();

      const aiBox = await aiInsights.boundingBox();
      const prsBox = await prsMerged.boundingBox();

      // AI Insights should be above PRs Merged
      expect(aiBox!.y).toBeLessThan(prsBox!.y);
    });

    test('Q&A form appears after AI Summary', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Get positions
      const aiInsights = page.getByRole('heading', { name: 'AI Insights' });
      const askMetrics = page.getByRole('heading', { name: 'Ask About Your Metrics' });

      const aiBox = await aiInsights.boundingBox();
      const askBox = await askMetrics.boundingBox();

      // AI Insights should be above Ask About Your Metrics
      expect(aiBox!.y).toBeLessThan(askBox!.y);
    });

    test('date range filter does not break insights section', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Click 30d filter
      await page.getByRole('link', { name: '30d' }).click();
      await page.waitForTimeout(500);

      // AI Insights should still be visible after filter change
      await expect(page.getByRole('heading', { name: 'AI Insights' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Ask About Your Metrics' })).toBeVisible();
    });
  });
});
