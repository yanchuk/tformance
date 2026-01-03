import { test, expect, Page } from '@playwright/test';
import { waitForHtmxComplete } from './helpers';
import { loginAs } from './fixtures/test-users';

/**
 * LLM Feedback System E2E Tests
 * Run with: npx playwright test llm-feedback.spec.ts
 * Tag: @llm-feedback
 *
 * Tests for thumbs up/down feedback on LLM-generated content:
 * - Engineering Insights (dashboard)
 * - PR Summaries (expanded row)
 * - Q&A Answers (insights page)
 * - General feedback button (PostHog survey)
 */

test.describe('LLM Feedback System @llm-feedback', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  // ==========================================================================
  // PHASE 0: BASELINE TESTS
  // These tests verify current behavior before adding feedback UI
  // ==========================================================================

  test.describe('Baseline: Engineering Insights', () => {
    test('Engineering Insights section loads on main dashboard', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should have Engineering Insights heading on main dashboard
      await expect(page.getByRole('heading', { name: 'Engineering Insights' })).toBeVisible();

      // Engineering insights container should exist and load
      const insightsContainer = page.locator('#engineering-insights-container');
      await expect(insightsContainer).toBeVisible({ timeout: 10000 });
    });

    test('Engineering Insights shows content or loading state', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Either shows insight content OR shows loading/no data state
      // This is the baseline - feedback UI will be added here
      const insightsContainer = page.locator('#engineering-insights-container');
      const hasContent = await insightsContainer.textContent();
      expect(hasContent?.length).toBeGreaterThan(0);
    });
  });

  test.describe('Baseline: PR Expanded Row', () => {
    test('PR list page loads successfully', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should have page title
      await expect(page.getByRole('heading', { name: /pull requests/i })).toBeVisible();
    });

    test('PR table has rows to expand', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Should have at least one PR row
      const prRows = page.locator('table tbody tr');
      const count = await prRows.count();
      expect(count).toBeGreaterThan(0);
    });

    test('PR row can be expanded to show details', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Find expandable row (look for expand button/chevron)
      const expandButton = page.locator('[data-testid="expand-pr-row"]').or(
        page.locator('button[x-on\\:click*="expanded"]')
      ).first();

      if (await expandButton.isVisible()) {
        await expandButton.click();
        await waitForHtmxComplete(page, 5000);

        // Expanded content should appear
        // LLM summary section will have feedback buttons added here
        const expandedContent = page.locator('[x-show="expanded"]').or(
          page.locator('.bg-base-200\\/50')
        );
        await expect(expandedContent.first()).toBeVisible({ timeout: 5000 });
      }
    });
  });

  test.describe('Baseline: Q&A Response', () => {
    test('Q&A form is accessible on analytics overview', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Page might show onboarding wizard or analytics overview
      // If onboarding is showing, skip this test
      const onboardingWizard = page.locator('.app-steps');
      if (await onboardingWizard.isVisible({ timeout: 2000 }).catch(() => false)) {
        test.skip();
        return;
      }

      // Should have Q&A card with form input
      const qaCard = page.locator('#ai-qa-card');
      await expect(qaCard).toBeVisible({ timeout: 10000 });

      // Should have the Q&A input field
      const qaInput = page.locator('#qa-input');
      await expect(qaInput).toBeVisible();
    });

    test('submitting Q&A question shows response', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Skip if onboarding is showing
      const qaCard = page.locator('#ai-qa-card');
      if (!(await qaCard.isVisible({ timeout: 3000 }).catch(() => false))) {
        test.skip();
        return;
      }

      // Click a suggested question
      const suggestedQuestion = page.getByRole('button', { name: /How is the team doing/i });
      if (await suggestedQuestion.isVisible()) {
        await suggestedQuestion.click();

        // Wait for response (LLM can be slow)
        await waitForHtmxComplete(page, 15000);

        // Response container should have content
        const response = page.locator('#qa-response');
        await response.waitFor({ state: 'attached', timeout: 15000 });
      }
    });
  });

  // ==========================================================================
  // PHASE 3: FEATURE TESTS (WILL FAIL UNTIL IMPLEMENTATION)
  // These tests define the expected behavior of the feedback system
  // ==========================================================================

  test.describe('Feature: Thumbs Rating on Engineering Insights', () => {
    test('thumbs up/down buttons appear on insights card', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Skip if onboarding is showing
      if (await page.locator('.app-steps').isVisible({ timeout: 2000 }).catch(() => false)) {
        test.skip();
        return;
      }

      // Should have thumbs up button
      const thumbsUp = page.locator('[data-testid="thumbs-up-engineering-insight"]');
      await expect(thumbsUp).toBeVisible();

      // Should have thumbs down button
      const thumbsDown = page.locator('[data-testid="thumbs-down-engineering-insight"]');
      await expect(thumbsDown).toBeVisible();
    });

    test('clicking thumbs up sends feedback and updates UI', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Skip if onboarding is showing
      if (await page.locator('.app-steps').isVisible({ timeout: 2000 }).catch(() => false)) {
        test.skip();
        return;
      }

      const thumbsUp = page.locator('[data-testid="thumbs-up-engineering-insight"]');
      await thumbsUp.click();

      // Wait for HTMX response
      await waitForHtmxComplete(page);

      // Button should show selected state (success color)
      await expect(thumbsUp).toHaveClass(/text-success/);
    });

    test('clicking thumbs down sends feedback and updates UI', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Skip if onboarding is showing
      if (await page.locator('.app-steps').isVisible({ timeout: 2000 }).catch(() => false)) {
        test.skip();
        return;
      }

      const thumbsDown = page.locator('[data-testid="thumbs-down-engineering-insight"]');
      await thumbsDown.click();

      // Wait for HTMX response
      await waitForHtmxComplete(page);

      // Button should show selected state (error color)
      await expect(thumbsDown).toHaveClass(/text-error/);
    });

    test('rating persists after page reload', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Skip if onboarding is showing
      if (await page.locator('.app-steps').isVisible({ timeout: 2000 }).catch(() => false)) {
        test.skip();
        return;
      }

      // Rate the insight
      const thumbsUp = page.locator('[data-testid="thumbs-up-engineering-insight"]');
      await thumbsUp.click();
      await waitForHtmxComplete(page);

      // Reload page
      await page.reload();
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Rating should still be shown
      await expect(thumbsUp).toHaveClass(/text-success/);
    });

    test('can change rating from thumbs up to thumbs down', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Skip if onboarding is showing
      if (await page.locator('.app-steps').isVisible({ timeout: 2000 }).catch(() => false)) {
        test.skip();
        return;
      }

      // First rate thumbs up
      const thumbsUp = page.locator('[data-testid="thumbs-up-engineering-insight"]');
      const thumbsDown = page.locator('[data-testid="thumbs-down-engineering-insight"]');

      await thumbsUp.click();
      await waitForHtmxComplete(page);
      await expect(thumbsUp).toHaveClass(/text-success/);

      // Now change to thumbs down
      await thumbsDown.click();
      await waitForHtmxComplete(page);

      // Thumbs down should be selected, thumbs up should be deselected
      await expect(thumbsDown).toHaveClass(/text-error/);
      // Check for deselected state - has text-base-content/50 but not text-success without hover prefix
      await expect(thumbsUp).toHaveClass(/text-base-content\/50/);
    });
  });

  test.describe('Feature: Thumbs Rating on PR Summary', () => {
    test('thumbs buttons appear in expanded PR row', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Expand first PR row
      const expandButton = page.locator('button[x-on\\:click*="expanded"]').first();
      if (await expandButton.isVisible()) {
        await expandButton.click();
        await waitForHtmxComplete(page, 5000);

        // Should have thumbs buttons in expanded content
        const thumbsUp = page.locator('[data-testid="thumbs-up-pr-summary"]').first();
        const thumbsDown = page.locator('[data-testid="thumbs-down-pr-summary"]').first();

        await expect(thumbsUp).toBeVisible();
        await expect(thumbsDown).toBeVisible();
      }
    });

    test('rating PR summary works after HTMX load', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Expand first PR row
      const expandButton = page.locator('button[x-on\\:click*="expanded"]').first();
      if (await expandButton.isVisible()) {
        await expandButton.click();
        await waitForHtmxComplete(page, 5000);

        // Rate the PR summary
        const thumbsUp = page.locator('[data-testid="thumbs-up-pr-summary"]').first();
        await thumbsUp.click();
        await waitForHtmxComplete(page);

        // Button should show selected state
        await expect(thumbsUp).toHaveClass(/text-success/);
      }
    });
  });

  test.describe('Feature: Thumbs Rating on Q&A Answer', () => {
    test('thumbs buttons appear after Q&A response', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Ask a question
      const suggestedQuestion = page.getByRole('button', { name: /How is the team doing/i });
      if (await suggestedQuestion.isVisible()) {
        await suggestedQuestion.click();
        await waitForHtmxComplete(page, 15000);

        // Should have thumbs buttons after the response
        const thumbsUp = page.locator('[data-testid="thumbs-up-qa-answer"]');
        const thumbsDown = page.locator('[data-testid="thumbs-down-qa-answer"]');

        await expect(thumbsUp).toBeVisible();
        await expect(thumbsDown).toBeVisible();
      }
    });
  });

  test.describe('Feature: Comment Modal', () => {
    test('add comment button appears after rating', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Expand first PR row to get thumbs rating
      const expandButton = page.locator('button[x-on\\:click*="expanded"]').first();
      if (!(await expandButton.isVisible({ timeout: 3000 }).catch(() => false))) {
        test.skip();
        return;
      }
      await expandButton.click();
      await waitForHtmxComplete(page, 5000);

      // Rate the PR summary
      const thumbsUp = page.locator('[data-testid="thumbs-up-pr-summary"]').first();
      await thumbsUp.click();
      await waitForHtmxComplete(page);

      // Add comment button should appear
      const addComment = page.locator('[data-testid="add-feedback-comment"]').first();
      await expect(addComment).toBeVisible();
    });

    test('clicking add comment opens modal', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Expand first PR row
      const expandButton = page.locator('button[x-on\\:click*="expanded"]').first();
      if (!(await expandButton.isVisible({ timeout: 3000 }).catch(() => false))) {
        test.skip();
        return;
      }
      await expandButton.click();
      await waitForHtmxComplete(page, 5000);

      // Rate the PR summary
      const thumbsUp = page.locator('[data-testid="thumbs-up-pr-summary"]').first();
      await thumbsUp.click();
      await waitForHtmxComplete(page);

      // Click add comment
      const addComment = page.locator('[data-testid="add-feedback-comment"]').first();
      await addComment.click();

      // Modal should appear
      const modal = page.locator('[data-testid="feedback-comment-modal"]');
      await expect(modal).toBeVisible();
    });

    test('submitting comment saves successfully', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await waitForHtmxComplete(page, 10000);

      // Expand first PR row
      const expandButton = page.locator('button[x-on\\:click*="expanded"]').first();
      if (!(await expandButton.isVisible({ timeout: 3000 }).catch(() => false))) {
        test.skip();
        return;
      }
      await expandButton.click();
      await waitForHtmxComplete(page, 5000);

      // Rate the PR summary
      const thumbsUp = page.locator('[data-testid="thumbs-up-pr-summary"]').first();
      await thumbsUp.click();
      await waitForHtmxComplete(page);

      // Open comment modal
      const addComment = page.locator('[data-testid="add-feedback-comment"]').first();
      await addComment.click();

      // Fill in comment
      const textarea = page.locator('[data-testid="feedback-comment-input"]');
      await textarea.fill('This insight was very helpful!');

      // Submit
      const submitBtn = page.locator('[data-testid="feedback-comment-submit"]');
      await submitBtn.click();
      await waitForHtmxComplete(page);

      // Modal should close, comment indicator should appear
      await expect(page.locator('[data-testid="feedback-comment-modal"]')).not.toBeVisible();
      await expect(page.locator('[data-testid="has-comment-indicator"]').first()).toBeVisible();
    });
  });
});
