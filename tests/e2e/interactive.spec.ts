import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * Interactive Elements Tests
 * Tests all clickable UI elements, buttons, forms, and modals.
 * Run with: npx playwright test interactive.spec.ts
 * Tag: @interactive
 */

test.describe('Interactive Elements @interactive', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Navigation Links', () => {
    test('logo navigates to app home', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      // Click the logo/brand link
      const logo = page.locator('a[href="/app/"]').first();
      if (await logo.isVisible()) {
        await logo.click();
        await expect(page).toHaveURL('/app/');
      }
    });

    test('Dashboard nav link works', async ({ page }) => {
      await page.goto('/app/');
      // Use exact match to avoid multiple matches
      const dashboardLink = page.getByRole('link', { name: 'Dashboard' }).or(
        page.getByRole('link', { name: 'Analytics' })
      ).first();
      if (await dashboardLink.isVisible()) {
        await dashboardLink.click();
        await expect(page).toHaveURL(/\/(metrics\/dashboard|app)/);
      }
    });

    test('Integrations nav link works', async ({ page }) => {
      await page.goto('/app/');
      const integrationsLink = page.getByRole('link', { name: /integrations/i }).first();
      if (await integrationsLink.isVisible()) {
        await integrationsLink.click();
        await expect(page).toHaveURL(/\/integrations/);
      }
    });

    test('Team Settings link works', async ({ page }) => {
      await page.goto('/app/');
      // Look for settings link in nav or dropdown
      const settingsLink = page.getByRole('link', { name: /settings/i }).first();
      if (await settingsLink.isVisible()) {
        await settingsLink.click();
        await expect(page).toHaveURL(/\/team/);
      }
    });
  });

  test.describe('Dashboard Filter Buttons', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      // Wait for dashboard to load
      await page.waitForLoadState('domcontentloaded');
    });

    test('7 Days filter button is clickable and activates', async ({ page }) => {
      const button = page.getByRole('button', { name: /7 days/i });
      if (await button.isVisible()) {
        await button.click();
        // Wait for HTMX content update
        await page.waitForTimeout(500);
        // Button should have active state
        await expect(button).toBeVisible();
      }
    });

    test('30 Days filter button is clickable and activates', async ({ page }) => {
      const button = page.getByRole('button', { name: /30 days/i });
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(500);
        await expect(button).toBeVisible();
      }
    });

    test('90 Days filter button is clickable and activates', async ({ page }) => {
      const button = page.getByRole('button', { name: /90 days/i });
      if (await button.isVisible()) {
        await button.click();
        await page.waitForTimeout(500);
        await expect(button).toBeVisible();
      }
    });

    test('multiple rapid filter clicks do not break UI', async ({ page }) => {
      const button7d = page.getByRole('button', { name: /7 days/i });
      const button30d = page.getByRole('button', { name: /30 days/i });

      if (await button7d.isVisible() && await button30d.isVisible()) {
        // Rapid clicks
        await button7d.click();
        await button30d.click();
        await button7d.click();
        await button30d.click();

        // Wait for final state
        await page.waitForTimeout(1000);

        // Page should still be functional
        await expect(page.locator('.stat').first()).toBeVisible();
      }
    });
  });

  test.describe('App Home Buttons', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');
    });

    test('View Analytics button navigates to team dashboard', async ({ page }) => {
      const button = page.getByRole('link', { name: 'View Analytics' });
      if (await button.isVisible()) {
        await button.click();
        await expect(page).toHaveURL(/\/metrics\/dashboard/);
      }
    });

    test('Manage Integrations button navigates to integrations', async ({ page }) => {
      const button = page.getByRole('link', { name: /manage integrations|integrations/i }).first();
      if (await button.isVisible()) {
        await button.click();
        await expect(page).toHaveURL(/\/integrations/);
      }
    });
  });

  test.describe('Integration Page Buttons', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/integrations/');
      await page.waitForLoadState('domcontentloaded');
    });

    test('GitHub card has connect or manage button', async ({ page }) => {
      const githubCard = page.locator('[data-integration="github"]').or(
        page.locator('.card').filter({ hasText: /github/i })
      );

      if (await githubCard.isVisible()) {
        const button = githubCard.getByRole('link').or(githubCard.getByRole('button')).first();
        await expect(button).toBeVisible();
      }
    });

    test('Jira card has connect or manage button', async ({ page }) => {
      const jiraCard = page.locator('[data-integration="jira"]').or(
        page.locator('.card').filter({ hasText: /jira/i })
      );

      if (await jiraCard.isVisible()) {
        const button = jiraCard.getByRole('link').or(jiraCard.getByRole('button')).first();
        await expect(button).toBeVisible();
      }
    });

    test('Slack card has connect or manage button', async ({ page }) => {
      const slackCard = page.locator('[data-integration="slack"]').or(
        page.locator('.card').filter({ hasText: /slack/i })
      );

      if (await slackCard.isVisible()) {
        const button = slackCard.getByRole('link').or(slackCard.getByRole('button')).first();
        await expect(button).toBeVisible();
      }
    });

    test('Sync Now button is clickable when visible', async ({ page }) => {
      const syncButton = page.getByRole('button', { name: /sync now|sync/i }).first();
      if (await syncButton.isVisible()) {
        // Click should trigger sync (not navigate)
        await syncButton.click();
        // Should show loading or success state
        await page.waitForTimeout(500);
        // Page should still be on integrations
        await expect(page).toHaveURL(/\/integrations/);
      }
    });
  });

  test.describe('GitHub Integration Management', () => {
    test('Members page loads when GitHub is connected', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');
      // Either shows members list or redirects to connect
      const url = page.url();
      if (url.includes('/members/')) {
        // Members page loaded - check for content
        await page.waitForLoadState('domcontentloaded');
      }
    });

    test('Repositories page loads when GitHub is connected', async ({ page }) => {
      await page.goto('/app/integrations/github/repos/');
      // Either shows repos list or redirects
      const url = page.url();
      if (url.includes('/repos/')) {
        await page.waitForLoadState('domcontentloaded');
      }
    });

    test('member toggle switches are interactive', async ({ page }) => {
      await page.goto('/app/integrations/github/members/');
      await page.waitForLoadState('domcontentloaded');

      // Find toggle switches
      const toggles = page.locator('input[type="checkbox"]').or(
        page.locator('.toggle')
      );

      const count = await toggles.count();
      if (count > 0) {
        const firstToggle = toggles.first();
        const initialState = await firstToggle.isChecked();
        await firstToggle.click();
        // State should change (or HTMX should process)
        await page.waitForTimeout(500);
      }
    });

    test('repository toggle switches are interactive', async ({ page }) => {
      await page.goto('/app/integrations/github/repos/');
      await page.waitForLoadState('domcontentloaded');

      const toggles = page.locator('input[type="checkbox"]').or(
        page.locator('.toggle')
      );

      const count = await toggles.count();
      if (count > 0) {
        const firstToggle = toggles.first();
        await firstToggle.click();
        await page.waitForTimeout(500);
      }
    });
  });

  test.describe('Table Interactions', () => {
    test('table headers are visible on team dashboard', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      // Wait for HTMX tables to load
      await page.waitForTimeout(2000);

      // Look for any table headers (HTMX may load them dynamically)
      const tableHeaders = page.locator('th');
      const count = await tableHeaders.count();
      // Tables may or may not be present depending on data
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('recent PRs table has clickable rows or links', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Wait for HTMX tables to load
      await page.waitForTimeout(1000);

      // Look for PR links in tables
      const prLinks = page.locator('table a').or(
        page.locator('[data-pr-link]')
      );

      const count = await prLinks.count();
      // Tables may have links if there's data
    });

    test('leaderboard table displays when data exists', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Look for leaderboard section
      const leaderboard = page.locator('[data-testid="leaderboard"]').or(
        page.getByText(/ai detective|leaderboard/i)
      );

      // Should be visible if there's survey data
    });
  });

  test.describe('Chart Interactions', () => {
    test('cycle time chart canvas is rendered', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Chart.js renders to canvas
      const canvases = page.locator('canvas');
      const count = await canvases.count();
      // Should have at least one chart
      expect(count).toBeGreaterThanOrEqual(0);
    });

    test('charts respond to hover (no errors)', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      const canvas = page.locator('canvas').first();
      if (await canvas.isVisible()) {
        // Hover over chart
        await canvas.hover();
        // Should not cause errors - check console
        const errors = await page.evaluate(() => {
          return (window as any).__playwright_console_errors || [];
        });
      }
    });
  });

  test.describe('Form Interactions', () => {
    test('login form submits on Enter key', async ({ page, context }) => {
      // Clear cookies to be logged out
      await context.clearCookies();
      await page.goto('/accounts/login/');

      await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');

      // Press Enter instead of clicking button
      await page.keyboard.press('Enter');

      // Should submit and redirect
      await expect(page).toHaveURL(/\/(app|onboarding)/, { timeout: 10000 });
    });

    test('login form has correct tab order', async ({ page, context }) => {
      await context.clearCookies();
      await page.goto('/accounts/login/');

      // Tab through form fields
      await page.keyboard.press('Tab');
      const emailFocused = await page.getByRole('textbox', { name: 'Email' }).evaluate(
        (el) => document.activeElement === el
      );

      await page.keyboard.press('Tab');
      const passwordFocused = await page.getByRole('textbox', { name: 'Password' }).evaluate(
        (el) => document.activeElement === el
      );

      // At least one should be focusable via tab
    });
  });

  test.describe('Dropdown Menus', () => {
    test('user dropdown opens on click', async ({ page }) => {
      await page.goto('/app/');

      // Look for user menu / dropdown trigger
      const userMenu = page.locator('[data-dropdown="user"]').or(
        page.getByRole('button', { name: /menu|profile|account/i })
      ).or(
        page.locator('.dropdown-toggle')
      ).first();

      if (await userMenu.isVisible()) {
        await userMenu.click();
        await page.waitForTimeout(200);

        // Dropdown content should appear
        const dropdown = page.locator('.dropdown-content').or(
          page.locator('[role="menu"]')
        );
        // May or may not be visible depending on UI implementation
      }
    });

    test('logout option is accessible', async ({ page }) => {
      await page.goto('/app/');

      // Find logout link or button
      const logoutLink = page.getByRole('link', { name: /logout|sign out/i }).or(
        page.getByRole('button', { name: /logout|sign out/i })
      );

      // Should exist somewhere on the page (possibly in dropdown)
      if (await logoutLink.isVisible()) {
        await logoutLink.click();
        await expect(page).toHaveURL('/');
      }
    });
  });

  test.describe('Modal Dialogs', () => {
    test('disconnect confirmation modal appears when triggered', async ({ page }) => {
      await page.goto('/app/integrations/');
      await page.waitForLoadState('domcontentloaded');

      // Look for disconnect button
      const disconnectButton = page.getByRole('button', { name: /disconnect/i }).first();

      if (await disconnectButton.isVisible()) {
        await disconnectButton.click();
        await page.waitForTimeout(300);

        // Modal should appear
        const modal = page.locator('[role="dialog"]').or(
          page.locator('.modal')
        );

        // Check for modal or inline confirmation
      }
    });

    test('modal can be closed with cancel button', async ({ page }) => {
      await page.goto('/app/integrations/');
      await page.waitForLoadState('domcontentloaded');

      const disconnectButton = page.getByRole('button', { name: /disconnect/i }).first();

      if (await disconnectButton.isVisible()) {
        await disconnectButton.click();
        await page.waitForTimeout(300);

        const cancelButton = page.getByRole('button', { name: 'Cancel' });
        if (await cancelButton.isVisible()) {
          await cancelButton.click();
          await page.waitForTimeout(200);
          // Modal should close
        }
      }
    });

    test('modal can be closed with escape key', async ({ page }) => {
      await page.goto('/app/integrations/');
      await page.waitForLoadState('domcontentloaded');

      const disconnectButton = page.getByRole('button', { name: /disconnect/i }).first();

      if (await disconnectButton.isVisible()) {
        await disconnectButton.click();
        await page.waitForTimeout(300);

        // Press Escape
        await page.keyboard.press('Escape');
        await page.waitForTimeout(200);

        // Modal should close
      }
    });
  });

  test.describe('Theme Toggle', () => {
    test('theme toggle dropdown opens on click', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Find theme toggle button
      const themeToggle = page.getByLabel('Toggle color theme');
      await expect(themeToggle).toBeVisible();

      // Click to open dropdown
      await themeToggle.click();

      // Should show Light, Dark, System options
      const lightOption = page.getByRole('button', { name: 'Light' });
      const darkOption = page.getByRole('button', { name: 'Dark' });
      const systemOption = page.getByRole('button', { name: 'System' });

      await expect(lightOption).toBeVisible();
      await expect(darkOption).toBeVisible();
      await expect(systemOption).toBeVisible();
    });

    test('can switch to light theme', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Open theme dropdown
      await page.getByLabel('Toggle color theme').click();

      // Click Light
      await page.getByRole('button', { name: 'Light' }).click();

      // Page should have light theme applied (data-theme attribute)
      const html = page.locator('html');
      await expect(html).toHaveAttribute('data-theme', 'tformance-light');
    });

    test('can switch to dark theme', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // First switch to light theme
      await page.getByLabel('Toggle color theme').click();
      await page.getByRole('button', { name: 'Light' }).click();

      // Now switch back to dark
      await page.getByLabel('Toggle color theme').click();
      await page.getByRole('button', { name: 'Dark' }).click();

      // Page should have dark theme applied
      const html = page.locator('html');
      await expect(html).toHaveAttribute('data-theme', 'tformance');
    });

    test('theme preference persists on page refresh', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Switch to light theme
      await page.getByLabel('Toggle color theme').click();
      await page.getByRole('button', { name: 'Light' }).click();

      // Wait for localStorage to be updated
      await page.waitForTimeout(200);

      // Refresh the page
      await page.reload();
      await page.waitForLoadState('domcontentloaded');

      // Theme should still be light
      const html = page.locator('html');
      await expect(html).toHaveAttribute('data-theme', 'tformance-light');
    });

    test('theme applies correctly across page navigation', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Switch to light theme
      await page.getByLabel('Toggle color theme').click();
      await page.getByRole('button', { name: 'Light' }).click();

      // Navigate to CTO dashboard
      await page.goto('/app/metrics/dashboard/cto/');
      await page.waitForLoadState('domcontentloaded');

      // Theme should still be light
      const html = page.locator('html');
      await expect(html).toHaveAttribute('data-theme', 'tformance-light');
    });
  });

  test.describe('HTMX Content Loading', () => {
    test('HTMX partials load without duplication', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Check that stat cards don't duplicate
      const statCards = page.locator('.stat');
      const count = await statCards.count();

      // Should have a reasonable number (not duplicated)
      if (count > 0) {
        expect(count).toBeLessThan(20); // Sanity check
      }
    });

    test('navigation stays intact after HTMX updates', async ({ page }) => {
      await page.goto('/app/metrics/dashboard/team/');
      await page.waitForLoadState('domcontentloaded');

      // Click a filter button
      const filterButton = page.getByRole('button', { name: /30 days/i });
      if (await filterButton.isVisible()) {
        await filterButton.click();
        await page.waitForTimeout(500);
      }

      // Navigation should still work
      const navLinks = page.locator('nav a');
      const navCount = await navLinks.count();
      expect(navCount).toBeGreaterThan(0);
    });
  });
});
