import { test, expect } from '@playwright/test';

/**
 * App Navigation Tests - Marketing vs App Section Separation
 * Run with: npx playwright test app-navigation.spec.ts
 *
 * These tests verify that the authenticated app section (/app/)
 * does NOT show marketing content (Features, Pricing, competitor comparisons)
 * while marketing pages DO show this content.
 */

test.describe('App Header - No Marketing Links', () => {
  test.beforeEach(async ({ page }) => {
    // Login to access app section
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test('app header does NOT contain Features link', async ({ page }) => {
    // The header navbar should not have a Features dropdown or link
    const navbar = page.locator('.navbar');
    await expect(navbar.getByRole('button', { name: 'Features' })).not.toBeVisible();
    await expect(navbar.getByRole('link', { name: 'Features' })).not.toBeVisible();
  });

  test('app header does NOT contain Pricing link', async ({ page }) => {
    const navbar = page.locator('.navbar');
    await expect(navbar.getByRole('link', { name: 'Pricing' })).not.toBeVisible();
  });

  test('app header does NOT contain Blog link', async ({ page }) => {
    const navbar = page.locator('.navbar');
    await expect(navbar.getByRole('link', { name: 'Blog' })).not.toBeVisible();
  });

  test('app header does NOT contain Compare Tools link', async ({ page }) => {
    const navbar = page.locator('.navbar');
    await expect(navbar.getByRole('link', { name: 'Compare Tools' })).not.toBeVisible();
  });

  test('app header logo links to dashboard', async ({ page }) => {
    // Logo should link to /app/ (dashboard), not / (home)
    const logoLink = page.locator('.navbar a').filter({ hasText: 'Tformance' }).first();
    const href = await logoLink.getAttribute('href');
    expect(href).toContain('/app');
  });
});

test.describe('App Footer - No Competitor Comparisons', () => {
  test.beforeEach(async ({ page }) => {
    // Login to access app section
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test('app footer does NOT contain competitor comparison links', async ({ page }) => {
    const footer = page.locator('footer');

    // None of these competitor links should be present
    await expect(footer.getByRole('link', { name: /vs LinearB/i })).not.toBeVisible();
    await expect(footer.getByRole('link', { name: /vs Jellyfish/i })).not.toBeVisible();
    await expect(footer.getByRole('link', { name: /vs Swarmia/i })).not.toBeVisible();
    await expect(footer.getByRole('link', { name: /All Comparisons/i })).not.toBeVisible();
  });

  test('app footer DOES contain legal links', async ({ page }) => {
    const footer = page.locator('footer');

    // These should still be present
    await expect(footer.getByRole('link', { name: 'Terms' })).toBeVisible();
    await expect(footer.getByRole('link', { name: 'Privacy' })).toBeVisible();
    await expect(footer.getByRole('link', { name: 'Contact' })).toBeVisible();
  });

  test('app footer DOES contain dark mode toggle', async ({ page }) => {
    const footer = page.locator('footer');

    // Dark mode toggle uses a details.dropdown with a sun/moon icon button
    await expect(footer.locator('details.dropdown')).toBeVisible();
  });
});

test.describe('Marketing Pages - Full Navigation Present', () => {
  // Desktop-only tests (marketing nav is hidden on mobile/tablet)
  test('homepage header HAS Features dropdown', async ({ page, viewport }) => {
    // Skip on mobile/tablet viewports where nav is in hamburger menu
    test.skip(!!viewport && viewport.width < 1024, 'Desktop nav hidden on mobile');

    await page.goto('/');
    const navbar = page.locator('.navbar');

    // Marketing page should have Features button/dropdown
    await expect(navbar.getByRole('button', { name: 'Features' })).toBeVisible();
  });

  test('homepage header HAS Pricing link', async ({ page, viewport }) => {
    // Skip on mobile/tablet viewports where nav is in hamburger menu
    test.skip(!!viewport && viewport.width < 1024, 'Desktop nav hidden on mobile');

    await page.goto('/');
    const navbar = page.locator('.navbar');

    await expect(navbar.getByRole('link', { name: 'Pricing' })).toBeVisible();
  });

  test('homepage footer HAS competitor comparison links', async ({ page }) => {
    await page.goto('/');
    const footer = page.locator('footer');

    // At least one competitor link should be visible
    await expect(footer.getByRole('link', { name: /vs LinearB/i })).toBeVisible();
    await expect(footer.getByRole('link', { name: /All Comparisons/i })).toBeVisible();
  });

  test('homepage logo links to home page', async ({ page }) => {
    await page.goto('/');

    // Logo should link to / (home)
    const logoLink = page.locator('.navbar a').filter({ hasText: 'Tformance' }).first();
    const href = await logoLink.getAttribute('href');
    expect(href).toBe('/');
  });
});
