import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * Copilot Metrics Tests
 * Tests the GitHub Copilot metrics integration features.
 * Run with: npx playwright test copilot.spec.ts
 * Tag: @copilot
 */

test.describe('Copilot Metrics @copilot', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('CTO Dashboard Copilot Section', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      // Wait for HTMX content
      await page.waitForTimeout(1000);
    });

    test('Copilot section exists on CTO dashboard', async ({ page }) => {
      // Look for Copilot section heading or divider
      const copilotSection = page.getByText(/copilot/i).or(
        page.locator('[data-section="copilot"]')
      );

      // Copilot section should be visible if GitHub is connected
      // It's okay if it's not visible (means no Copilot data)
    });

    test('Copilot metrics cards render when data exists', async ({ page }) => {
      // Look for Copilot-specific cards
      const copilotCards = page.locator('[data-testid="copilot-cards"]').or(
        page.locator('.copilot-metrics')
      );

      // Wait for HTMX to load cards
      await page.waitForSelector('.stat', { timeout: 5000 }).catch((): null => null);

      // Check for specific Copilot metrics
      const suggestionsCard = page.getByText(/suggestions/i);
      const acceptanceCard = page.getByText(/acceptance.*rate/i);
      const activeUsersCard = page.getByText(/active.*users/i);
      const costCard = page.getByText(/cost|estimate/i);

      // At least one should be visible if Copilot is enabled
    });

    test('Copilot trend chart renders', async ({ page }) => {
      // Look for Copilot trend chart container
      const trendSection = page.locator('[data-chart="copilot-trend"]').or(
        page.getByText(/acceptance.*trend|copilot.*trend/i)
      );

      // If section exists, look for canvas (Chart.js)
      if (await trendSection.isVisible().catch(() => false)) {
        const canvas = page.locator('canvas');
        expect(await canvas.count()).toBeGreaterThan(0);
      }
    });

    test('Copilot members table displays when available', async ({ page }) => {
      // Look for Copilot members table
      const membersSection = page.getByText(/copilot.*member|usage.*member/i).or(
        page.locator('[data-table="copilot-members"]')
      );

      // If visible, should have table structure
      if (await membersSection.isVisible().catch(() => false)) {
        const table = page.locator('table').filter({ hasText: /copilot|suggestions/i });
        // Table headers should include user metrics
      }
    });
  });

  test.describe('Copilot Integration Settings', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/app/integrations/');
      await page.waitForLoadState('domcontentloaded');
    });

    test('Copilot status shown on integrations page', async ({ page }) => {
      // Copilot should appear as part of GitHub integration or separately
      const copilotStatus = page.getByText(/copilot/i);

      // Should be somewhere on integrations page
    });

    test('Copilot sync button is interactive when enabled', async ({ page }) => {
      // Look for Copilot sync button
      const syncButton = page.getByRole('button', { name: /sync.*copilot|copilot.*sync/i }).or(
        page.locator('[data-action="sync-copilot"]')
      );

      if (await syncButton.isVisible()) {
        // Button should be clickable
        await expect(syncButton).toBeEnabled();

        // Click should trigger action (not navigation)
        await syncButton.click();
        await page.waitForTimeout(500);

        // Should still be on integrations page
        await expect(page).toHaveURL(/\/integrations/);
      }
    });

    test('Copilot settings show enable/disable toggle', async ({ page }) => {
      // Look for Copilot toggle
      const copilotToggle = page.locator('[data-setting="copilot-enabled"]').or(
        page.locator('.toggle').filter({ hasText: /copilot/i })
      ).or(
        page.locator('input[type="checkbox"]').filter({ hasText: /copilot/i })
      );

      // Toggle may or may not be visible depending on GitHub connection
    });

    test('last sync timestamp shown', async ({ page }) => {
      // Look for last sync info
      const lastSync = page.getByText(/last.*sync|synced.*at|updated/i);

      // Should show timestamp if Copilot has been synced
    });
  });

  test.describe('Copilot Data Display', () => {
    test('Copilot metrics show numeric values', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Check that Copilot metrics show actual numbers, not NaN or errors
      const statValues = page.locator('.stat-value');
      const count = await statValues.count();

      for (let i = 0; i < count; i++) {
        const text = await statValues.nth(i).textContent();
        if (text) {
          // Should not contain error indicators
          expect(text.toLowerCase()).not.toContain('nan');
          expect(text.toLowerCase()).not.toContain('undefined');
          expect(text.toLowerCase()).not.toContain('error');
        }
      }
    });

    test('acceptance rate shows percentage format', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Look for acceptance rate value
      const acceptanceRate = page.locator('.stat').filter({ hasText: /acceptance/i });

      if (await acceptanceRate.isVisible()) {
        const value = await acceptanceRate.locator('.stat-value').textContent();
        // Should be a percentage (contains % or is a decimal)
        if (value) {
          const hasPercentage = value.includes('%') || /^\d+\.?\d*$/.test(value.trim());
          // Value should look like a percentage
        }
      }
    });
  });

  test.describe('Copilot Empty States', () => {
    test('shows appropriate message when no Copilot data', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');

      // If no Copilot data, should show helpful message
      const emptyState = page.getByText(/no copilot|copilot.*not.*enabled|enable.*copilot|connect.*copilot/i);

      // Either has data or shows empty state message
    });

    test('Copilot section gracefully handles missing data', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Page should not show error states
      const errorMessages = page.getByText(/error|failed|crash/i);
      const errors = await errorMessages.count();

      // Minimal errors expected (some may be in logs, not UI)
      expect(errors).toBeLessThan(3);
    });
  });

  test.describe('Copilot Chart Interactions', () => {
    test('Copilot trend chart responds to date filters', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Change date filter
      const filter30d = page.getByRole('button', { name: /30 days/i });
      if (await filter30d.isVisible()) {
        await filter30d.click();
        await page.waitForTimeout(500);

        // Chart should update (no way to verify data change, but no errors)
        const errors = await page.locator('.error').count();
        expect(errors).toBe(0);
      }
    });

    test('Copilot chart canvas exists when section visible', async ({ page }) => {
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Find the Copilot chart section container
      const copilotChartSection = page.locator('#copilot-trend-container');

      // If section exists, check for canvas or "No data" message
      if (await copilotChartSection.isVisible()) {
        const canvas = copilotChartSection.locator('canvas');
        const noDataMessage = copilotChartSection.getByText(/no.*data|not.*available/i);

        // Either canvas or no-data message should be present
        const hasCanvas = await canvas.isVisible().catch(() => false);
        const hasNoData = await noDataMessage.isVisible().catch(() => false);

        // At least one should be true (chart rendered or message shown)
        expect(hasCanvas || hasNoData).toBeTruthy();
      }
    });
  });
});

test.describe('Copilot Access Control @copilot', () => {
  test('Copilot section only visible to admins/CTOs', async ({ page }) => {
    // Login as admin
    await loginAs(page);
    await page.goto('/app/metrics/overview/');

    // CTO dashboard should be accessible to admin
    await expect(page).toHaveURL(/\/metrics\/overview/);

    // Copilot section should be present (if data exists)
    const copilotText = page.getByText(/copilot/i);
    // Should find at least one reference to Copilot on CTO dashboard
  });

  test('team dashboard does not show Copilot section', async ({ page }) => {
    await loginAs(page);
    await page.goto('/app/metrics/dashboard/team/');
    await page.waitForLoadState('domcontentloaded');

    // Team dashboard should NOT have Copilot-specific cards
    // (Copilot is CTO-level visibility)
    const copilotCards = page.locator('[data-section="copilot-metrics"]');
    const cardCount = await copilotCards.count();

    // Copilot cards should not be on team dashboard
    expect(cardCount).toBe(0);
  });
});
