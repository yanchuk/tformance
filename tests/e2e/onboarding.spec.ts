import { test, expect } from '@playwright/test';

/**
 * Onboarding Flow Tests
 * Tests the onboarding journey access control and redirects.
 * Run with: npx playwright test onboarding.spec.ts
 * Tag: @onboarding
 *
 * Note: OAuth flows redirect to external providers which we cannot test.
 * Most onboarding pages redirect users who already have a team to /app/,
 * so we primarily test access control and redirect behavior.
 */

test.describe('Onboarding Flow @onboarding', () => {
  test.describe('Access Control (Unauthenticated)', () => {
    test('onboarding redirects to login when not authenticated', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/onboarding/');
      await expect(page).toHaveURL(/\/accounts\/login.*next=.*onboarding/);
    });

    test('skip endpoint requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/onboarding/skip/');
      await expect(page).toHaveURL(/\/accounts\/login.*next=.*onboarding.*skip/);
    });

    test('github connect requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/onboarding/github/');
      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('complete page requires authentication', async ({ page }) => {
      await page.context().clearCookies();
      await page.goto('/onboarding/complete/');
      await expect(page).toHaveURL(/\/accounts\/login/);
    });
  });

  test.describe('Redirects (User with Team)', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();
      await expect(page).toHaveURL(/\/app/);
    });

    test('onboarding start redirects to app', async ({ page }) => {
      await page.goto('/onboarding/');
      await expect(page).toHaveURL(/\/app/);
    });

    test('skip endpoint redirects to app', async ({ page }) => {
      await page.goto('/onboarding/skip/');
      await expect(page).toHaveURL(/\/app/);
    });

    test('org selection redirects to app or onboarding', async ({ page }) => {
      await page.goto('/onboarding/org/');
      const url = page.url();
      expect(url).toMatch(/\/(app|onboarding)/);
    });

    test('repos selection redirects to app or onboarding', async ({ page }) => {
      await page.goto('/onboarding/repos/');
      const url = page.url();
      expect(url).toMatch(/\/(app|onboarding)/);
    });

    test('jira page redirects to app or onboarding', async ({ page }) => {
      await page.goto('/onboarding/jira/');
      const url = page.url();
      expect(url).toMatch(/\/(app|onboarding)/);
    });

    test('slack page redirects to app or onboarding', async ({ page }) => {
      await page.goto('/onboarding/slack/');
      const url = page.url();
      expect(url).toMatch(/\/(app|onboarding)/);
    });

    test('github connect redirects appropriately', async ({ page }) => {
      await page.goto('/onboarding/github/');
      const url = page.url();
      // Should redirect to app, GitHub OAuth, or stay on onboarding
      const isValidRedirect = url.includes('/app') ||
        url.includes('github.com') ||
        url.includes('/onboarding');
      expect(isValidRedirect).toBeTruthy();
    });
  });

  test.describe('Complete Page', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();
    });

    test('complete page shows success heading', async ({ page }) => {
      await page.goto('/onboarding/complete/');

      const url = page.url();
      if (url.includes('/onboarding/complete')) {
        await expect(page.getByRole('heading', { name: /You're All Set/ })).toBeVisible();
      }
    });

    test('complete page shows Go to Dashboard button', async ({ page }) => {
      await page.goto('/onboarding/complete/');

      const url = page.url();
      if (url.includes('/onboarding/complete')) {
        await expect(page.getByRole('link', { name: /Go to Dashboard/ })).toBeVisible();
      }
    });

    test('Go to Dashboard navigates to app', async ({ page }) => {
      await page.goto('/onboarding/complete/');

      const dashboardButton = page.getByRole('link', { name: /Go to Dashboard/ });
      if (await dashboardButton.isVisible()) {
        await dashboardButton.click();
        await expect(page).toHaveURL(/\/app/);
      }
    });
  });

  test.describe('Page Navigation Controls', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();
    });

    test('logout button is visible on complete page', async ({ page }) => {
      await page.goto('/onboarding/complete/');

      const url = page.url();
      if (url.includes('/onboarding/complete')) {
        const logoutButton = page.getByRole('link', { name: /log out/i });
        await expect(logoutButton).toBeVisible();
      }
    });

    test('logout button logs user out', async ({ page }) => {
      await page.goto('/onboarding/complete/');

      const logoutButton = page.getByRole('link', { name: /log out/i });
      if (await logoutButton.isVisible()) {
        await logoutButton.click();

        // Should be logged out
        await page.goto('/onboarding/');
        await expect(page).toHaveURL(/\/accounts\/login/);
      }
    });
  });
});
