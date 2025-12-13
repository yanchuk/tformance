import { test, expect } from '@playwright/test';

/**
 * Authentication Tests
 * Run with: npx playwright test auth.spec.ts
 * Tag: @auth
 */

test.describe('Authentication Tests @auth', () => {
  test.describe('Login Flow', () => {
    test('valid credentials redirect to app', async ({ page }) => {
      await page.goto('/accounts/login/');

      // Fill login form
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');

      // Submit
      await page.getByRole('button', { name: 'Sign In' }).click();

      // Should redirect to app or onboarding
      await expect(page).toHaveURL(/\/(app|onboarding)/);
    });

    test('invalid credentials show error message', async ({ page }) => {
      await page.goto('/accounts/login/');

      // Fill with wrong password
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('wrongpassword');

      // Submit
      await page.getByRole('button', { name: 'Sign In' }).click();

      // Should show error and stay on login page
      await expect(page).toHaveURL(/\/accounts\/login/);
      await expect(page.getByText(/email address and\/or password.*not correct/i)).toBeVisible();
    });
  });

  test.describe('Access Control', () => {
    test('unauthenticated user redirected to login', async ({ page }) => {
      // Clear any existing session
      await page.context().clearCookies();

      // Try to access protected page
      await page.goto('/app/');

      // Should redirect to login with next param
      await expect(page).toHaveURL(/\/accounts\/login\/\?next=/);
    });

    test('protected redirect preserves destination', async ({ page }) => {
      await page.context().clearCookies();

      await page.goto('/app/metrics/dashboard/');

      // Should redirect with next param pointing to original destination
      const url = page.url();
      expect(url).toContain('/accounts/login/');
      expect(url).toContain('next=');
    });
  });

  test.describe('Logout Flow', () => {
    test('logout clears session and redirects to home', async ({ page }) => {
      // First login
      await page.goto('/accounts/login/');
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();

      // Wait for redirect to app
      await expect(page).toHaveURL(/\/app/);

      // Logout
      await page.goto('/accounts/logout/');

      // Should be on homepage
      await expect(page).toHaveURL('/');

      // Try to access protected page - should redirect to login
      await page.goto('/app/');
      await expect(page).toHaveURL(/\/accounts\/login/);
    });
  });
});
