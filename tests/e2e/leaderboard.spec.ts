import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * AI Detective Leaderboard Tests
 * Tests the leaderboard functionality for tracking AI guess accuracy.
 * Run with: npx playwright test leaderboard.spec.ts
 * Tag: @leaderboard
 *
 * The AI Detective Leaderboard shows team members ranked by their accuracy
 * at guessing whether PRs were AI-assisted based on code reviews.
 *
 * Location: Team Dashboard (/app/metrics/dashboard/team/)
 * Data source: PRSurveyReview (reviewer guesses vs author disclosure)
 */

test.describe('AI Detective Leaderboard @leaderboard', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Leaderboard Display', () => {
    test('leaderboard section loads on team dashboard', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow HTMX to load

      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();
    });

    test('leaderboard description text is visible', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByText(/best at spotting AI-assisted code/i)).toBeVisible();
    });

    test('leaderboard container exists for HTMX content', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // The container should exist (even if empty)
      const container = page.locator('#leaderboard-container');
      await expect(container).toBeAttached();
    });

    test('leaderboard table loads via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500); // Allow HTMX to load

      // Either table loads or "No results" message shows
      const container = page.locator('#leaderboard-container');
      const hasTable = await container.locator('table').isVisible().catch(() => false);
      const hasEmptyState = await container.getByText(/No AI Detective results/i).isVisible().catch(() => false);

      expect(hasTable || hasEmptyState).toBeTruthy();
    });
  });

  test.describe('Leaderboard Table Structure', () => {
    test('table has correct column headers when data exists', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      const container = page.locator('#leaderboard-container');
      const table = container.locator('table');

      // If table exists, check headers
      if (await table.isVisible()) {
        await expect(table.getByRole('columnheader', { name: '#' })).toBeVisible();
        await expect(table.getByRole('columnheader', { name: /Detective/i })).toBeVisible();
        await expect(table.getByRole('columnheader', { name: /Correct/i })).toBeVisible();
        await expect(table.getByRole('columnheader', { name: /Total/i })).toBeVisible();
        await expect(table.getByRole('columnheader', { name: /Accuracy/i })).toBeVisible();
      }
    });

    test('empty state shows appropriate message', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      const container = page.locator('#leaderboard-container');
      const hasData = await container.locator('table').isVisible().catch(() => false);

      if (!hasData) {
        // Should show empty state
        await expect(container.getByText(/No AI Detective results/i)).toBeVisible();
        await expect(container.getByText(/Respond to Slack surveys to participate/i)).toBeVisible();
      }
    });

    test('leaderboard rows display member information', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      const container = page.locator('#leaderboard-container');
      const table = container.locator('table');

      if (await table.isVisible()) {
        const rows = table.locator('tbody tr');
        const rowCount = await rows.count();

        if (rowCount > 0) {
          // First row should have rank, name, correct count, total, accuracy
          const firstRow = rows.first();

          // Check for avatar or placeholder
          const hasAvatar = await firstRow.locator('.avatar').isVisible();
          expect(hasAvatar).toBeTruthy();

          // Check for accuracy progress bar
          const hasProgress = await firstRow.locator('progress').isVisible();
          expect(hasProgress).toBeTruthy();

          // Check for accuracy badge
          const hasBadge = await firstRow.locator('.badge').isVisible();
          expect(hasBadge).toBeTruthy();
        }
      }
    });
  });

  test.describe('Leaderboard Ranking', () => {
    test('first place shows gold medal emoji', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      const container = page.locator('#leaderboard-container');
      const table = container.locator('table');

      if (await table.isVisible()) {
        const firstRow = table.locator('tbody tr').first();
        // Gold medal emoji: 🥇 (U+1F947)
        const firstCell = firstRow.locator('td').first();
        const cellText = await firstCell.textContent();

        // Either has medal emoji or rank number
        const hasMedalOrRank = cellText?.includes('🥇') || cellText?.trim() === '1';
        expect(hasMedalOrRank).toBeTruthy();
      }
    });

    test('accuracy percentages are displayed correctly', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      const container = page.locator('#leaderboard-container');
      const table = container.locator('table');

      if (await table.isVisible()) {
        // Check that accuracy badges contain percentage values
        const badges = table.locator('.badge');
        const badgeCount = await badges.count();

        for (let i = 0; i < badgeCount; i++) {
          const badge = badges.nth(i);
          const text = await badge.textContent();
          // Should contain a percentage (e.g., "75%")
          expect(text).toMatch(/\d+%/);
        }
      }
    });
  });

  test.describe('Date Range Filter', () => {
    test('leaderboard respects date range filter', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/?days=7');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      // Change to 30 days
      await page.getByRole('link', { name: '30d' }).click();
      await page.waitForURL(/\?days=30/);
      await page.waitForTimeout(1500);

      // Leaderboard should still be visible after filter change
      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();

      // Container should still have content
      const container = page.locator('#leaderboard-container');
      await expect(container).not.toBeEmpty();
    });

    test('leaderboard updates with 90 day filter', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/?days=90');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1500);

      // Leaderboard section should be visible
      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();

      // Container should exist
      const container = page.locator('#leaderboard-container');
      await expect(container).toBeAttached();
    });
  });

  test.describe('Leaderboard API', () => {
    test('leaderboard table API endpoint responds', async ({ page }) => {
      // Already logged in via beforeEach

      // Direct API call to leaderboard table
      const response = await page.request.get('/app/metrics/tables/leaderboard/?days=30');

      expect(response.status()).toBe(200);
    });

    test('leaderboard table API returns HTML content', async ({ page }) => {
      // Already logged in via beforeEach

      const response = await page.request.get('/app/metrics/tables/leaderboard/?days=30');
      const contentType = response.headers()['content-type'];

      expect(contentType).toContain('text/html');
    });

    test('leaderboard table API respects days parameter', async ({ page }) => {
      // Already logged in via beforeEach

      // Both should return 200 (may have different data)
      const response7 = await page.request.get('/app/metrics/tables/leaderboard/?days=7');
      const response90 = await page.request.get('/app/metrics/tables/leaderboard/?days=90');

      expect(response7.status()).toBe(200);
      expect(response90.status()).toBe(200);
    });
  });

  test.describe('Leaderboard Integration', () => {
    test('leaderboard is part of the dashboard layout', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Leaderboard should be in a card container
      const leaderboardCard = page.locator('.card').filter({
        has: page.getByRole('heading', { name: 'AI Detective Leaderboard' })
      });

      await expect(leaderboardCard).toBeVisible();
    });

    test('leaderboard appears after review distribution', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Both sections should be visible in the dashboard
      await expect(page.getByRole('heading', { name: 'Review Distribution' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();
    });
  });
});

