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

  test.describe('CTO Dashboard', () => {
    test('dashboard page loads without errors', async ({ page }) => {
      // Navigate to analytics which redirects to CTO dashboard
      await page.getByRole('link', { name: /Analytics/ }).click();
      await page.waitForLoadState('domcontentloaded');

      // Should have CTO Overview heading
      await expect(page.getByRole('heading', { name: 'CTO Overview' })).toBeVisible();
    });

    test('metrics cards display data', async ({ page }) => {
      await page.getByRole('link', { name: /Analytics/ }).click();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Check for metric labels (use first() to avoid strict mode violation)
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
      await expect(page.getByText('Avg Cycle Time').first()).toBeVisible();
    });

    test('charts render correctly', async ({ page }) => {
      await page.getByRole('link', { name: /Analytics/ }).click();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow time for chart rendering

      // Check for chart headings
      await expect(page.getByRole('heading', { name: 'AI Adoption Trend' })).toBeVisible();
    });

    test('team breakdown table loads', async ({ page }) => {
      await page.getByRole('link', { name: /Analytics/ }).click();
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Check for Team Breakdown heading
      await expect(page.getByRole('heading', { name: 'Team Breakdown' })).toBeVisible();
    });

    test('date range filter changes URL', async ({ page }) => {
      await page.getByRole('link', { name: /Analytics/ }).click();
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

      await page.getByRole('link', { name: /Integrations/ }).click();

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
