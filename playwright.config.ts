import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright E2E Test Configuration
 *
 * Run all tests: npx playwright test
 * Run smoke tests only: npx playwright test --grep @smoke
 * Run auth tests: npx playwright test --grep @auth
 * Run dashboard tests: npx playwright test --grep @dashboard
 * Run with UI: npx playwright test --ui
 * Run headed: npx playwright test --headed
 * Run specific file: npx playwright test surveys.spec.ts
 */
export default defineConfig({
  testDir: './tests/e2e',

  // Run tests in parallel
  fullyParallel: true,

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 0,

  // Opt out of parallel tests on CI (to avoid database conflicts)
  workers: process.env.CI ? 1 : undefined,

  // Reporter to use
  reporter: [
    ['html', { open: 'never' }],
    ['list'],
    // Add JSON reporter for CI integration
    ...(process.env.CI ? [['json', { outputFile: 'test-results/results.json' }] as const] : []),
  ],

  // Shared settings for all projects
  use: {
    // Base URL for all tests
    baseURL: 'http://localhost:8000',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure (useful for debugging flaky tests)
    video: 'on-first-retry',

    // Timeout for each action
    actionTimeout: 10000,

    // Default navigation timeout
    navigationTimeout: 15000,
  },

  // Global timeout for each test
  timeout: 30000,

  // Expect timeout
  expect: {
    timeout: 5000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  // Output directory for test artifacts
  outputDir: 'test-results/',

  // Run local dev server before starting tests (optional)
  // Uncomment if you want Playwright to start the server automatically
  // webServer: {
  //   command: 'make dev',
  //   url: 'http://localhost:8000',
  //   reuseExistingServer: !process.env.CI,
  //   timeout: 120000,
  // },
});
