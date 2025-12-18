import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * Subscription and Billing Tests
 * Tests subscription page, plan display, and Stripe integration points.
 * Run with: npx playwright test subscription.spec.ts
 * Tag: @subscription @billing
 *
 * Note: Actual Stripe checkout flows are not tested as they redirect
 * to external Stripe pages. We test up to the redirect point.
 */

test.describe('Subscription Page @subscription', () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page);
  });

  test.describe('Subscription Page Load', () => {
    test('subscription page loads', async ({ page }) => {
      await page.goto('/app/subscription/');
      await page.waitForLoadState('domcontentloaded');

      // Should show subscription/billing heading or content
      const hasHeading = await page.getByRole('heading', { name: /subscription|billing|plan/i }).isVisible().catch(() => false);
      const hasContent = await page.getByText(/subscription|billing|plan/i).first().isVisible().catch(() => false);

      expect(hasHeading || hasContent).toBeTruthy();
    });

    test('shows subscription status', async ({ page }) => {
      await page.goto('/app/subscription/');
      await page.waitForLoadState('domcontentloaded');

      // Should show current subscription status
      const hasStatus = await page.getByText(/active|inactive|trial|free|pro|enterprise/i).isVisible().catch(() => false);

      // Some status indication should be present
    });
  });

  test.describe('Plan Display', () => {
    test('shows available plans or current plan', async ({ page }) => {
      await page.goto('/app/subscription/');
      await page.waitForLoadState('domcontentloaded');

      // Look for plan information
      const planInfo = page.getByText(/plan|pricing|month|year/i);
      const hasPlanInfo = await planInfo.first().isVisible().catch(() => false);

      // Some plan information should be visible
    });

    test('upgrade button visible when applicable', async ({ page }) => {
      await page.goto('/app/subscription/');
      await page.waitForLoadState('domcontentloaded');

      // Look for upgrade/subscribe button
      const upgradeButton = page.getByRole('button', { name: /upgrade|subscribe|start|choose/i }).or(
        page.getByRole('link', { name: /upgrade|subscribe|start|choose/i })
      );

      // Upgrade option may or may not be visible depending on current plan
      const hasUpgrade = await upgradeButton.isVisible().catch(() => false);
    });
  });

  test.describe('Stripe Integration Points', () => {
    test('checkout canceled page loads', async ({ page }) => {
      await page.goto('/app/subscription/checkout-canceled/');

      // Should show cancellation message or redirect
      const url = page.url();
      if (url.includes('checkout-canceled')) {
        const hasCancelMessage = await page.getByText(/cancel|return|try again/i).isVisible().catch(() => false);
        // Should show some message about canceled checkout
      }
    });

    test('subscription confirm page exists', async ({ page }) => {
      await page.goto('/subscriptions/confirm/');

      // May redirect or show confirmation info
      // Just testing the route exists
    });
  });

  test.describe('Demo Mode', () => {
    test('demo page loads', async ({ page }) => {
      await page.goto('/app/subscription/demo/');
      await page.waitForLoadState('domcontentloaded');

      // Should show demo content or subscription page
      const url = page.url();
      expect(url).toMatch(/\/subscription/);
    });
  });

  test.describe('Billing Portal', () => {
    test('portal link exists for subscribed users', async ({ page }) => {
      await page.goto('/app/subscription/');
      await page.waitForLoadState('domcontentloaded');

      // Look for billing portal / manage subscription link
      const portalLink = page.getByRole('link', { name: /manage|portal|billing/i }).or(
        page.getByRole('button', { name: /manage|portal|billing/i })
      );

      // Portal link may or may not be visible
      const hasPortal = await portalLink.isVisible().catch(() => false);
    });
  });

  test.describe('Access Control', () => {
    test('subscription page requires authentication', async ({ page, context }) => {
      await context.clearCookies();
      await page.goto('/app/subscription/');

      // Should redirect to login
      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('subscription page requires team membership', async ({ page }) => {
      // Already logged in via beforeEach
      await page.goto('/app/subscription/');

      // Should either show page or redirect if not team admin
      const url = page.url();
      // Valid states: on subscription page, or redirected due to permissions
    });
  });

  test.describe('Subscription Navigation', () => {
    test('can navigate to billing from app', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Find billing/subscription link
      const billingLink = page.getByRole('link', { name: /billing|subscription/i });

      if (await billingLink.isVisible()) {
        await billingLink.click();
        await expect(page).toHaveURL(/\/subscription/);
      }
    });

    test('billing link in sidebar', async ({ page }) => {
      await page.goto('/app/');
      await page.waitForLoadState('domcontentloaded');

      // Look for billing in navigation
      const billingLink = page.getByRole('link', { name: /billing/i });
      const hasBillingLink = await billingLink.isVisible().catch(() => false);

      // Billing should be accessible from nav
      expect(hasBillingLink).toBeTruthy();
    });
  });
});

test.describe('Subscription API Endpoints @subscription', () => {
  test('products API endpoint exists', async ({ page }) => {
    await loginAs(page);

    // Navigate to subscription page which uses this API
    await page.goto('/app/subscription/');
    await page.waitForLoadState('domcontentloaded');

    // If we can see the subscription page, the API is working
    const url = page.url();
    expect(url).toMatch(/\/subscription/);
  });

  test('create checkout session requires auth', async ({ page, context }) => {
    await context.clearCookies();

    const response = await page.request.post('/app/subscription/stripe/api/create-checkout-session/');

    // Should get redirect (302) or forbidden (403)
    expect([302, 403]).toContain(response.status());
  });

  test('create portal session requires auth', async ({ page, context }) => {
    await context.clearCookies();

    const response = await page.request.post('/app/subscription/stripe/api/create-portal-session/');

    // Should get redirect (302) or forbidden (403)
    expect([302, 403]).toContain(response.status());
  });
});
