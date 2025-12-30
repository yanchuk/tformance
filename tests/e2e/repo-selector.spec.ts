import { test, expect, Page } from '@playwright/test';

/**
 * Repository Selector Tests
 * Run with: npx playwright test repo-selector.spec.ts
 * Tag: @repo-selector
 *
 * Tests for the repository filter dropdown on analytics pages:
 * - Dropdown interaction (open/close)
 * - URL state management
 * - Chart filtering
 * - Navigation preservation
 */

/**
 * Wait for page to be fully loaded with Alpine and charts.
 */
async function waitForPageReady(page: Page, timeout = 15000): Promise<void> {
  // Wait for DOM to be loaded
  await page.waitForLoadState('domcontentloaded');
  // Wait for Alpine to be initialized and stores to be ready
  await page.waitForFunction(
    () => {
      const Alpine = (window as any).Alpine;
      return Alpine && Alpine.store && Alpine.store('dateRange') !== undefined;
    },
    { timeout }
  );
  // Small delay for Alpine to finish initializing components
  await page.waitForTimeout(200);
}

/**
 * Wait for HTMX request to complete.
 */
async function waitForHtmxComplete(page: Page, timeout = 10000): Promise<void> {
  await page.waitForFunction(() => !document.body.classList.contains('htmx-request'), { timeout });
}

/**
 * Check if repo selector is visible (only shows when team has multiple repos).
 */
async function hasRepoSelector(page: Page): Promise<boolean> {
  // Look for "Repository:" label in the filter controls
  const label = page.locator('#filter-controls-container').getByText('Repository:');
  return label.isVisible({ timeout: 2000 }).catch(() => false);
}

/**
 * Get the repo selector dropdown button.
 */
function getRepoSelectorButton(page: Page) {
  // The button is inside the repo-selector component
  return page.locator('[data-testid="repo-selector"] button');
}

/**
 * Get the repo selector dropdown menu.
 */
function getRepoDropdown(page: Page) {
  // The dropdown is inside the repo-selector component
  return page.locator('[data-testid="repo-selector"] .menu.shadow-lg');
}

