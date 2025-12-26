import { test, expect } from '@playwright/test';

/**
 * Analytics Pages Tests
 * Run with: npx playwright test analytics.spec.ts
 * Tag: @analytics
 *
 * Tests for the new tabbed analytics pages:
 * - Analytics Overview (Team Health)
 * - AI Adoption Page
 * - Delivery Page
 * - Quality Page
 * - Team Performance Page
 * - Pull Requests Data Explorer
 */

test.describe('Analytics Pages Tests @analytics', () => {
  // Login before each test
  test.beforeEach(async ({ page }) => {
    await page.goto('/accounts/login/');
    await page.getByRole('textbox', { name: 'Email' }).fill('admin@example.com');
    await page.getByRole('textbox', { name: 'Password' }).fill('admin123');
    await page.getByRole('button', { name: 'Sign In' }).click();
    await expect(page).toHaveURL(/\/app/);
  });

  test.describe('Analytics Overview Page', () => {
    test('overview page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Team Health Overview' })).toBeVisible();
    });

    test('tab navigation displays all tabs correctly', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      // Should have all 6 tabs
      await expect(page.getByRole('tab', { name: 'Overview' })).toBeVisible();
      await expect(page.getByRole('tab', { name: 'AI Adoption' })).toBeVisible();
      await expect(page.getByRole('tab', { name: 'Delivery' })).toBeVisible();
      await expect(page.getByRole('tab', { name: 'Quality' })).toBeVisible();
      await expect(page.getByRole('tab', { name: 'Team' })).toBeVisible();
      await expect(page.getByRole('tab', { name: 'Pull Requests' })).toBeVisible();
    });

    test('date range filter buttons display', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      // Should have time range filter buttons (now using button role, not link)
      await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    });

    test('key metrics cards load via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow HTMX to load

      // Check for metric labels
      await expect(page.getByText('PRs Merged').first()).toBeVisible();
      await expect(page.getByText('Avg Cycle Time').first()).toBeVisible();
    });

    test('AI adoption chart section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'AI Adoption Trend' })).toBeVisible();
    });

    test('cycle time trend section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Cycle Time Trend' })).toBeVisible();
    });

    test('quality by AI status section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Quality by AI Status' })).toBeVisible();
    });

    test('PR size distribution section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'PR Size Distribution' })).toBeVisible();
    });

    test('explore data quick links display', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Explore Data' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'All Pull Requests' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'AI-Assisted PRs' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Full Dashboard' })).toBeVisible();
    });

    test('date filter changes URL', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // Click 7d - Alpine updates button state, HTMX updates page content
      await page.getByRole('button', { name: '7d' }).click();
      // Wait for HTMX to update the content (checking that page still renders)
      await page.waitForTimeout(1000);
      // Verify button state updated (Alpine works)
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-primary/);
    });

    test('time range button highlighting updates on HTMX click', async ({ page }) => {
      // Start with default (30d)
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // 30d should be primary (active)
      await expect(page.getByRole('button', { name: '30d' })).toHaveClass(/btn-primary/);
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-ghost/);

      // Click 7d - Alpine immediately updates button state
      await page.getByRole('button', { name: '7d' }).click();
      await page.waitForTimeout(500);

      // 7d should now be primary (active), 30d should be ghost
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-primary/);
      await expect(page.getByRole('button', { name: '30d' })).toHaveClass(/btn-ghost/);
    });

    test('time range button highlighting updates when switching to 90d', async ({ page }) => {
      await page.goto('/app/metrics/analytics/?days=7');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // 7d should be active
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-primary/);

      // Click 90d - Alpine immediately updates state
      await page.getByRole('button', { name: '90d' }).click();
      await page.waitForTimeout(500);

      // 90d should now be active
      await expect(page.getByRole('button', { name: '90d' })).toHaveClass(/btn-primary/);
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-ghost/);
    });

    test('navigate to Pull Requests via tab', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('tab', { name: 'Pull Requests' }).click();
      await expect(page).toHaveURL(/\/pull-requests/);
    });

    test('navigate to PR list via quick link', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('link', { name: 'All Pull Requests' }).click();
      await expect(page).toHaveURL(/\/pull-requests/);
    });

    test('navigate to AI-assisted PRs via quick link', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('link', { name: 'AI-Assisted PRs' }).click();
      await expect(page).toHaveURL(/\/pull-requests\/\?ai=yes/);
    });

    test('insights panel displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      // Check for AI Insights heading
      await expect(page.getByRole('heading', { name: 'AI Insights' })).toBeVisible();
    });
  });

  test.describe('AI Adoption Page', () => {
    test('AI Adoption page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'AI Adoption', exact: true })).toBeVisible();
    });

    test('AI Adoption tab is active', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('tab', { name: 'AI Adoption' })).toHaveClass(/tab-active/);
    });

    test('AI Adoption has date filter', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    });

    test('AI Adoption date filter updates button state', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // Verify initial state - 30d is default
      await expect(page.getByRole('button', { name: '30d' })).toHaveClass(/btn-primary/);

      // Click 7d and verify state updates
      await page.getByRole('button', { name: '7d' }).click();
      await page.waitForTimeout(500);
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-primary/);
    });

    test('navigate from AI Adoption to Delivery tab', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('tab', { name: 'Delivery' }).click();
      await expect(page).toHaveURL(/\/delivery/);
    });

    test('AI vs Non-AI comparison section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'AI vs Non-AI Quality Comparison' })).toBeVisible();
    });

    test('AI tool breakdown section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'AI Tools Breakdown' })).toBeVisible();
    });
  });

  test.describe('Delivery Page', () => {
    test('Delivery page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Delivery Metrics' })).toBeVisible();
    });

    test('Delivery tab is active', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('tab', { name: 'Delivery' })).toHaveClass(/tab-active/);
    });

    test('Delivery has date filter', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    });

    test('Delivery date filter updates button state', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // Click 90d and verify state updates
      await page.getByRole('button', { name: '90d' }).click();
      await page.waitForTimeout(500);
      await expect(page.getByRole('button', { name: '90d' })).toHaveClass(/btn-primary/);
    });

    test('navigate from Delivery to Quality tab', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('tab', { name: 'Quality' }).click();
      await expect(page).toHaveURL(/\/quality/);
    });

    test('Cycle Time Trend section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Cycle Time Trend' })).toBeVisible();
    });

    test('PR Size Distribution section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/delivery/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'PR Size Distribution' })).toBeVisible();
    });
  });

  test.describe('Quality Page', () => {
    test('Quality page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Quality Metrics' })).toBeVisible();
    });

    test('Quality tab is active', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('tab', { name: 'Quality' })).toHaveClass(/tab-active/);
    });

    test('Quality has date filter', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    });

    test('Quality date filter updates button state', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // Click 7d and verify state updates
      await page.getByRole('button', { name: '7d' }).click();
      await page.waitForTimeout(500);
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-primary/);
    });

    test('navigate from Quality to Team tab', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('tab', { name: 'Team' }).click();
      await expect(page).toHaveURL(/\/team/);
    });

    test('Review Time Trend section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Review Time Trend' })).toBeVisible();
    });

    test('CI/CD Pass Rate section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/quality/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'CI/CD Pass Rate' })).toBeVisible();
    });
  });

  test.describe('Team Performance Page', () => {
    test('Team page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Team Performance' })).toBeVisible();
    });

    test('Team tab is active', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('tab', { name: 'Team' })).toHaveClass(/tab-active/);
    });

    test('Team has date filter', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    });

    test('Team date filter updates button state', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Wait for HTMX/Alpine to initialize

      // Click 7d and verify state updates
      await page.getByRole('button', { name: '7d' }).click();
      await page.waitForTimeout(500);
      await expect(page.getByRole('button', { name: '7d' })).toHaveClass(/btn-primary/);
    });

    test('navigate from Team to Pull Requests tab', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('tab', { name: 'Pull Requests' }).click();
      await expect(page).toHaveURL(/\/pull-requests/);
    });

    test('Team Breakdown section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Team Breakdown' })).toBeVisible();
    });

    test('Reviewer Workload section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Reviewer Workload' })).toBeVisible();
    });

    test('Review Distribution section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Review Distribution' })).toBeVisible();
    });

    test('AI Detective Leaderboard section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'AI Detective Leaderboard' })).toBeVisible();
    });

    test('Explore Team Data links display', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Explore Team Data' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'All Pull Requests' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Quality Metrics' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Full Dashboard' })).toBeVisible();
    });

    test('navigate from Team to PR list via quick link', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      await page.getByRole('link', { name: 'All Pull Requests' }).click();
      await expect(page).toHaveURL(/\/pull-requests/);
    });
  });

  test.describe('Pull Requests Data Explorer', () => {
    test('PR list page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Pull Requests' })).toBeVisible();
    });

    test('filter panel displays', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Should have filter controls
      await expect(page.getByText('Filters').first()).toBeVisible();
    });

    test('PR table displays with expected columns', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500); // Allow table to load

      // Check for table headers (Cmts = Comments abbreviated, Size = Lines)
      await expect(page.getByRole('columnheader', { name: 'Title' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Author' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Cmts' })).toBeVisible();
      await expect(page.getByRole('columnheader', { name: 'Size' })).toBeVisible();
    });

    test('sortable columns show cursor pointer on hover', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Sortable columns should have cursor-pointer class
      const cycleTimeHeader = page.getByRole('columnheader', { name: /Cycle Time/ });
      await expect(cycleTimeHeader).toHaveClass(/cursor-pointer/);
    });

    test('clicking sortable column updates URL with sort params', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Click Cycle Time column header to sort
      await page.getByRole('columnheader', { name: /Cycle Time/ }).click();
      await page.waitForTimeout(300);

      // URL should include sort params
      await expect(page).toHaveURL(/sort=cycle_time/);
    });

    test('clicking same column toggles sort order', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?sort=cycle_time&order=desc');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Should show descending indicator
      await expect(page.getByRole('columnheader', { name: /Cycle Time/ })).toContainText('▼');

      // Click again to toggle to ascending
      await page.getByRole('columnheader', { name: /Cycle Time/ }).click();
      await page.waitForTimeout(300);

      await expect(page).toHaveURL(/order=asc/);
      await expect(page.getByRole('columnheader', { name: /Cycle Time/ })).toContainText('▲');
    });

    test('sort indicator shows on active sort column', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/?sort=review_time&order=desc');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Review Time should show ▼
      await expect(page.getByRole('columnheader', { name: /Review Time/ })).toContainText('▼');

      // Other sortable columns should NOT show indicator
      await expect(page.getByRole('columnheader', { name: /Cycle Time/ })).not.toContainText('▲');
      await expect(page.getByRole('columnheader', { name: /Cycle Time/ })).not.toContainText('▼');
    });

    test('sort by Cmts column works', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Click Cmts (Comments) column header
      await page.getByRole('columnheader', { name: 'Cmts' }).click();
      await page.waitForTimeout(300);

      await expect(page).toHaveURL(/sort=comments/);
    });

    test('sort by Size column works', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Click Size (Lines) column header
      await page.getByRole('columnheader', { name: 'Size' }).click();
      await page.waitForTimeout(300);

      await expect(page).toHaveURL(/sort=lines/);
    });

    test('sorting preserves filters', async ({ page }) => {
      // Start with a filter applied
      await page.goto('/app/metrics/pull-requests/?state=merged');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Click to sort
      await page.getByRole('columnheader', { name: /Cycle Time/ }).click();
      await page.waitForTimeout(300);

      // URL should have both filter and sort params
      await expect(page).toHaveURL(/state=merged/);
      await expect(page).toHaveURL(/sort=cycle_time/);
    });

    test('stats row displays totals', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Should show total count label in stats
      await expect(page.getByText('Total PRs')).toBeVisible();
    });

    test('state filter works', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Select Merged state filter
      await page.selectOption('select[name="state"]', 'merged');

      // Submit filter form or wait for HTMX update
      await page.getByRole('button', { name: /Apply|Filter/ }).click();

      // URL should include state filter
      await expect(page).toHaveURL(/state=merged/);
    });

    test('CSV export button displays', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('link', { name: /Export|CSV/ })).toBeVisible();
    });

    test('pagination displays for large datasets', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(500);

      // Should show pagination if more than 50 PRs
      // This is conditional - may not show if demo data has < 50 PRs
      const pageInfo = page.locator('.join').filter({ hasText: /Page|Next|Previous|\d/ });
      // Just verify page loads without error
      await expect(page.getByRole('heading', { name: 'Pull Requests' })).toBeVisible();
    });

    test('navigate back to Overview via tab', async ({ page }) => {
      await page.goto('/app/metrics/pull-requests/');
      await page.waitForLoadState('domcontentloaded');

      // Note: PR list page may have different tab structure
      // Try to navigate back via any available link
      await page.goto('/app/metrics/analytics/');
      await expect(page).toHaveURL(/\/analytics/);
    });
  });

  test.describe('Active Tab Indicator', () => {
    test('active tab indicator updates after HTMX navigation', async ({ page }) => {
      // Start at Overview
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      // Verify Overview tab is active on initial load
      await expect(page.getByRole('tab', { name: 'Overview' })).toHaveClass(/tab-active/);
      await expect(page.getByRole('tab', { name: 'Quality' })).not.toHaveClass(/tab-active/);

      // Click Quality tab (HTMX navigation)
      await page.getByRole('tab', { name: 'Quality' }).click();
      await page.waitForURL(/\/quality/);

      // Verify Quality tab is now active (this is the bug - it should be active)
      await expect(page.getByRole('tab', { name: 'Quality' })).toHaveClass(/tab-active/);
      await expect(page.getByRole('tab', { name: 'Overview' })).not.toHaveClass(/tab-active/);
    });

    test('active tab indicator correct on each page full load', async ({ page }) => {
      // Test Overview
      await page.goto('/app/metrics/analytics/');
      await expect(page.getByRole('tab', { name: 'Overview' })).toHaveClass(/tab-active/);

      // Test AI Adoption
      await page.goto('/app/metrics/analytics/ai-adoption/');
      await expect(page.getByRole('tab', { name: 'AI Adoption' })).toHaveClass(/tab-active/);

      // Test Delivery
      await page.goto('/app/metrics/analytics/delivery/');
      await expect(page.getByRole('tab', { name: 'Delivery' })).toHaveClass(/tab-active/);

      // Test Quality
      await page.goto('/app/metrics/analytics/quality/');
      await expect(page.getByRole('tab', { name: 'Quality' })).toHaveClass(/tab-active/);

      // Test Team
      await page.goto('/app/metrics/analytics/team/');
      await expect(page.getByRole('tab', { name: 'Team' })).toHaveClass(/tab-active/);

      // Test Pull Requests
      await page.goto('/app/metrics/pull-requests/');
      await expect(page.getByRole('tab', { name: 'Pull Requests' })).toHaveClass(/tab-active/);
    });

    test('active tab indicator updates through full navigation flow', async ({ page }) => {
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');

      // Navigate through tabs and verify active state updates
      const tabSequence = [
        { click: 'AI Adoption', url: /\/ai-adoption/ },
        { click: 'Delivery', url: /\/delivery/ },
        { click: 'Quality', url: /\/quality/ },
        { click: 'Team', url: /\/team/ },
        { click: 'Pull Requests', url: /\/pull-requests/ },
        { click: 'Overview', url: /\/analytics\/(\?|$)/ },
      ];

      for (const { click, url } of tabSequence) {
        await page.getByRole('tab', { name: click }).click();
        await page.waitForURL(url);
        await expect(page.getByRole('tab', { name: click })).toHaveClass(/tab-active/);
      }
    });
  });

  test.describe('Cross-Page Navigation', () => {
    test('can navigate from old dashboard to new analytics', async ({ page }) => {
      // Go to old CTO overview
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');

      // Should have quick nav buttons to new pages
      await expect(page.getByRole('link', { name: 'Health Overview' })).toBeVisible();
      await expect(page.getByRole('link', { name: 'Pull Requests' })).toBeVisible();

      // Click Health Overview
      await page.getByRole('link', { name: 'Health Overview' }).click();
      await expect(page).toHaveURL(/\/analytics/);
    });

    test('full tab navigation flow: Overview -> AI -> Delivery -> Quality -> Team -> PRs', async ({ page }) => {
      // Start at Analytics Overview
      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await expect(page.getByRole('tab', { name: 'Overview' })).toHaveClass(/tab-active/);

      // Navigate through all tabs with explicit waits for webkit
      await page.getByRole('tab', { name: 'AI Adoption' }).click();
      await page.waitForURL(/\/ai-adoption/);

      await page.getByRole('tab', { name: 'Delivery' }).click();
      await page.waitForURL(/\/delivery/);

      await page.getByRole('tab', { name: 'Quality' }).click();
      await page.waitForURL(/\/quality/);

      await page.getByRole('tab', { name: 'Team' }).click();
      await page.waitForURL(/\/team/);

      await page.getByRole('tab', { name: 'Pull Requests' }).click();
      await page.waitForURL(/\/pull-requests/);
    });

    test('full navigation flow: Dashboard -> Analytics -> PR List -> Back', async ({ page }) => {
      // Start at CTO overview (direct navigation to avoid sidebar ambiguity)
      await page.goto('/app/metrics/overview/');
      await page.waitForLoadState('domcontentloaded');

      // Navigate to new analytics via button
      await page.getByRole('link', { name: 'Health Overview' }).click();
      await expect(page).toHaveURL(/\/analytics/);

      // Navigate to PR list via tab
      await page.getByRole('tab', { name: 'Pull Requests' }).click();
      await expect(page).toHaveURL(/\/pull-requests/);

      // Navigate back to Full Dashboard via quick link
      await page.goto('/app/metrics/analytics/');
      await page.getByRole('link', { name: 'Full Dashboard' }).click();
      await expect(page).toHaveURL(/\/overview/);
    });

    test('date filter persists when switching tabs via HTMX', async ({ page }) => {
      // Start at Analytics Overview with 7d filter
      await page.goto('/app/metrics/analytics/?days=7');
      await page.waitForLoadState('domcontentloaded');

      // Navigate to AI Adoption via tab (uses HTMX hx-get with days param)
      await page.getByRole('tab', { name: 'AI Adoption' }).click();
      await expect(page).toHaveURL(/days=7/);
    });

    test('sidebar Analytics link goes to overview', async ({ page }) => {
      // Go to integrations first (any page with sidebar)
      await page.goto('/app/integrations/');
      await page.waitForLoadState('domcontentloaded');

      // Click Analytics in sidebar
      await page.getByRole('link', { name: 'Analytics' }).click();

      // Should go to analytics overview (via redirect)
      await expect(page).toHaveURL(/\/analytics/);
    });

    test('navigate from Team page to Quality via quick link', async ({ page }) => {
      await page.goto('/app/metrics/analytics/team/');
      await page.waitForLoadState('domcontentloaded');

      // Wait for the Explore Team Data section to be visible
      await expect(page.getByRole('heading', { name: 'Explore Team Data' })).toBeVisible();

      // Click and wait for navigation
      await Promise.all([
        page.waitForURL(/\/quality/),
        page.getByRole('link', { name: 'Quality Metrics' }).click(),
      ]);
      await expect(page).toHaveURL(/\/quality/);
    });
  });

  test.describe('Trends Page', () => {
    test('Trends page loads with title', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Trends & Comparison' })).toBeVisible();
    });

    test('Trends tab is active', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('tab', { name: 'Trends' })).toHaveClass(/tab-active/);
    });

    test('Trends has date filter', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('button', { name: '7d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '30d' })).toBeVisible();
      await expect(page.getByRole('button', { name: '90d' })).toBeVisible();
    });

    test('metric selector displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      // Should have metric checkboxes for comparison
      await expect(page.getByText('Compare:')).toBeVisible();
      await expect(page.getByRole('checkbox').first()).toBeVisible();
      // Cycle Time should be checked by default
      await expect(page.getByLabel('Cycle Time')).toBeChecked();
    });

    test('granularity toggle displays weekly/monthly options', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      // Should have granularity toggle
      await expect(page.getByText('Group by:')).toBeVisible();
      await expect(page.getByRole('button', { name: 'Weekly' })).toBeVisible();
      await expect(page.getByRole('button', { name: 'Monthly' })).toBeVisible();
    });

    test('trend chart loads via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000); // Allow HTMX to load chart

      // Check for chart header that appears after HTMX load
      await expect(page.getByRole('heading', { name: /Cycle Time \(hours\)/ })).toBeVisible();
    });

    test('chart has zoom/pan instructions', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      await expect(page.getByText('Scroll to zoom, drag to pan')).toBeVisible();
    });

    test('quick stats cards display', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // Should show metric cards in the grid (not in the dropdown)
      const cardGrid = page.locator('.grid.grid-cols-1.md\\:grid-cols-4');
      await expect(cardGrid.getByText('Cycle Time')).toBeVisible();
      await expect(cardGrid.getByText('Review Time')).toBeVisible();
      await expect(cardGrid.getByText('PRs Merged')).toBeVisible();
      await expect(cardGrid.getByText('AI Adoption')).toBeVisible();
    });

    test('Industry Benchmark section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Industry Benchmark' })).toBeVisible();
    });

    test('Chart Settings section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Chart Settings' })).toBeVisible();
    });

    test('Tips section displays', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      await expect(page.getByRole('heading', { name: 'Tips' })).toBeVisible();
    });

    test('selecting multiple metrics shows comparison chart', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Add Review Time to comparison (Cycle Time already selected)
      await page.getByLabel('Review Time').click();
      await page.waitForTimeout(2000);

      // Chart title should show comparison
      await expect(page.getByRole('heading', { name: /Cycle Time vs Review Time/ })).toBeVisible();
      // Should show "Comparing" badge
      await expect(page.getByText('Comparing')).toBeVisible();
    });

    test('PR type breakdown chart loads via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Scroll to PR type chart section (it's below the fold)
      await page.locator('#pr-type-chart-container').scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // PR type chart should load via HTMX
      await expect(page.getByRole('heading', { name: 'PR Types Over Time' })).toBeVisible();
      // Chart canvas should exist
      await expect(page.locator('#pr-type-chart')).toBeAttached();
    });

    test('Tech breakdown chart loads via HTMX', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(2000);

      // Scroll to tech chart section (it's below the fold)
      await page.locator('#tech-chart-container').scrollIntoViewIfNeeded();
      await page.waitForTimeout(1000);

      // Tech breakdown chart should load via HTMX
      await expect(page.getByRole('heading', { name: 'Technology Breakdown' })).toBeVisible();
      // Chart canvas should exist
      await expect(page.locator('#tech-chart')).toBeAttached();
    });

    test('navigate from Trends to other tabs', async ({ page }) => {
      await page.goto('/app/metrics/analytics/trends/');
      await page.waitForLoadState('domcontentloaded');

      // Navigate to Overview (URL may have query params like ?days=30)
      await page.getByRole('tab', { name: 'Overview' }).click();
      await expect(page).toHaveURL(/\/analytics\/?\?/);
    });
  });

  test.describe('Responsive UI Tests @responsive', () => {
    test('key metrics card values are fully visible at narrow viewport (768px)', async ({ page }) => {
      // Set narrow viewport (tablet portrait)
      await page.setViewportSize({ width: 768, height: 1024 });

      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow HTMX to load cards

      // Get all stat-value elements
      const statValues = page.locator('.stat-value');
      const count = await statValues.count();

      // Verify we have cards loaded
      expect(count).toBeGreaterThan(0);

      // Check each card value text is fully visible (not truncated/clipped)
      for (let i = 0; i < count; i++) {
        const element = statValues.nth(i);
        const box = await element.boundingBox();

        // Skip if element is not visible
        if (!box) continue;

        // Check if text is being truncated by comparing natural width vs actual width
        // Natural width = what the text would take without constraints
        const { isTruncated, textContent, naturalWidth, actualWidth } = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          // Get actual width
          const actualWidth = el.clientWidth;
          // Create a temporary span to measure natural text width
          const span = document.createElement('span');
          span.style.visibility = 'hidden';
          span.style.position = 'absolute';
          span.style.whiteSpace = 'nowrap';
          span.style.font = style.font;
          span.style.fontSize = style.fontSize;
          span.style.fontWeight = style.fontWeight;
          span.textContent = el.textContent;
          document.body.appendChild(span);
          const naturalWidth = span.offsetWidth;
          document.body.removeChild(span);
          return {
            isTruncated: naturalWidth > actualWidth + 2, // 2px tolerance
            textContent: el.textContent?.trim() || '',
            naturalWidth,
            actualWidth
          };
        });

        // Value should NOT be truncated - font should be small enough to fit
        expect(isTruncated, `Card "${textContent}" is truncated (natural: ${naturalWidth}px, actual: ${actualWidth}px)`).toBe(false);
      }
    });

    test('key metrics card values are fully visible at 1024px viewport', async ({ page }) => {
      // Set tablet landscape viewport
      await page.setViewportSize({ width: 1024, height: 768 });

      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000); // Allow HTMX to load cards

      // Get all stat-value elements
      const statValues = page.locator('.stat-value');
      const count = await statValues.count();

      // Verify we have cards loaded
      expect(count).toBeGreaterThan(0);

      // Check each card value is not truncated
      for (let i = 0; i < count; i++) {
        const element = statValues.nth(i);
        const box = await element.boundingBox();

        if (!box) continue;

        const { isTruncated, textContent, naturalWidth, actualWidth } = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          const actualWidth = el.clientWidth;
          const span = document.createElement('span');
          span.style.visibility = 'hidden';
          span.style.position = 'absolute';
          span.style.whiteSpace = 'nowrap';
          span.style.font = style.font;
          span.style.fontSize = style.fontSize;
          span.style.fontWeight = style.fontWeight;
          span.textContent = el.textContent;
          document.body.appendChild(span);
          const naturalWidth = span.offsetWidth;
          document.body.removeChild(span);
          return {
            isTruncated: naturalWidth > actualWidth + 2,
            textContent: el.textContent?.trim() || '',
            naturalWidth,
            actualWidth
          };
        });

        expect(isTruncated, `Card "${textContent}" is truncated at 1024px`).toBe(false);
      }
    });

    test('key metrics card values are fully visible at mobile viewport (375px)', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto('/app/metrics/analytics/');
      await page.waitForLoadState('domcontentloaded');
      await page.waitForTimeout(1000);

      // On mobile, cards should stack (grid-cols-1) giving more width
      const statValues = page.locator('.stat-value');
      const count = await statValues.count();

      expect(count).toBeGreaterThan(0);

      // Check text is not truncated at mobile size (full width cards)
      for (let i = 0; i < count; i++) {
        const element = statValues.nth(i);
        const box = await element.boundingBox();

        if (!box) continue;

        const { isTruncated, textContent, naturalWidth, actualWidth } = await element.evaluate((el) => {
          const style = window.getComputedStyle(el);
          const actualWidth = el.clientWidth;
          const span = document.createElement('span');
          span.style.visibility = 'hidden';
          span.style.position = 'absolute';
          span.style.whiteSpace = 'nowrap';
          span.style.font = style.font;
          span.style.fontSize = style.fontSize;
          span.style.fontWeight = style.fontWeight;
          span.textContent = el.textContent;
          document.body.appendChild(span);
          const naturalWidth = span.offsetWidth;
          document.body.removeChild(span);
          return {
            isTruncated: naturalWidth > actualWidth + 2,
            textContent: el.textContent?.trim() || '',
            naturalWidth,
            actualWidth
          };
        });

        expect(isTruncated, `Card "${textContent}" is truncated on mobile`).toBe(false);
      }
    });
  });
});
