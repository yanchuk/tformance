import { Page } from '@playwright/test';

/**
 * Test user credentials for e2e tests.
 * These users should exist in the database (created by migrations or seed data).
 */
export const TEST_USERS = {
  admin: {
    email: 'admin@example.com',
    password: 'admin123',
    role: 'admin' as const,
  },
} as const;

export type TestUserRole = keyof typeof TEST_USERS;

/**
 * Log in as a specific test user.
 *
 * @param page - Playwright page object
 * @param userRole - Role of user to log in as (defaults to 'admin')
 * @returns Promise that resolves when login is complete
 *
 * @example
 * ```ts
 * await loginAs(page, 'admin');
 * // Now authenticated as admin user
 * ```
 */
export async function loginAs(page: Page, userRole: TestUserRole = 'admin'): Promise<void> {
  const user = TEST_USERS[userRole];

  await page.goto('/accounts/login/');
  await page.getByRole('textbox', { name: 'Email' }).fill(user.email);
  await page.getByRole('textbox', { name: 'Password' }).fill(user.password);
  await page.getByRole('button', { name: 'Sign In' }).click();

  // Wait for redirect to app or onboarding
  await page.waitForURL(/\/(app|onboarding)/, { timeout: 10000 });
}

/**
 * Log out the current user.
 *
 * @param page - Playwright page object
 * @returns Promise that resolves when logout is complete
 */
export async function logout(page: Page): Promise<void> {
  await page.goto('/accounts/logout/');
  await page.waitForURL('/');
}

/**
 * Clear all cookies to ensure clean session state.
 *
 * @param page - Playwright page object
 */
export async function clearSession(page: Page): Promise<void> {
  await page.context().clearCookies();
}

/**
 * Check if user is currently authenticated.
 *
 * @param page - Playwright page object
 * @returns true if authenticated, false otherwise
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
  const response = await page.goto('/app/');
  const url = page.url();
  return !url.includes('/accounts/login');
}
