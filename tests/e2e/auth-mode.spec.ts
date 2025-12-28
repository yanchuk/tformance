import { test, expect } from '@playwright/test';

/**
 * Auth Mode Tests
 * Tests for AUTH_MODE feature flag behavior
 *
 * NOTE: These tests run against the current AUTH_MODE setting.
 * In development (AUTH_MODE=all), email forms are visible.
 * In production (AUTH_MODE=github_only), only GitHub OAuth is shown.
 *
 * Run with: npx playwright test auth-mode.spec.ts
 * Tag: @auth-mode
 */

test.describe('Auth Mode Tests @auth-mode', () => {
  test.describe('Login Page Elements', () => {
    test('login page has GitHub OAuth button', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // GitHub button should always be visible regardless of auth mode
      const githubButton = page.getByRole('button', { name: /continue with github/i });
      await expect(githubButton).toBeVisible({ timeout: 10000 });
    });

    test('login page has back to home link', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // Back to home should always be visible
      const backLink = page.getByRole('link', { name: /back to home/i });
      await expect(backLink).toBeVisible({ timeout: 10000 });
    });

    test('login page displays correctly', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // Should have Sign In heading
      const heading = page.getByRole('heading', { name: /sign in/i });
      await expect(heading).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('Signup Page Elements', () => {
    test('signup page has GitHub OAuth button', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // GitHub button should always be visible regardless of auth mode
      const githubButton = page.getByRole('button', { name: /continue with github/i });
      await expect(githubButton).toBeVisible({ timeout: 10000 });
    });

    test('signup page has sign in link', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // Already have account link should be visible (use exact match to avoid header link)
      const signInLink = page.getByRole('link', { name: 'Sign in', exact: true });
      await expect(signInLink).toBeVisible({ timeout: 10000 });
    });

    test('signup page displays correctly', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // Should have heading (Sign Up or Get Started depending on mode)
      const heading = page.getByRole('heading', { name: /sign up|get started/i });
      await expect(heading).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('AUTH_MODE=all (Development Mode)', () => {
    // These tests verify behavior when email auth is enabled
    // They may be skipped if AUTH_MODE=github_only in the test environment

    test('login page shows email form when email auth enabled', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // Check for email field - if visible, we're in "all" mode
      const emailField = page.getByRole('textbox', { name: /email/i });
      const hasEmail = await emailField.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasEmail) {
        // If email is visible, password should also be visible
        const passwordField = page.locator('input[type="password"]');
        await expect(passwordField).toBeVisible({ timeout: 10000 });

        // Sign In button should be visible
        const signInButton = page.getByRole('button', { name: /^sign in$/i });
        await expect(signInButton).toBeVisible({ timeout: 10000 });

        // Should have "or continue with" text
        const orContinue = page.getByText(/or continue with/i);
        await expect(orContinue).toBeVisible({ timeout: 10000 });
      }
    });

    test('signup page shows email form when email auth enabled', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // Check for email field
      const emailField = page.getByRole('textbox', { name: /email/i });
      const hasEmail = await emailField.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasEmail) {
        // Should have password field
        const passwordField = page.locator('input[type="password"]').first();
        await expect(passwordField).toBeVisible({ timeout: 10000 });

        // Should have Sign Up button
        const signUpButton = page.getByRole('button', { name: /^sign up$/i });
        await expect(signUpButton).toBeVisible({ timeout: 10000 });
      }
    });

    test('can fill login form when email auth enabled', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      const emailField = page.getByRole('textbox', { name: /email/i });
      const hasEmail = await emailField.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasEmail) {
        // Fill in credentials
        await emailField.fill('test@example.com');
        await page.locator('input[type="password"]').fill('testpassword');

        // Verify values are set
        await expect(emailField).toHaveValue('test@example.com');
      }
    });
  });

  test.describe('AUTH_MODE=github_only (Production Mode)', () => {
    // These tests verify behavior when only GitHub auth is shown
    // They check for the absence of email forms

    test('login page hides email form in github_only mode', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // Check if we're in github_only mode by looking for the message
      const githubOnlyMessage = page.getByText(/sign in with your github account/i);
      const isGithubOnly = await githubOnlyMessage.isVisible({ timeout: 5000 }).catch(() => false);

      if (isGithubOnly) {
        // Email field should NOT be visible
        const emailField = page.getByRole('textbox', { name: /email/i });
        await expect(emailField).not.toBeVisible();

        // Password field should NOT be visible
        const passwordField = page.locator('input[type="password"]');
        await expect(passwordField).not.toBeVisible();

        // "or continue with" should NOT appear (no divider)
        const orContinue = page.getByText(/or continue with/i);
        await expect(orContinue).not.toBeVisible();
      }
    });

    test('signup page shows GitHub CTA in github_only mode', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // Check heading - should be "Get Started" not "Sign Up"
      const getStartedHeading = page.getByRole('heading', { name: /get started/i });
      const isGithubOnly = await getStartedHeading.isVisible({ timeout: 5000 }).catch(() => false);

      if (isGithubOnly) {
        // Should show GitHub signup message
        const githubMessage = page.getByText(/create your account using github/i);
        await expect(githubMessage).toBeVisible({ timeout: 10000 });

        // Email field should NOT be visible
        const emailField = page.getByRole('textbox', { name: /email/i });
        await expect(emailField).not.toBeVisible();
      }
    });
  });

  test.describe('Google OAuth Filtering', () => {
    test('Google button is hidden when ALLOW_GOOGLE_AUTH=false', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // Google button should NOT be visible (we disabled it)
      const googleButton = page.getByRole('button', { name: /continue with google/i });
      await expect(googleButton).not.toBeVisible();
    });

    test('only GitHub OAuth is available on signup', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // GitHub should be visible
      const githubButton = page.getByRole('button', { name: /continue with github/i });
      await expect(githubButton).toBeVisible({ timeout: 10000 });

      // Google should NOT be visible
      const googleButton = page.getByRole('button', { name: /continue with google/i });
      await expect(googleButton).not.toBeVisible();
    });
  });

  test.describe('Navigation Between Auth Pages', () => {
    test('can navigate from login to signup', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      // Find and click sign up link (only visible in "all" mode)
      const signUpLink = page.getByRole('link', { name: /sign up/i });
      const hasSignUpLink = await signUpLink.isVisible({ timeout: 5000 }).catch(() => false);

      if (hasSignUpLink) {
        await signUpLink.click();
        await expect(page).toHaveURL(/\/accounts\/signup/);
      }
    });

    test('can navigate from signup to login', async ({ page }) => {
      await page.goto('/accounts/signup/');
      await page.waitForLoadState('domcontentloaded');

      // Click sign in link (use exact match to avoid header link)
      const signInLink = page.getByRole('link', { name: 'Sign in', exact: true });
      await expect(signInLink).toBeVisible({ timeout: 10000 });
      await signInLink.click();

      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('can navigate back to home from login', async ({ page }) => {
      await page.goto('/accounts/login/');
      await page.waitForLoadState('domcontentloaded');

      const backLink = page.getByRole('link', { name: /back to home/i });
      await expect(backLink).toBeVisible({ timeout: 10000 });
      await backLink.click();

      await expect(page).toHaveURL('/');
    });
  });
});
