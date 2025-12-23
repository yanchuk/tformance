import { test, expect } from '@playwright/test';

/**
 * Integration Page Tests
 * Tests the integrations management pages (GitHub, Jira, Slack, Copilot)
 * Run with: npx playwright test integrations.spec.ts
 * Tag: @integrations
 */

test.describe('Integration Tests @integrations', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('Integrations Home Page', () => {
    test('page loads with correct title and subtitle', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Verify page title
      await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible();
      // Verify subtitle text
      await expect(page.getByText('Connect your development tools to start tracking metrics.')).toBeVisible();
    });

    test('displays all four integration cards', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Each integration should have a heading (h2) in its card
      await expect(page.getByRole('heading', { name: 'GitHub', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Jira', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'Slack', exact: true })).toBeVisible();
      await expect(page.getByRole('heading', { name: 'GitHub Copilot' })).toBeVisible();
    });

    test('shows GitHub description text', async ({ page }) => {
      await page.goto('/app/integrations/');
      await expect(page.getByText('Pull requests, commits, and reviews')).toBeVisible();
    });

    test('shows Jira description text', async ({ page }) => {
      await page.goto('/app/integrations/');
      await expect(page.getByText('Issues and sprint tracking')).toBeVisible();
    });

    test('shows Slack description text', async ({ page }) => {
      await page.goto('/app/integrations/');
      await expect(page.getByText('PR surveys and leaderboards')).toBeVisible();
    });

    test('shows Copilot description text', async ({ page }) => {
      await page.goto('/app/integrations/');
      await expect(page.getByText('AI coding assistant metrics')).toBeVisible();
    });
  });

  test.describe('GitHub Integration - Connected State', () => {
    test('shows connected status when GitHub is integrated', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Demo data has GitHub connected, so "Connected" badge should be visible
      // First Connected text should be for GitHub
      const connectedBadges = page.getByText('Connected', { exact: true });
      await expect(connectedBadges.first()).toBeVisible();
    });

    test('shows Members link when connected', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Members link should be visible in GitHub card
      const membersLink = page.getByRole('link', { name: /Members/ });
      await expect(membersLink).toBeVisible();
    });

    test('shows Repositories link when connected', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Repositories link should be visible in GitHub card
      const reposLink = page.getByRole('link', { name: /Repositories/ });
      await expect(reposLink).toBeVisible();
    });

    test('shows Disconnect button when connected', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Disconnect button should be visible
      const disconnectButton = page.getByRole('button', { name: 'Disconnect' }).first();
      await expect(disconnectButton).toBeVisible();
    });

    test('Disconnect button shows confirmation flow', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Click first disconnect button (GitHub)
      const disconnectButton = page.getByRole('button', { name: 'Disconnect' }).first();
      await disconnectButton.click();

      // Should show Confirm and Cancel buttons
      await expect(page.getByRole('button', { name: 'Confirm' }).first()).toBeVisible();
      await expect(page.getByRole('button', { name: 'Cancel' }).first()).toBeVisible();
    });

    test('Cancel button hides confirmation flow', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Click disconnect to show confirmation
      const disconnectButton = page.getByRole('button', { name: 'Disconnect' }).first();
      await disconnectButton.click();

      // Click Cancel
      await page.getByRole('button', { name: 'Cancel' }).first().click();

      // Confirm button should no longer be visible
      await expect(page.getByRole('button', { name: 'Confirm' }).first()).not.toBeVisible();
      // Disconnect button should be visible again
      await expect(disconnectButton).toBeVisible();
    });
  });

  test.describe('GitHub Members Page', () => {
    test('navigates to Members page from integrations', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Click Members link
      await page.getByRole('link', { name: /Members/ }).click();

      // Should be on GitHub Members page
      await expect(page).toHaveURL(/\/github\/members/);
      await expect(page.getByRole('heading', { name: 'GitHub Members' })).toBeVisible();
    });

    test('Members page shows subtitle', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');
      await expect(page.getByText('Manage team members imported from GitHub.')).toBeVisible();
    });

    test('Members page has Back to Integrations link', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');

      const backLink = page.getByRole('link', { name: 'Back to Integrations' });
      await expect(backLink).toBeVisible();

      // Click and verify navigation
      await backLink.click();
      await expect(page).toHaveURL(/\/integrations\/?$/);
    });

    test('Members page shows Sync Now button for admins', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');

      // Admin user should see Sync Now button
      await expect(page.getByRole('button', { name: /Sync Now/ })).toBeVisible();
    });

    test('Members page shows table with expected columns', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');

      // Table headers should be visible (if members exist)
      const table = page.locator('table');
      const tableExists = await table.isVisible().catch(() => false);

      if (tableExists) {
        await expect(page.getByRole('columnheader', { name: 'Name', exact: true })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'GitHub Username' })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'Email' })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'Status', exact: true })).toBeVisible();
      } else {
        // Empty state - should show empty message
        await expect(page.getByText('No GitHub members found')).toBeVisible();
      }
    });

    test('Members page shows member count', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');

      // Either shows count or empty state
      const hasCount = await page.getByText(/Showing \d+ members?/).isVisible().catch(() => false);
      const hasEmpty = await page.getByText('No GitHub members found').isVisible().catch(() => false);

      expect(hasCount || hasEmpty).toBeTruthy();
    });
  });

  test.describe('GitHub Repositories Page', () => {
    test('navigates to Repositories page from integrations', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Click Repositories link
      await page.getByRole('link', { name: /Repositories/ }).click();

      // Should be on GitHub Repositories page
      await expect(page).toHaveURL(/\/github\/repos/);
      await expect(page.getByRole('heading', { name: 'GitHub Repositories' })).toBeVisible();
    });

    test('Repositories page shows subtitle', async ({ page }) => {
      await page.goto('/app/integrations/github/repos/');
      await expect(page.getByText('Repositories from your GitHub organization.')).toBeVisible();
    });

    test('Repositories page has Back to Integrations link', async ({ page }) => {
      await page.goto('/app/integrations/github/repos/');

      const backLink = page.getByRole('link', { name: 'Back to Integrations' });
      await expect(backLink).toBeVisible();
    });

    test('Repositories page shows table with expected columns', async ({ page }) => {
      await page.goto('/app/integrations/github/repos/');

      const table = page.locator('table');
      const tableExists = await table.isVisible().catch(() => false);

      if (tableExists) {
        await expect(page.getByRole('columnheader', { name: 'Name', exact: true })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'Description' })).toBeVisible();
        await expect(page.getByRole('columnheader', { name: 'Status', exact: true })).toBeVisible();
      } else {
        // Empty state
        await expect(page.getByText('No repositories found')).toBeVisible();
      }
    });

    test('Repositories page shows repository count', async ({ page }) => {
      await page.goto('/app/integrations/github/repos/');

      // Either shows count or empty state
      const hasCount = await page.getByText(/Showing \d+ repositor(y|ies)/).isVisible().catch(() => false);
      const hasEmpty = await page.getByText('No repositories found').isVisible().catch(() => false);

      expect(hasCount || hasEmpty).toBeTruthy();
    });
  });

  test.describe('Jira Integration', () => {
    test('shows Jira integration card', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Jira card should be visible
      await expect(page.getByRole('heading', { name: 'Jira', exact: true })).toBeVisible();
    });

    test('shows Connect Jira or Projects link based on connection status', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Either Connect Jira link (not connected) or Projects link (connected) should be visible
      const connectLink = page.getByRole('link', { name: 'Connect Jira' });
      const projectsLink = page.getByRole('link', { name: /Projects/ });

      const connectVisible = await connectLink.isVisible().catch(() => false);
      const projectsVisible = await projectsLink.isVisible().catch(() => false);

      // One of them must be visible
      expect(connectVisible || projectsVisible).toBeTruthy();
    });
  });

  test.describe('Slack Integration', () => {
    test('shows Slack integration card', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Slack card should be visible
      await expect(page.getByRole('heading', { name: 'Slack', exact: true })).toBeVisible();
    });

    test('shows Connect Slack or Settings link based on connection status', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Either Connect Slack link (not connected) or Settings link (connected) should be visible
      const connectLink = page.getByRole('link', { name: 'Connect Slack' });
      const settingsLink = page.getByRole('link', { name: /Settings/ });

      const connectVisible = await connectLink.isVisible().catch(() => false);
      const settingsVisible = await settingsLink.isVisible().catch(() => false);

      // One of them must be visible
      expect(connectVisible || settingsVisible).toBeTruthy();
    });
  });

  test.describe('GitHub Copilot Integration', () => {
    test('shows Copilot integration card', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Copilot card should be visible
      await expect(page.getByRole('heading', { name: 'GitHub Copilot' })).toBeVisible();
    });

    test('shows availability status', async ({ page }) => {
      await page.goto('/app/integrations/');

      // Either "Available" or "Not available" should be visible
      const available = page.getByText('Available', { exact: true });
      const notAvailable = page.getByText('Not available', { exact: true });

      const availableVisible = await available.isVisible().catch(() => false);
      const notAvailableVisible = await notAvailable.isVisible().catch(() => false);

      expect(availableVisible || notAvailableVisible).toBeTruthy();
    });

    test('shows Sync Now button when Copilot is available', async ({ page }) => {
      await page.goto('/app/integrations/');

      // If Available, Sync Now button should be visible
      const available = page.getByText('Available', { exact: true });
      const availableVisible = await available.isVisible().catch(() => false);

      if (availableVisible) {
        // Sync Now button should be in Copilot card
        const syncButton = page.getByRole('button', { name: /Sync Now/ });
        await expect(syncButton).toBeVisible();
      }
    });

    test('shows guidance text when Copilot is not available', async ({ page }) => {
      await page.goto('/app/integrations/');

      // If Not Available, guidance text should be visible
      const notAvailable = page.getByText('Not available', { exact: true });
      const notAvailableVisible = await notAvailable.isVisible().catch(() => false);

      if (notAvailableVisible) {
        await expect(page.getByText(/Connect GitHub first to access Copilot metrics/)).toBeVisible();
      }
    });
  });

  test.describe('Navigation Integration', () => {
    test('breadcrumb navigation works from Members page', async ({ page }) => {
      // Start at Members page
      await page.goto('/app/integrations/github/members/');

      // Click back link
      await page.getByRole('link', { name: 'Back to Integrations' }).click();

      // Should be on integrations home
      await expect(page).toHaveURL(/\/integrations\/?$/);
      await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible();
    });

    test('breadcrumb navigation works from Repositories page', async ({ page }) => {
      // Start at Repositories page
      await page.goto('/app/integrations/github/repos/');

      // Click back link
      await page.getByRole('link', { name: 'Back to Integrations' }).click();

      // Should be on integrations home
      await expect(page).toHaveURL(/\/integrations\/?$/);
      await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible();
    });

    test('can navigate between Members and Repositories via integrations home', async ({ page }) => {
      // Start at integrations home
      await page.goto('/app/integrations/');

      // Go to Members
      await page.getByRole('link', { name: /Members/ }).click();
      await expect(page).toHaveURL(/\/github\/members/);

      // Go back to integrations
      await page.getByRole('link', { name: 'Back to Integrations' }).click();

      // Go to Repositories
      await page.getByRole('link', { name: /Repositories/ }).click();
      await expect(page).toHaveURL(/\/github\/repos/);
    });
  });
});