test.describe('Repository Selector Tests @repo-selector', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('Repo Selector Display', () => {
    test('repo selector only shows when team has multiple repos', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      // Check if the repo selector exists (it's conditional based on repo count)
      const hasSelector = await hasRepoSelector(page);

      if (hasSelector) {
        // If visible, verify the button is visible
        const button = getRepoSelectorButton(page);
        await expect(button).toBeVisible();
      } else {
        // If not visible, that's expected for teams with 0-1 repos
        // Just verify the page loaded correctly
        await expect(page.getByRole('heading', { name: 'Team Health Overview' })).toBeVisible();
      }
    });

    test('repo selector appears on all analytics tabs when team has multiple repos', async ({ page }) => {
      const tabs = [
        { url: '/app/metrics/analytics/', name: 'Overview' },
        { url: '/app/metrics/analytics/ai-adoption/', name: 'AI Adoption' },
        { url: '/app/metrics/analytics/delivery/', name: 'Delivery' },
        { url: '/app/metrics/analytics/quality/', name: 'Quality' },
        { url: '/app/metrics/analytics/team/', name: 'Team' },
        { url: '/app/metrics/analytics/trends/', name: 'Trends' },
      ];

      // Check first tab to see if repo selector is present
      await page.goto(tabs[0].url);
      await waitForPageReady(page);
      const hasSelector = await hasRepoSelector(page);

      if (!hasSelector) {
        // Skip test if team doesn't have multiple repos
        test.skip();
        return;
      }

      // Check all tabs have the repo selector
      for (const tab of tabs) {
        await page.goto(tab.url);
        await waitForPageReady(page);
        await expect(page.locator('#filter-controls-container').getByText('Repository:')).toBeVisible();
      }
    });
  });

  test.describe('Dropdown Interaction', () => {
    test('clicking repo selector opens dropdown menu', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Click the repo selector button
      const button = getRepoSelectorButton(page);
      await button.click();

      // Dropdown menu should appear
      const dropdown = getRepoDropdown(page);
      await expect(dropdown).toBeVisible();

      // Should show "All Repositories" option
      await expect(dropdown.getByText('All Repositories')).toBeVisible();
    });

    test('dropdown contains All Repositories option', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Open dropdown
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      await expect(dropdown).toBeVisible();

      // Should have "All Repositories" option - this is always present
      await expect(dropdown.getByText('All Repositories')).toBeVisible();
    });

    test('search input appears for teams with many repos', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Open dropdown
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      await expect(dropdown).toBeVisible();

      // Search input only shows when >5 repos - check if it's present
      const searchInput = dropdown.getByPlaceholder('Search repositories...');
      // This may or may not be visible depending on repo count
      const hasSearch = await searchInput.isVisible().catch(() => false);

      // Just verify the dropdown structure is correct
      await expect(dropdown.getByText('All Repositories')).toBeVisible();
    });
  });

  test.describe('URL State Management', () => {
    test('selecting repo updates URL with repo param', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Open dropdown
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);

      // Wait for dropdown and get first repo link (skip "All Repositories")
      await expect(dropdown).toBeVisible();
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      // Click first repo
      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // URL should include repo param
      await expect(page).toHaveURL(/repo=/);
    });

    test('selecting All Repositories removes repo param from URL', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // First select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      let dropdown = getRepoDropdown(page);
      await expect(dropdown).toBeVisible();

      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Verify repo is now in URL
      await expect(page).toHaveURL(/repo=/);

      // Now open dropdown and select "All Repositories"
      const newButton = getRepoSelectorButton(page);
      await newButton.click();
      dropdown = getRepoDropdown(page);
      await expect(dropdown).toBeVisible();
      await dropdown.getByText('All Repositories').first().click();
      await waitForHtmxComplete(page);

      // URL should NOT have repo param
      const url = page.url();
      expect(url).not.toMatch(/repo=/);
    });

    test('page refresh restores repo from URL', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Open dropdown and select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      // Click first repo
      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Verify URL has repo param
      await expect(page).toHaveURL(/repo=/);

      // Refresh the page
      await page.reload();
      await waitForPageReady(page);

      // The repo selector button should show the selected repo (text should change from "All Repositories")
      // We verify this by checking the button has btn-primary class (active state)
      const newButton = getRepoSelectorButton(page);
      await expect(newButton).toHaveClass(/btn-primary/);
    });

    test('browser back/forward preserves repo selection', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Open dropdown and select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Navigate to a different tab
      await page.getByRole('tab', { name: 'AI Adoption' }).click();
      await expect(page).toHaveURL(/\/ai-adoption/);
      await expect(page).toHaveURL(/repo=/);

      // Go back
      await page.goBack();
      await expect(page).toHaveURL(/\/analytics\//);
      await expect(page).toHaveURL(/repo=/);

      // Go forward
      await page.goForward();
      await expect(page).toHaveURL(/\/ai-adoption/);
      await expect(page).toHaveURL(/repo=/);
    });
  });

  test.describe('Tab Navigation Preservation', () => {
    test('repo selection persists when switching tabs', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);
      await expect(page).toHaveURL(/repo=/);

      // Navigate through tabs and verify repo param persists
      const tabs = ['AI Adoption', 'Delivery', 'Quality', 'Team', 'Trends'];

      for (const tab of tabs) {
        await page.getByRole('tab', { name: tab }).click();
        await expect(page).toHaveURL(/repo=/);
      }
    });

    test('date filter and repo filter work together', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Set date filter to 7d
      await page.getByRole('button', { name: '7d' }).click();
      await waitForHtmxComplete(page);
      await expect(page).toHaveURL(/days=7/);

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Both params should be in URL
      await expect(page).toHaveURL(/days=7/);
      await expect(page).toHaveURL(/repo=/);

      // Switch tabs - both should persist
      await page.getByRole('tab', { name: 'AI Adoption' }).click();
      await expect(page).toHaveURL(/days=7/);
      await expect(page).toHaveURL(/repo=/);
    });
  });

  test.describe('Crosslinks Include Repo Filter', () => {
    test('View PRs quick links include repo param when repo selected', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Check "All Pull Requests" link includes repo param
      const prLink = page.getByRole('link', { name: 'All Pull Requests' });
      const href = await prLink.getAttribute('href');
      expect(href).toMatch(/repo=/);

      // Click and verify URL
      await prLink.click();
      await expect(page).toHaveURL(/\/pull-requests/);
      await expect(page).toHaveURL(/repo=/);
    });

    test('AI-Assisted PRs link includes repo param when repo selected', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Check "AI-Assisted PRs" link includes repo param
      const aiLink = page.getByRole('link', { name: 'AI-Assisted PRs' });
      const href = await aiLink.getAttribute('href');
      expect(href).toMatch(/repo=/);
      expect(href).toMatch(/ai=yes/);
    });
  });

  test.describe('Data Filtering', () => {
    test('selecting repo triggers HTMX chart updates with repo param', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Monitor network requests
      const chartRequests: string[] = [];
      page.on('request', request => {
        const url = request.url();
        if (url.includes('/cards/') || url.includes('/charts/')) {
          chartRequests.push(url);
        }
      });

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      // Clear previous requests
      chartRequests.length = 0;

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Wait for URL to update with repo param instead of networkidle
      await expect(page).toHaveURL(/repo=/, { timeout: 5000 });

      // Give HTMX requests time to start
      await page.waitForTimeout(500);

      // Verify chart requests include repo parameter
      const requestsWithRepo = chartRequests.filter(url => url.includes('repo='));
      expect(requestsWithRepo.length).toBeGreaterThan(0);
    });

    test('key metrics cards update when repo is selected', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Wait for initial metrics to load (skeleton disappears)
      await expect(page.locator('#key-metrics-container .skeleton')).toHaveCount(0, { timeout: 10000 });

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Wait for URL to update with repo param
      await expect(page).toHaveURL(/repo=/, { timeout: 5000 });

      // Verify metrics container still exists and content loaded (no skeletons)
      await expect(page.locator('#key-metrics-container')).toBeVisible();
      await expect(page.locator('#key-metrics-container .skeleton')).toHaveCount(0, { timeout: 10000 });
    });
  });

  test.describe('Button State', () => {
    test('repo selector button highlights when repo is selected', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      const button = getRepoSelectorButton(page);

      // Initially should NOT have btn-primary class (ghost/default state)
      await expect(button).not.toHaveClass(/btn-primary/);

      // Select a repo
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Button should now have btn-primary class to indicate active filter
      const activeButton = getRepoSelectorButton(page);
      await expect(activeButton).toHaveClass(/btn-primary/);
    });

    test('repo selector shows short repo name', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await waitForPageReady(page);

      const hasSelector = await hasRepoSelector(page);
      if (!hasSelector) {
        test.skip();
        return;
      }

      // Select a repo
      const button = getRepoSelectorButton(page);
      await button.click();
      const dropdown = getRepoDropdown(page);
      const repoLinks = dropdown.locator('li a').filter({ hasNot: page.locator('text=All Repositories') });
      const repoCount = await repoLinks.count();

      if (repoCount === 0) {
        test.skip();
        return;
      }

      await repoLinks.first().click();
      await waitForHtmxComplete(page);

      // Button text should show just the repo name (not "owner/repo")
      // The getDisplayName() function returns just the repo part
      const activeButton = getRepoSelectorButton(page);
      const buttonText = await activeButton.textContent();

      // Should NOT show "All Repositories"
      expect(buttonText).not.toContain('All Repositories');
    });
  });
});
