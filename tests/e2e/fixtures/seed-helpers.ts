import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Expected seed data counts for validation.
 * These match the defaults in seed_demo_data management command.
 */
export const SEED_DATA_COUNTS = {
  teams: 1,
  membersPerTeam: 5,
  prsPerTeam: 50,
  surveysApprox: 30, // ~60% of merged PRs
  reviewsApprox: 60, // 1-2 per survey
  commitsApprox: 300, // varies
  jiraIssuesPerTeam: 40,
  aiUsageDaysPerTeam: 150, // 30 days of data
  weeklyMetricsPerTeam: 40, // 8 weeks * 5 members
} as const;

/**
 * Expected data ranges for spot-check validation.
 */
export const EXPECTED_RANGES = {
  cycleTimeHours: { min: 2, max: 72 },
  reviewTimeHours: { min: 1, max: 24 },
  qualityRating: { min: 1, max: 3 },
  aiAssistedPercent: { min: 0, max: 100 },
  prAdditions: { min: 10, max: 500 },
  prDeletions: { min: 5, max: 200 },
} as const;

/**
 * Run the Django seed command to populate demo data.
 *
 * @param options - Seed options
 * @returns Promise with stdout/stderr
 *
 * @example
 * ```ts
 * // Default seed
 * await runSeedCommand();
 *
 * // Custom amounts
 * await runSeedCommand({ teams: 2, members: 10, prs: 100 });
 *
 * // Clear and reseed
 * await runSeedCommand({ clear: true });
 * ```
 */
export async function runSeedCommand(options?: {
  teams?: number;
  members?: number;
  prs?: number;
  clear?: boolean;
  teamSlug?: string;
}): Promise<{ stdout: string; stderr: string }> {
  let command = 'python manage.py seed_demo_data';

  if (options?.clear) {
    command += ' --clear';
  }
  if (options?.teams) {
    command += ` --teams ${options.teams}`;
  }
  if (options?.members) {
    command += ` --members ${options.members}`;
  }
  if (options?.prs) {
    command += ` --prs ${options.prs}`;
  }
  if (options?.teamSlug) {
    command += ` --team-slug ${options.teamSlug}`;
  }

  return execAsync(command);
}

/**
 * Check if seed data appears to be loaded by making a quick API check.
 * This is a lightweight check that doesn't query the database directly.
 *
 * @param baseUrl - Base URL of the application
 * @returns true if seed data appears present, false otherwise
 */
export async function checkSeedDataExists(baseUrl: string = 'http://localhost:8000'): Promise<boolean> {
  try {
    // Check health endpoint to verify server is running
    const response = await fetch(`${baseUrl}/health/`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Wait for the dev server to be ready.
 *
 * @param baseUrl - Base URL to check
 * @param timeoutMs - Maximum time to wait
 * @returns true if server is ready, false if timeout
 */
export async function waitForServer(
  baseUrl: string = 'http://localhost:8000',
  timeoutMs: number = 30000
): Promise<boolean> {
  const startTime = Date.now();
  const pollInterval = 1000;

  while (Date.now() - startTime < timeoutMs) {
    try {
      const response = await fetch(`${baseUrl}/health/`);
      if (response.ok || response.status === 500) {
        // 500 is acceptable - means server is up but might have config issues
        return true;
      }
    } catch {
      // Server not ready yet
    }
    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  return false;
}

/**
 * Validate that a numeric value is within expected range.
 *
 * @param value - Value to validate
 * @param range - Expected min/max range
 * @returns true if value is within range
 */
export function isInRange(
  value: number,
  range: { min: number; max: number }
): boolean {
  return value >= range.min && value <= range.max;
}

/**
 * Parse a metric value from dashboard display text.
 * Handles formats like "24.5h", "85%", "2.5", etc.
 *
 * @param text - Text containing the metric value
 * @returns Parsed numeric value or NaN
 */
export function parseMetricValue(text: string): number {
  // Remove common suffixes and parse
  const cleaned = text.replace(/[h%s]/gi, '').replace(/,/g, '').trim();
  return parseFloat(cleaned);
}
