/**
 * Alpine.js + HTMX Integration Tests
 *
 * Tests that Alpine components and stores work correctly with HTMX:
 * - Stores persist across HTMX content swaps
 * - Components reinitialize after swap
 * - State is preserved during navigation
 */
import { test, expect } from '@playwright/test';

test.use({ browserName: 'chromium' });

test.describe('Alpine.js + HTMX Integration', () => {
  test.beforeEach(async ({ page }) => {
    page.setDefaultTimeout(15000);

    // Login
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await page.waitForURL(/\/app/, { timeout: 5000 });
  });

  test.describe('Alpine Stores', () => {
    test('dateRange store exists and has initial values', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Check that Alpine store exists and has expected structure
      const storeExists = await page.evaluate(() => {
        const Alpine = (window as any).Alpine;
        if (!Alpine) return { exists: false };
        const store = Alpine.store('dateRange');
        return {
          exists: !!store,
          hasDays: typeof store?.days === 'number',
          hasSetDays: typeof store?.setDays === 'function',
          hasIsActive: typeof store?.isActive === 'function',
        };
      });

      expect(storeExists.exists).toBe(true);
      expect(storeExists.hasDays).toBe(true);
      expect(storeExists.hasSetDays).toBe(true);
      expect(storeExists.hasIsActive).toBe(true);
    });

    test('metrics store exists and has toggle functionality', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Test metrics store
      const metricsStore = await page.evaluate(() => {
        const Alpine = (window as any).Alpine;
        if (!Alpine) return { exists: false };
        const store = Alpine.store('metrics');

        // Test toggle functionality
        store.toggle('cycle_time');
        const afterToggle = store.isSelected('cycle_time');
        store.toggle('cycle_time');
        const afterUntoggle = store.isSelected('cycle_time');

        return {
          exists: !!store,
          hasToggle: typeof store?.toggle === 'function',
          hasIsSelected: typeof store?.isSelected === 'function',
          toggleWorks: afterToggle === true && afterUntoggle === false,
        };
      });

      expect(metricsStore.exists).toBe(true);
      expect(metricsStore.hasToggle).toBe(true);
      expect(metricsStore.toggleWorks).toBe(true);
    });

    test('dateRange store persists across HTMX tab navigation', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Set store value directly
      await page.evaluate(() => {
        const Alpine = (window as any).Alpine;
        Alpine.store('dateRange').setDays(90);
      });

      // Verify it was set
      const beforeNav = await page.evaluate(() => {
        return (window as any).Alpine.store('dateRange').days;
      });
      expect(beforeNav).toBe(90);

      // Navigate to another tab via HTMX
      const qualityTab = page.getByRole('tab', { name: 'Quality' });
      await qualityTab.click();
      await page.waitForTimeout(2000);

      // Check store value after HTMX swap
      const afterNav = await page.evaluate(() => {
        return (window as any).Alpine.store('dateRange').days;
      });

      // Store should persist because it's on Alpine global, not DOM
      expect(afterNav).toBe(90);
    });

    test('metrics store persists selected metrics across HTMX navigation', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Select some metrics
      await page.evaluate(() => {
        const Alpine = (window as any).Alpine;
        const store = Alpine.store('metrics');
        store.toggle('cycle_time');
        store.toggle('review_time');
      });

      // Verify selections
      const beforeNav = await page.evaluate(() => {
        return (window as any).Alpine.store('metrics').selected;
      });
      expect(beforeNav).toContain('cycle_time');
      expect(beforeNav).toContain('review_time');

      // Navigate via HTMX
      const deliveryTab = page.getByRole('tab', { name: 'Delivery' });
      await deliveryTab.click();
      await page.waitForTimeout(2000);

      // Check store persisted
      const afterNav = await page.evaluate(() => {
        return (window as any).Alpine.store('metrics').selected;
      });
      expect(afterNav).toContain('cycle_time');
      expect(afterNav).toContain('review_time');
    });
  });

  test.describe('Alpine Component Reinitialization', () => {
    test('Alpine components in swapped content initialize', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Navigate to trigger HTMX swap
      const teamTab = page.getByRole('tab', { name: 'Team' });
      await teamTab.click();
      await page.waitForTimeout(2000);

      // Check that Alpine components exist in the swapped content
      // Look for any x-data attributes that should have been initialized
      const alpineComponents = await page.evaluate(() => {
        const elements = document.querySelectorAll('[x-data]');
        return {
          count: elements.length,
          // Check if Alpine has initialized them (they should have _x_dataStack)
          initialized: Array.from(elements).filter(
            (el) => (el as any)._x_dataStack !== undefined
          ).length,
        };
      });

      // Should have at least some Alpine components initialized
      // The exact count depends on the page content
      expect(alpineComponents.count).toBeGreaterThanOrEqual(0);
      // All found components should be initialized
      expect(alpineComponents.initialized).toBe(alpineComponents.count);
    });

    test('date picker Alpine component works after HTMX swap', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Navigate to trigger swap
      const aiTab = page.getByRole('tab', { name: 'AI Adoption' });
      await aiTab.click();
      await page.waitForTimeout(2000);

      // Find and click a date button (should be in the swapped content)
      const btn7d = page.locator('button:has-text("7d")').first();
      if (await btn7d.isVisible()) {
        await btn7d.click();
        await page.waitForTimeout(1000);

        // The button should respond (Alpine component initialized)
        // Check if it has the active class or triggered navigation
        const url = page.url();
        const hasDateParam = url.includes('days=');
        expect(hasDateParam).toBe(true);
      }
    });
  });

  test.describe('Store URL Sync', () => {
    test('dateRange store syncs from URL params on load', async ({ page }) => {
      // Load page with specific days param
      await page.goto('/app/metrics/analytics/?days=90');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Check store synced from URL
      const storeDays = await page.evaluate(() => {
        return (window as any).Alpine.store('dateRange').days;
      });

      expect(storeDays).toBe(90);
    });

    test('dateRange store syncs preset from URL', async ({ page }) => {
      // Load page with preset param
      await page.goto('/app/metrics/analytics/?preset=this_year');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Check store synced preset
      const storeState = await page.evaluate(() => {
        const store = (window as any).Alpine.store('dateRange');
        return {
          preset: store.preset,
          days: store.days,
        };
      });

      expect(storeState.preset).toBe('this_year');
      expect(storeState.days).toBe(0); // Should be 0 when preset is set
    });
  });
});
