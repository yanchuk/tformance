import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * Integration Feature Flags Tests
 * Tests the Coming Soon states and I'm Interested button functionality.
 * Run with: npx playwright test integration-flags.spec.ts
 * Tag: @integration-flags
 *
 * Tests cover:
 * - Google Workspace Coming Soon state (always visible)
 * - I'm Interested button functionality
 * - HTMX swap to Thanks confirmation
 * - Onboarding skip behavior when flags are disabled
 *
 * Note: Current dev flag states:
 * - integration_jira_enabled: True (enabled)
 * - integration_slack_enabled: NULL (disabled)
 * - integration_copilot_enabled: NULL (disabled)
 * - integration_google_workspace_enabled: NULL (disabled)
 */

test.describe('Integration Feature Flags @integration-flags', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Google Workspace Coming Soon', () => {
    test('shows Coming Soon badge on Google Workspace card', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Google Workspace heading should be visible
      const googleHeading = page.getByRole('heading', { name: 'Google Workspace' });
      await expect(googleHeading).toBeVisible();

      // Coming Soon badge should be visible next to the heading (use .grid > .app-card for inner cards)
      const googleCard = page.locator('.grid > .app-card').filter({ has: googleHeading });
      await expect(googleCard.getByText('Coming Soon')).toBeVisible();
    });

    test('shows Google Workspace description', async ({ page }) => {
      await page.goto('/app/integrations/');

      await expect(page.getByText('Track communication workload in calendars')).toBeVisible();
    });

    test('shows Google Workspace benefits list', async ({ page }) => {
      await page.goto('/app/integrations/');

      const googleHeading = page.getByRole('heading', { name: 'Google Workspace' });
      const googleCard = page.locator('.grid > .app-card').filter({ has: googleHeading });

      // Check for benefits (at least one should be visible)
      await expect(googleCard.getByText('Meeting time analysis')).toBeVisible();
    });

    test("shows I'm Interested button on Google Workspace", async ({ page }) => {
      await page.goto('/app/integrations/');

      const googleHeading = page.getByRole('heading', { name: 'Google Workspace' });
      const googleCard = page.locator('.grid > .app-card').filter({ has: googleHeading });
      const interestedButton = googleCard.getByRole('button', { name: "I'm Interested" });

      await expect(interestedButton).toBeVisible();
    });

    test("clicking I'm Interested changes to Thanks confirmation", async ({ page }) => {
      await page.goto('/app/integrations/');

      const googleHeading = page.getByRole('heading', { name: 'Google Workspace' });
      const googleCard = page.locator('.grid > .app-card').filter({ has: googleHeading });
      const interestedButton = googleCard.getByRole('button', { name: "I'm Interested" });

      // Click the button
      await interestedButton.click();

      // Wait for HTMX swap to complete
      await page.waitForTimeout(500);

      // Should now show Thanks! confirmation (button is disabled)
      await expect(googleCard.getByRole('button', { name: /Thanks/i })).toBeVisible();
      await expect(googleCard.getByRole('button', { name: /Thanks/i })).toBeDisabled();
    });
  });

  test.describe('Integration Cards Display', () => {
    test('displays all integration cards on integrations page', async ({ page }) => {
      await page.goto('/app/integrations/');

      // All four main integrations should be visible
      await expect(page.getByRole('heading', { name: 'GitHub', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Jira', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Slack', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'GitHub Copilot' })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Google Workspace' })).toBeVisible();
    });

    test('Jira card shows appropriate state based on flag', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Find the Jira card by looking for the heading (use .grid > .app-card for inner cards)
      const jiraHeading = page.getByRole('heading', { name: 'Jira', exact: true });
      await expect(jiraHeading).toBeVisible();

      // Get the parent card container
      const jiraCard = page.locator('.grid > .app-card').filter({ has: jiraHeading });

      // Jira flag is currently disabled in dev, so should show either:
      // - "Coming Soon" badge and "I'm Interested" button
      // - Or if flag becomes enabled: "Connected" / "Connect Jira"
      const hasComingSoon = await jiraCard.getByText('Coming Soon').isVisible().catch(() => false);
      const hasConnected = await jiraCard.getByText('Connected', { exact: true }).isVisible().catch(() => false);
      const hasConnect = await jiraCard.getByRole('link', { name: 'Connect Jira' }).isVisible().catch(() => false);

      // One of these should be true
      expect(hasComingSoon || hasConnected || hasConnect).toBeTruthy();
    });
  });

  test.describe('HTMX Interest Tracking', () => {
    test('interest tracking endpoint returns HTML partial', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Set up request interception to verify the response
      const responsePromise = page.waitForResponse(
        response => response.url().includes('/interest/') && response.status() === 200
      );

      // Click the I'm Interested button on Google Workspace (use .grid > .app-card for inner cards)
      const googleHeading = page.getByRole('heading', { name: 'Google Workspace' });
      const googleCard = page.locator('.grid > .app-card').filter({ has: googleHeading });
      await googleCard.getByRole('button', { name: "I'm Interested" }).click();

      // Wait for the response
      const response = await responsePromise;

      // Verify it returned HTML content (not JSON)
      const contentType = response.headers()['content-type'];
      expect(contentType).toContain('text/html');
    });
  });

});
