import { Page } from '@playwright/test';

/**
 * Alpine.js helper utilities for E2E tests.
 * Use these helpers to wait for Alpine initialization and store state.
 */

/**
 * Wait for Alpine.js to be loaded and initialized.
 *
 * @param page - Playwright page object
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 *
 * @example
 * ```ts
 * await page.goto('/app/');
 * await waitForAlpine(page);
 * // Alpine is now available
 * ```
 */
export async function waitForAlpine(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => typeof (window as any).Alpine !== 'undefined',
    { timeout }
  );
}

/**
 * Wait for a specific Alpine store to be initialized.
 *
 * @param page - Playwright page object
 * @param storeName - Name of the Alpine store to wait for (default: 'dateRange')
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 *
 * @example
 * ```ts
 * await waitForAlpineStore(page, 'dateRange');
 * // $store.dateRange is now available
 * ```
 */
export async function waitForAlpineStore(
  page: Page,
  storeName: string = 'dateRange',
  timeout = 5000
): Promise<void> {
  await page.waitForFunction(
    (name) => {
      const Alpine = (window as any).Alpine;
      return Alpine && Alpine.store && Alpine.store(name) !== undefined;
    },
    storeName,
    { timeout }
  );
}

/**
 * Wait for Alpine components on the page to be fully initialized.
 * This checks that all [x-data] elements have been processed by Alpine.
 *
 * @param page - Playwright page object
 * @param timeout - Maximum wait time in milliseconds (default: 5000)
 *
 * @example
 * ```ts
 * await waitForAlpineComponents(page);
 * // All Alpine components are initialized
 * ```
 */
export async function waitForAlpineComponents(page: Page, timeout = 5000): Promise<void> {
  await page.waitForFunction(
    () => {
      const Alpine = (window as any).Alpine;
      if (!Alpine) return false;

      const alpineElements = document.querySelectorAll('[x-data]');
      if (alpineElements.length === 0) return true; // No components to wait for

      return Array.from(alpineElements).every(el => (el as any).__x);
    },
    { timeout }
  ).catch(() => {
    // Fallback: if Alpine check fails, continue
  });
}

/**
 * Get the value of an Alpine store property.
 *
 * @param page - Playwright page object
 * @param storeName - Name of the Alpine store
 * @param propertyPath - Dot-separated path to the property
 * @returns The store property value
 *
 * @example
 * ```ts
 * const days = await getAlpineStoreValue(page, 'dateRange', 'days');
 * expect(days).toBe(30);
 * ```
 */
export async function getAlpineStoreValue(
  page: Page,
  storeName: string,
  propertyPath: string
): Promise<unknown> {
  return page.evaluate(
    ({ store, path }) => {
      const Alpine = (window as any).Alpine;
      if (!Alpine || !Alpine.store) return undefined;

      const storeObj = Alpine.store(store);
      if (!storeObj) return undefined;

      // Navigate property path
      return path.split('.').reduce((obj, key) => obj?.[key], storeObj);
    },
    { store: storeName, path: propertyPath }
  );
}
