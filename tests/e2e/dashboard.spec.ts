import { test, expect } from '@playwright/test';

/**
 * Dashboard Tests
 * Run with: npx playwright test dashboard.spec.ts
 * Tag: @dashboard
 *
 * These tests require a logged-in session.
 */

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
      await page.waitForTimeout(1000); // Allow HTMX to load

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
      await page.waitForTimeout(1000); // Allow HTMX to load

      await expect(page.getByRole('heading', { name: 'Review Distribution' })).toBeVisible();
    });

    test('AI detective leaderboard section loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow HTMX to load

      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();
    });

    test('recent pull requests table loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow HTMX to load

      await expect(page.getByRole('heading', { name: 'Recent Pull Requests' })).toBeVisible();

      // Check for table headers
      await expect(page.getByRole('columnheader', { name: 'Pull Request' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Author' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'AI' })).toBeVisible();
    });

    test('date range filter works', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Click 30d filter
      await page.getByRole('link', { name: '30d' }).click();
      await expect(page).toHaveURL(/\?days=30/);

      // Click 90d filter
      await page.getByRole('link', { name: '90d' }).click();
      await expect(page).toHaveURL(/\?days=90/);
    });
  });

  test.describe('CTO Dashboard', () => {
    test('dashboard page loads without errors', async ({ page }) => {
      // Navigate directly to CTO dashboard
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Should have CTO Overview heading
      await expect(page.getByRole('heading', { name: 'CTO Overview' })).toBeVisible();
    });

    test('metrics cards display data', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Check for metric labels (use first() to avoid strict mode violation)
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
      await expect(page.getByText('Avg Cycle Time').first()).toBeVisible();
    });

    test('charts render correctly', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow time for chart rendering

      // Check for chart headings
      await expect(page.getByRole('heading', { name: 'AI Adoption Trend' })).toBeVisible();
    });

    test('team breakdown table loads', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Check for Team Breakdown heading
      await expect(page.getByRole('heading', { name: 'Team Breakdown' })).toBeVisible();
    });

    test('date range filter changes URL', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Click 7d filter
      await page.getByRole('link', { name: '7d' }).click();
      await expect(page).toHaveURL(/\?days=7/);

      // Click 90d filter
      await page.getByRole('link', { name: '90d' }).click();
      await expect(page).toHaveURL(/\?days=90/);
    });
  });

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
