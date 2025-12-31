import { test, expect, Page } from '@playwright/test';

/**
 * Personal Notes E2E Tests
 * Run with: npx playwright test notes.spec.ts
 * Tag: @notes
 *
 * Tests for the Personal PR Notes feature allowing CTOs to add
 * private notes to PRs during weekly reviews.
 *
 * Note: These tests run only on desktop browsers (chromium, firefox, webkit)
 * since mobile/tablet have different navigation (hamburger menu).
 */

/**
 * Wait for page navigation to complete.
 */
async function waitForPageLoad(page: Page, timeout = 5000): Promise<void> {
  await page.waitForLoadState('domcontentloaded', { timeout });
  await page.waitForFunction(
    () => typeof window !== 'undefined' && document.readyState === 'complete',
    { timeout }
  );
}

test.describe('Personal Notes Tests @notes', () => {
  // Skip mobile and tablet devices - sidebar navigation is different
  test.beforeEach(async ({ page }, testInfo) => {
    const projectName = testInfo.project.name;
    if (projectName.includes('Mobile') || projectName.includes('Tablet')) {
      test.skip();
    }

    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('My Notes Page', () => {
    test('my notes page is accessible', async ({ page }) => {
      await page.goto('/app/notes/');
      await waitForPageLoad(page);

      // Should have page title
      await expect(page.getByRole('heading', { name: 'My Notes' })).toBeVisible();
    });

    test('my notes page shows filter dropdowns', async ({ page }) => {
      await page.goto('/app/notes/');
      await waitForPageLoad(page);

      // Flag and status filter dropdowns should be visible
      const flagFilter = page.locator('select').first();
      const statusFilter = page.locator('select').nth(1);

      await expect(flagFilter).toBeVisible();
      await expect(statusFilter).toBeVisible();
    });

    test('flag filter has all options', async ({ page }) => {
      await page.goto('/app/notes/');
      await waitForPageLoad(page);

      const flagFilter = page.locator('select').first();

      // Verify key flag options exist
      await expect(flagFilter.locator('option', { hasText: 'All Flags' })).toHaveCount(1);
      await expect(flagFilter.locator('option', { hasText: 'False Positive' })).toHaveCount(1);
      await expect(flagFilter.locator('option', { hasText: 'Review Later' })).toHaveCount(1);
      await expect(flagFilter.locator('option', { hasText: 'Important' })).toHaveCount(1);
      await expect(flagFilter.locator('option', { hasText: 'Concern' })).toHaveCount(1);
    });

    test('status filter has open and resolved options', async ({ page }) => {
      await page.goto('/app/notes/');
      await waitForPageLoad(page);

      const statusFilter = page.locator('select').nth(1);

      // Verify status options exist
      await expect(statusFilter.locator('option', { hasText: 'All Status' })).toHaveCount(1);
      await expect(statusFilter.locator('option', { hasText: 'Open' })).toHaveCount(1);
      await expect(statusFilter.locator('option', { hasText: 'Resolved' })).toHaveCount(1);
    });

    test('empty state shows when no notes', async ({ page }) => {
      // Filter by a flag that likely has no notes
      await page.goto('/app/notes/?flag=concern');
      await waitForPageLoad(page);

      // Should show empty state message
      await expect(page.getByText('No notes yet')).toBeVisible();
    });
  });

  test.describe('Note Form', () => {
    test('note form is accessible from PR list', async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await waitForPageLoad(page);

      // Click the expand button on the second PR row (first might have notes from other tests)
      const secondPrTbody = page.locator('tbody').nth(1);
      const expandButton = secondPrTbody.getByRole('button', { name: 'Click to expand details' });
      await expandButton.click();

      // Wait for the expanded row's note link to appear (Add Note or Edit Note)
      // Use secondPrTbody to scope the search to the expanded row
      const noteLink = secondPrTbody.getByRole('link', { name: /Add Note|Edit Note/ });
      await expect(noteLink).toBeVisible({ timeout: 5000 });
    });

    test('clicking note link navigates to note form', async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await waitForPageLoad(page);

      // Click the expand button on the second PR row
      const expandButton = page.locator('tbody').nth(1).getByRole('button', { name: 'Click to expand details' });
      await expandButton.click();

      // Wait for note link (Add Note or Edit Note) to appear
      const noteLink = page.getByRole('link', { name: /Add Note|Edit Note/ });
      await expect(noteLink).toBeVisible({ timeout: 5000 });

      // Click the note link
      await noteLink.click();

      // Should be on note form page
      await expect(page).toHaveURL(/\/app\/notes\/pr\/\d+\//);
      await expect(page.getByRole('heading', { name: /Add Note|Edit Note/ })).toBeVisible();
    });

    test('note form has all required fields', async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await waitForPageLoad(page);

      // Click the expand button on the second PR row
      const expandButton = page.locator('tbody').nth(1).getByRole('button', { name: 'Click to expand details' });
      await expandButton.click();

      // Wait for note link to appear
      const noteLink = page.getByRole('link', { name: /Add Note|Edit Note/ });
      await expect(noteLink).toBeVisible({ timeout: 5000 });
      await noteLink.click();

      // Should have note textarea
      await expect(page.getByRole('textbox', { name: /observations/ })).toBeVisible();

      // Should have flag dropdown
      const flagDropdown = page.locator('select#id_flag');
      await expect(flagDropdown).toBeVisible();

      // Should have Cancel and Save/Add Note buttons
      await expect(page.getByRole('link', { name: 'Cancel' })).toBeVisible();
      const submitButton = page.getByRole('button', { name: /Add Note|Save/ });
      await expect(submitButton).toBeVisible();
    });

    test('can submit a note', async ({ page }) => {
      await page.goto('/app/pull-requests/');
      await waitForPageLoad(page);

      // Click the expand button on the second PR row
      const expandButton = page.locator('tbody').nth(1).getByRole('button', { name: 'Click to expand details' });
      await expandButton.click();

      // Wait for note link to appear
      const noteLink = page.getByRole('link', { name: /Add Note|Edit Note/ });
      await expect(noteLink).toBeVisible({ timeout: 5000 });
      await noteLink.click();

      // Fill in the note
      await page.getByRole('textbox', { name: /observations/ }).fill('E2E test note - flagging for review');
      await page.locator('select#id_flag').selectOption('review_later');

      // Submit the form
      const submitButton = page.getByRole('button', { name: /Add Note|Save/ });
      await submitButton.click();

      // Should redirect to PR list
      await expect(page).toHaveURL(/\/app\/.*pull-requests/);
    });
  });

  test.describe('Navigation', () => {
    test('my notes link is in sidebar', async ({ page }) => {
      await page.goto('/app/');
      await waitForPageLoad(page);

      // Should have My Notes link in navigation
      await expect(page.getByRole('link', { name: 'My Notes' })).toBeVisible();
    });

    test('clicking my notes navigates to notes page', async ({ page }) => {
      await page.goto('/app/');
      await waitForPageLoad(page);

      // Click My Notes link
      await page.getByRole('link', { name: 'My Notes' }).click();

      // Should navigate to notes page
      await expect(page).toHaveURL('/app/notes/');
      await expect(page.getByRole('heading', { name: 'My Notes' })).toBeVisible();
    });
  });
});