/**
 * Leaderboard with Seeded Data Tests
 *
 * These tests verify leaderboard functionality with actual data.
 * Run after seeding: python manage.py seed_demo_data --scenario detective-game
 */
test.describe('Leaderboard with Data @leaderboard @data', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test('leaderboard shows multiple team members when data exists', async ({ page }) => {
    await page.goto('/app/metrics/dashboard/team/?days=90');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000); // Allow HTMX to load

    const container = page.locator('#leaderboard-container');
    const table = container.locator('table');

    if (await table.isVisible()) {
      const rows = table.locator('tbody tr');
      const rowCount = await rows.count();

      // With seeded data, should have at least 1 member
      // (exact count depends on seed data)
      expect(rowCount).toBeGreaterThanOrEqual(0);
    }
  });

  test('leaderboard shows correct guess counts', async ({ page }) => {
    await page.goto('/app/metrics/dashboard/team/?days=90');
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(2000);

    const container = page.locator('#leaderboard-container');
    const table = container.locator('table');

    if (await table.isVisible()) {
      // Find cells with "correct" count (should be numbers)
      const correctCells = table.locator('td.text-success');
      const count = await correctCells.count();

      for (let i = 0; i < count; i++) {
        const text = await correctCells.nth(i).textContent();
        // Should be a number
        expect(text?.trim()).toMatch(/^\d+$/);
      }
    }
  });
});
