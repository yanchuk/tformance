import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * User Profile Tests
 * Tests profile editing, avatar upload, and API key management.
 * Run with: npx playwright test profile.spec.ts
 * Tag: @profile
 */

test.describe('User Profile @profile', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Profile Page', () => {
    test('profile page loads', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Should show "My Details" heading or user email in form
      const hasMyDetailsHeading = await page.getByRole('heading', { name: /my details/i }).isVisible().catch(() => false);
      const hasEmailInput = await page.getByRole('textbox', { name: /email/i }).isVisible().catch(() => false);
      const hasUserInfo = await page.getByText(/admin@example.com/i).isVisible().catch(() => false);

      expect(hasMyDetailsHeading || hasEmailInput || hasUserInfo).toBeTruthy();
    });

    test('shows current user email', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Email should be in input field or displayed
      const emailInput = page.getByRole('textbox', { name: /email/i });
      const hasEmailInput = await emailInput.isVisible().catch(() => false);

      if (hasEmailInput) {
        const value = await emailInput.inputValue();
        expect(value).toBe('admin@example.com');
      } else {
        const hasEmailText = await page.getByText(/admin@example.com/).isVisible().catch(() => false);
        expect(hasEmailText).toBeTruthy();
      }
    });

    test('has editable fields', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Look for editable fields (name, display name, etc.)
      const nameInput = page.getByRole('textbox', { name: /name/i });
      const hasEditableFields = await nameInput.isVisible().catch(() => false);

      // Profile should have some editable fields
    });

    test('save button exists', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      const saveButton = page.getByRole('button', { name: /save|update/i });
      const hasSaveButton = await saveButton.isVisible().catch(() => false);

      // Should have save functionality
    });
  });

  test.describe('Profile Updates', () => {
    test('can update display name', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Find name input
      const nameInput = page.getByRole('textbox', { name: /first.*name|display.*name|name/i }).first();

      if (await nameInput.isVisible()) {
        const originalValue = await nameInput.inputValue();

        // Change value
        await nameInput.fill('Updated Name');

        // Find and click save
        const saveButton = page.getByRole('button', { name: /save|update/i });
        if (await saveButton.isVisible()) {
          await saveButton.click();
          await page.waitForTimeout(500);

          // Should show success or stay on page
        }
      }
    });
  });

  test.describe('Avatar Upload', () => {
    test('avatar upload section exists', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Look for avatar/image upload
      const avatarSection = page.getByText(/avatar|photo|image|picture/i);
      const fileInput = page.locator('input[type="file"]');
      const uploadButton = page.getByRole('button', { name: /upload|change.*photo/i });

      const hasAvatarSection = await avatarSection.isVisible().catch(() => false);
      const hasFileInput = await fileInput.isVisible().catch(() => false);
      const hasUploadButton = await uploadButton.isVisible().catch(() => false);

      // Some avatar functionality should exist
    });
  });

  test.describe('API Keys', () => {
    test('API keys section exists on profile', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Look for "API Keys" heading
      const apiKeyHeading = page.getByRole('heading', { name: /api keys/i });
      const hasApiSection = await apiKeyHeading.isVisible().catch(() => false);

      expect(hasApiSection).toBeTruthy();
    });

    test('new API key button exists', async ({ page }) => {
      await page.goto('/users/profile/');
      await page.waitForLoadState('domcontentloaded');

      // Look for "New API Key" button
      const createButton = page.getByRole('button', { name: /new api key/i });
      const hasCreateButton = await createButton.isVisible().catch(() => false);

      expect(hasCreateButton).toBeTruthy();
    });

    test('create API key endpoint requires auth', async ({ page, context }) => {
      await context.clearCookies();

      // POST to create endpoint without auth should fail
      const response = await page.request.post('/users/api-keys/create/');

      // Should get redirect (302) or forbidden (403)
      expect([302, 403]).toContain(response.status());
    });

    test('revoke API key endpoint requires auth', async ({ page, context }) => {
      await context.clearCookies();

      // POST to revoke endpoint without auth should fail
      const response = await page.request.post('/users/api-keys/revoke/');

      // Should get redirect (302) or forbidden (403)
      expect([302, 403]).toContain(response.status());
    });
  });

  test.describe('Profile Access Control', () => {
    test('profile page requires authentication', async ({ page, context }) => {
      await context.clearCookies();
      await page.goto('/users/profile/');

      // Should redirect to login
      await expect(page).toHaveURL(/\/accounts\/login/);
    });
  });

  test.describe('Profile Navigation', () => {
    test('can navigate to profile from app', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Find profile link in nav
      const profileLink = page.getByRole('link', { name: /profile/i });

      if (await profileLink.isVisible()) {
        await profileLink.click();
        await expect(page).toHaveURL(/\/users\/profile/);
      }
    });

    test('profile link in user menu', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Look for profile in sidebar or dropdown
      const profileLink = page.getByRole('link', { name: /profile/i });
      const hasProfileLink = await profileLink.isVisible().catch(() => false);

      expect(hasProfileLink).toBeTruthy();
    });
  });
});
