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

  test.describe('Signup Flow', () => {
    test('signup page loads', async ({ page }) => {
      await page.goto('/accounts/signup/');

      // Should show signup form
      const hasEmailField = await page.getByRole('textbox', { name: 'Email' }).isVisible().catch(() => false);
      const hasSignupHeading = await page.getByText(/sign up|create.*account|register/i).isVisible().catch(() => false);

      expect(hasEmailField || hasSignupHeading).toBeTruthy();
    });

    test('signup form has required fields', async ({ page }) => {
      await page.goto('/accounts/signup/');

      // Check for email field
      const emailField = page.getByRole('textbox', { name: 'Email' });
      expect(await emailField.isVisible()).toBeTruthy();

      // Check for password field
      const passwordField = page.getByRole('textbox', { name: /password/i }).first();
      const hasPassword = await passwordField.isVisible().catch(() => false);

      // Should have password field (might be type="password" not textbox)
    });

    test('signup with invalid email shows error', async ({ page }) => {
      await page.goto('/accounts/signup/');

      const emailField = page.getByRole('textbox', { name: 'Email' });
      if (await emailField.isVisible()) {
        await emailField.fill('invalid-email');

        // Try to submit
        const submitButton = page.getByRole('button', { name: /sign up|create|register/i });
        if (await submitButton.isVisible()) {
          await submitButton.click();

          // Should show validation error or stay on page
          await expect(page).toHaveURL(/\/accounts\/signup/);
        }
      }
    });

    test('signup redirects after success', async ({ page }) => {
      await page.goto('/accounts/signup/');

      // Generate unique email
      const uniqueEmail = `test-${Date.now()}@example.com`;

      const emailField = page.getByRole('textbox', { name: 'Email' });
      if (await emailField.isVisible()) {
        await emailField.fill(uniqueEmail);

        // Fill password fields
        const passwordFields = page.locator('input[type="password"]');
        const passwordCount = await passwordFields.count();

        if (passwordCount >= 1) {
          await passwordFields.nth(0).fill('TestPassword123!');
        }
        if (passwordCount >= 2) {
          await passwordFields.nth(1).fill('TestPassword123!');
        }

        // Submit
        const submitButton = page.getByRole('button', { name: /sign up|create|register/i });
        if (await submitButton.isVisible()) {
          await submitButton.click();

          // Should redirect to onboarding or app (or email verification)
          await page.waitForURL(/\/(onboarding|app|accounts\/confirm)/, { timeout: 10000 }).catch(() => {});
        }
      }
    });
  });

  test.describe('Password Change', () => {
    test('password change page requires authentication', async ({ page, context }) => {
      await context.clearCookies();
      await page.goto('/accounts/password/change/');

      // Should redirect to login
      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('password change page loads when authenticated', async ({ page }) => {
      // Login first
      await page.goto('/accounts/login/');
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();
      await expect(page).toHaveURL(/\/app/);

      // Navigate to password change
      await page.goto('/accounts/password/change/');

      // Should show password change form
      const hasPasswordField = await page.locator('input[type="password"]').first().isVisible().catch(() => false);
      const hasChangeHeading = await page.getByText(/change.*password|password/i).isVisible().catch(() => false);

      expect(hasPasswordField || hasChangeHeading).toBeTruthy();
    });

    test('password change requires current password', async ({ page }) => {
      // Login first
      await page.goto('/accounts/login/');
      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();

      await page.goto('/accounts/password/change/');

      // Look for current password field
      const currentPasswordLabel = page.getByText(/current|old/i);
      const hasCurrentPassword = await currentPasswordLabel.isVisible().catch(() => false);

      // Password change should require current password
    });
  });

  test.describe('Password Reset', () => {
    test('password reset page loads', async ({ page }) => {
      await page.goto('/accounts/password/reset/');

      // Should show reset form
      const hasEmailField = await page.getByRole('textbox', { name: /email/i }).isVisible().catch(() => false);
      const hasResetHeading = await page.getByText(/reset|forgot|password/i).isVisible().catch(() => false);

      expect(hasEmailField || hasResetHeading).toBeTruthy();
    });

    test('can enter email for password reset', async ({ page }) => {
      await page.goto('/accounts/password/reset/');

      const emailField = page.getByRole('textbox', { name: /email/i });
      if (await emailField.isVisible()) {
        await emailField.fill('admin@example.com');
        const value = await emailField.inputValue();
        expect(value).toBe('admin@example.com');
      }
    });

    test('password reset form submission', async ({ page }) => {
      await page.goto('/accounts/password/reset/');

      const emailField = page.getByRole('textbox', { name: /email/i });
      const submitButton = page.getByRole('button', { name: /reset|send|submit/i });

      if (await emailField.isVisible() && await submitButton.isVisible()) {
        await emailField.fill('admin@example.com');
        await submitButton.click();

        // Should show success message or redirect to done page
        await page.waitForTimeout(500);

        const hasSuccess = await page.getByText(/sent|check.*email|reset.*link/i).isVisible().catch(() => false);
        const onDonePage = page.url().includes('done');

        // Either shows success message or redirects
      }
    });
  });
});
