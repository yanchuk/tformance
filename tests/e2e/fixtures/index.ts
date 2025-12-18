/**
 * E2E Test Fixtures
 *
 * Central export for all test fixtures and helpers.
 *
 * Usage:
 * ```ts
 * import { test, expect, loginAs, waitForHtmxContent } from './fixtures';
 * ```
 */

// Re-export test and expect with custom fixtures
export { test, expect } from './test-fixtures';

// Re-export all helpers from test-fixtures
export {
  waitForHtmxContent,
  selectDateRange,
  getStatCardValue,
  chartHasData,
  navigateTo,
  openDropdown,
  confirmModal,
  cancelModal,
} from './test-fixtures';

// Re-export user management
export {
  TEST_USERS,
  loginAs,
  logout,
  clearSession,
  isAuthenticated,
} from './test-users';
export type { TestUserRole } from './test-users';

// Re-export seed helpers
export {
  SEED_DATA_COUNTS,
  EXPECTED_RANGES,
  runSeedCommand,
  checkSeedDataExists,
  waitForServer,
  isInRange,
  parseMetricValue,
} from './seed-helpers';
