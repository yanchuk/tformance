import { test, expect } from '@playwright/test';

/**
 * Trends Charts Tests
 * Run with: npx playwright test trends-charts.spec.ts
 * Tag: @trends-charts
 *
 * Tests for validating the Trends page charts rendering:
 * - PR Types Over Time chart should render as full-width stacked bar
 * - Technology Breakdown chart should render as full-width stacked bar
 * - Industry Benchmark panel should load without 500 error
 *
 * Issue: https://github.com/tformance/dev/active/trends-charts-fix
 */

test.describe('Trends Charts Tests @trends-charts', () => {
  // Login before each test - supports both email and GitHub-only auth modes
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.waitForLoadState('domcontentloaded');

    // Check if email auth is enabled (AUTH_MODE=all)
    const emailField = page.getByRole('textbox', { name: 'Email' });
    const hasEmailAuth = await emailField.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasEmailAuth) {
      // Email/password login
      await emailField.fill('admin@example.com');
      await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
      await page.getByRole('button', { name: 'Sign In' }).click();
      await expect(page).toHaveURL(/\/app/);
    } else {
      // GitHub-only mode - skip tests that require authentication
      test.skip(true, 'Email auth not enabled (AUTH_MODE=github_only). Run with AUTH_MODE=all for full test coverage.');
    }
  });

  test.describe('PR Types Over Time Chart', () => {
    test('PR Types chart canvas renders with actual chart content', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000); // Allow HTMX to load charts

      // Scroll to PR type chart section
      await page.locator('#pr-type-chart-container').scrollIntoViewIfNeeded();
      await page.waitForTimeout(1500);

      // Canvas element should exist
      const canvas = page.locator('#pr-type-chart');
      await expect(canvas).toBeAttached();

      // Chart.js creates a chart instance - verify it's actually rendering
      // by checking if canvas has non-zero dimensions and content
      const chartRendered = await page.evaluate(() => {
        const canvas = document.getElementById('pr-type-chart') as HTMLCanvasElement;
        if (!canvas) return { exists: false, hasContent: false, width: 0, height: 0 };

        // Check if canvas has actual dimensions
        const width = canvas.width;
        const height = canvas.height;

        // Check if Chart.js instance is attached (Chart.js stores it on the canvas)
        const chartInstance = (window as any).Chart?.getChart?.(canvas);

        return {
          exists: true,
          hasContent: !!chartInstance,
          width,
          height,
          hasChartInstance: !!chartInstance
        };
      });

      expect(chartRendered.exists).toBe(true);
      expect(chartRendered.width).toBeGreaterThan(0);
      expect(chartRendered.height).toBeGreaterThan(0);
      // This assertion will FAIL if chart is not rendering (bug exists)
      expect(chartRendered.hasChartInstance).toBe(true);
    });

    test('PR Types chart should be full-width (not side-by-side with Tech chart)', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Get the PR type chart container's parent grid
      const prTypeContainer = page.locator('#pr-type-chart-container');
      await prTypeContainer.scrollIntoViewIfNeeded();

      // Check that PR Type chart container is NOT in a 2-column grid
      // It should be full-width like the main trend chart
      const parentClasses = await prTypeContainer.evaluate((el) => {
        const parent = el.closest('.grid');
        return parent?.className || '';
      });

      // Should NOT have lg:grid-cols-2 (side-by-side layout)
      expect(parentClasses).not.toContain('lg:grid-cols-2');
    });
  });

  test.describe('Technology Breakdown Chart', () => {
    test('Tech Breakdown chart canvas renders with actual chart content', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000);

      // Scroll to tech chart section
      await page.locator('#tech-chart-container').scrollIntoViewIfNeeded();
      await page.waitForTimeout(1500);

      // Canvas element should exist
      const canvas = page.locator('#tech-chart');
      await expect(canvas).toBeAttached();

      // Verify Chart.js instance is actually rendering
      const chartRendered = await page.evaluate(() => {
        const canvas = document.getElementById('tech-chart') as HTMLCanvasElement;
        if (!canvas) return { exists: false, hasContent: false, width: 0, height: 0 };

        const width = canvas.width;
        const height = canvas.height;
        const chartInstance = (window as any).Chart?.getChart?.(canvas);

        return {
          exists: true,
          hasContent: !!chartInstance,
          width,
          height,
          hasChartInstance: !!chartInstance
        };
      });

      expect(chartRendered.exists).toBe(true);
      expect(chartRendered.width).toBeGreaterThan(0);
      expect(chartRendered.height).toBeGreaterThan(0);
      // This assertion will FAIL if chart is not rendering (bug exists)
      expect(chartRendered.hasChartInstance).toBe(true);
    });

    test('Tech Breakdown chart should be full-width (not side-by-side with PR Types)', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      const techContainer = page.locator('#tech-chart-container');
      await techContainer.scrollIntoViewIfNeeded();

      // Check that Tech chart container is NOT in a 2-column grid
      const parentClasses = await techContainer.evaluate((el) => {
        const parent = el.closest('.grid');
        return parent?.className || '';
      });

      // Should NOT have lg:grid-cols-2 (side-by-side layout)
      expect(parentClasses).not.toContain('lg:grid-cols-2');
    });
  });

  test.describe('Industry Benchmark Panel', () => {
    test('Benchmark panel loads without 500 error', async ({ page }) => {
      // Listen for network errors
      const errors: string[] = [];
      page.on('response', (response) => {
        if (response.url().includes('/benchmark/') && response.status() >= 500) {
          errors.push(`${response.status()} from ${response.url()}`);
        }
      });

      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000); // Allow all HTMX panels to load

      // Should have NO 500 errors from benchmark endpoints
      expect(errors).toHaveLength(0);
    });

    test('Benchmark panel content loads successfully', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000);

      // Industry Benchmark heading should be visible
      await expect(page.getByRole('heading', { name: 'Industry Benchmark' })).toBeVisible();

      // Should NOT show loading skeleton after data loads
      const loadingSkeletons = page.locator('.animate-pulse').filter({
        has: page.locator('[id*="benchmark"]')
      });

      // Wait for loading to complete - skeleton should disappear
      await expect(loadingSkeletons).toHaveCount(0);
    });
  });

  test.describe('Chart Height and Styling', () => {
    test('PR Types chart has adequate height (320px like main chart)', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      const prTypeChart = page.locator('#pr-type-chart');
      await prTypeChart.scrollIntoViewIfNeeded();

      const box = await prTypeChart.boundingBox();
      expect(box).not.toBeNull();
      // Should be at least 300px tall (target is 320px)
      expect(box!.height).toBeGreaterThanOrEqual(300);
    });

    test('Tech Breakdown chart has adequate height (320px like main chart)', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      const techChart = page.locator('#tech-chart');
      await techChart.scrollIntoViewIfNeeded();

      const box = await techChart.boundingBox();
      expect(box).not.toBeNull();
      // Should be at least 300px tall (target is 320px)
      expect(box!.height).toBeGreaterThanOrEqual(300);
    });
  });

  test.describe('Wide Trend Chart HTMX Integration', () => {
    test('Wide trend chart renders after initial page load', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000);

      // Main trend chart canvas should exist and have Chart.js instance
      const canvas = page.locator('#trend-chart');
      await expect(canvas).toBeAttached();

      const chartRendered = await page.evaluate(() => {
        const canvas = document.getElementById('trend-chart') as HTMLCanvasElement;
        if (!canvas) return { exists: false, hasChart: false };
        const chartInstance = (window as any).Chart?.getChart?.(canvas);
        return {
          exists: true,
          hasChart: !!chartInstance,
          width: canvas.width,
          height: canvas.height,
        };
      });

      expect(chartRendered.exists).toBe(true);
      expect(chartRendered.hasChart).toBe(true);
    });

    test('Wide trend chart re-renders after granularity change (HTMX swap)', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000);

      // Verify initial chart exists
      const initialChart = await page.evaluate(() => {
        const canvas = document.getElementById('trend-chart') as HTMLCanvasElement;
        return canvas ? !!(window as any).Chart?.getChart?.(canvas) : false;
      });
      expect(initialChart).toBe(true);

      // Find and click granularity dropdown/button to trigger HTMX swap
      // The granularity selector should be in the trends page
      const granularitySelect = page.locator('[data-granularity], select[name="granularity"], #granularity-select').first();

      if (await granularitySelect.isVisible()) {
        // Change granularity - this should trigger HTMX swap
        await granularitySelect.selectOption({ index: 1 });
      } else {
        // If no dropdown, look for granularity buttons (weekly/monthly)
        const monthlyBtn = page.getByRole('button', { name: /monthly/i }).first();
        if (await monthlyBtn.isVisible()) {
          await monthlyBtn.click();
        }
      }

      // Wait for HTMX swap to complete
      await page.waitForTimeout(2000);

      // After HTMX swap, chart should still render (this is the critical test)
      const chartAfterSwap = await page.evaluate(() => {
        const canvas = document.getElementById('trend-chart') as HTMLCanvasElement;
        if (!canvas) return { exists: false, hasChart: false };
        const chartInstance = (window as any).Chart?.getChart?.(canvas);
        return {
          exists: true,
          hasChart: !!chartInstance,
        };
      });

      // This assertion will FAIL if inline script doesn't execute after HTMX swap
      expect(chartAfterSwap.exists).toBe(true);
      expect(chartAfterSwap.hasChart).toBe(true);
    });

    test('No inline script errors in wide chart template', async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000);

      // Filter for chart-related errors
      const chartErrors = consoleErrors.filter(
        (err) =>
          err.includes('trend') ||
          err.includes('chart') ||
          err.includes('Chart') ||
          err.includes('canvas')
      );

      // Should have no chart-related errors
      expect(chartErrors).toHaveLength(0);
    });
  });

  test.describe('No Console Errors', () => {
    test('Trends page loads without JavaScript errors', async ({ page }) => {
      const consoleErrors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          consoleErrors.push(msg.text());
        }
      });

      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(3000);

      // Filter out expected/known errors
      const unexpectedErrors = consoleErrors.filter(
        (err) =>
          !err.includes('favicon') &&
          !err.includes('404') &&
          !err.includes('posthog') && // PostHog CSP errors are expected in dev
          !err.includes('Content Security Policy')
      );

      expect(unexpectedErrors).toHaveLength(0);
    });
  });
});
