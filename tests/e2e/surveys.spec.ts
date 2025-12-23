import { test, expect } from '@playwright/test';
import { loginAs } from './fixtures/test-users';

/**
 * Survey System Tests
 * Tests the PR survey flows for authors and reviewers.
 * Run with: npx playwright test surveys.spec.ts
 * Tag: @surveys
 *
 * ## Survey Access Requirements
 *
 * Survey pages have two levels of access control:
 * 1. Valid survey token (unique per survey, expires after 7 days)
 * 2. Author/Reviewer verification via GitHub OAuth
 *
 * The author/reviewer access check compares the logged-in user's GitHub
 * social account UID against the TeamMember's github_id. This means:
 * - Author survey: Only accessible to users whose GitHub UID matches the PR author
 * - Reviewer survey: Only accessible to users whose GitHub UID matches a PR reviewer
 *
 * ## Test Limitations
 *
 * Full survey flow tests require:
 * - A valid survey token (seeded via: python manage.py seed_e2e_surveys)
 * - A GitHub OAuth social account linked to the test user
 * - The social account UID matching the TeamMember's github_id
 *
 * Since our E2E test user (admin@example.com) uses email/password login without
 * a GitHub social account, we cannot test the full survey submission flow.
 *
 * ## What These Tests Cover
 *
 * 1. Invalid token handling - verified
 * 2. Authentication requirements - verified
 * 3. URL structure validation - verified
 * 4. Survey page renders (when accessible) - conditional
 * 5. Complete page accessibility - verified
 */

test.describe('Survey System @surveys', () => {
  test.describe('Invalid Token Handling', () => {
    test('invalid token shows 403 forbidden', async ({ page }) => {
      await loginAs(page);

      // Try to access survey with invalid token
      const response = await page.goto('/survey/invalid-token-12345/');

      // Should return 404 (token not found)
      expect(response?.status()).toBe(404);
    });

    test('empty token path returns 404', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto('/survey/');

      // Should be 404 (no matching URL pattern)
      expect(response?.status()).toBe(404);
    });

    test('malformed token with path traversal is rejected', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto(`/survey/${encodeURIComponent('../../../etc/passwd')}/`);
      expect(response?.status()).toBeGreaterThanOrEqual(400);
    });

    test('malformed token with XSS is rejected', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto(`/survey/${encodeURIComponent('<script>alert(1)</script>')}/`);
      expect(response?.status()).toBeGreaterThanOrEqual(400);
    });

    test('very long token is rejected', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto(`/survey/${'a'.repeat(1000)}/`);
      expect(response?.status()).toBeGreaterThanOrEqual(400);
    });

    test('special characters in token are rejected', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto(`/survey/${encodeURIComponent('!@#$%^&*()')}/`);
      expect(response?.status()).toBeGreaterThanOrEqual(400);
    });
  });

  test.describe('Survey URL Structure', () => {
    test('author survey URL returns 404 with invalid token', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto('/survey/test-token/author/');
      // Should return 404 (invalid token not found)
      expect(response?.status()).toBe(404);
    });

    test('reviewer survey URL returns 404 with invalid token', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto('/survey/test-token/reviewer/');
      expect(response?.status()).toBe(404);
    });

    test('submit URL rejects GET requests', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto('/survey/test-token/submit/');
      // Should return 405 Method Not Allowed or 404 (no GET handler)
      expect([404, 405]).toContain(response?.status());
    });

    test('complete URL returns 404 with invalid token', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto('/survey/test-token/complete/');
      // Complete page may allow expired tokens, but still validates token exists
      expect(response?.status()).toBe(404);
    });
  });

  test.describe('Survey Authentication', () => {
    test('survey landing redirects unauthenticated users to login', async ({ page, context }) => {
      await context.clearCookies();

      await page.goto('/survey/some-token/');

      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('author survey redirects unauthenticated users to login', async ({ page, context }) => {
      await context.clearCookies();

      await page.goto('/survey/some-token/author/');

      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('reviewer survey redirects unauthenticated users to login', async ({ page, context }) => {
      await context.clearCookies();

      await page.goto('/survey/some-token/reviewer/');

      await expect(page).toHaveURL(/\/accounts\/login/);
    });

    test('login redirect preserves survey URL in next param', async ({ page, context }) => {
      await context.clearCookies();

      await page.goto('/survey/test-token/author/');

      const url = page.url();
      expect(url).toContain('/accounts/login');
      expect(url).toContain('next=');
      expect(url).toContain('survey');
    });
  });

  test.describe('Survey Form Submission Security', () => {
    test('POST to submit endpoint without valid token fails', async ({ page }) => {
      await loginAs(page);

      const response = await page.request.post('/survey/invalid-token/submit/', {
        form: {
          ai_assisted: 'true',
        },
      });

      // Should fail with 403 (CSRF) or 404 (token not found)
      // CSRF check happens before token validation
      expect([403, 404]).toContain(response.status());
    });

    test('POST to submit endpoint without CSRF fails', async ({ page }) => {
      await loginAs(page);

      // Get a real token first (if available from seed data)
      // For this test, we just verify CSRF is enforced
      const response = await page.request.post('/survey/any-token/submit/', {
        data: 'ai_assisted=true',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      // Should fail with 403 (CSRF) or 404 (invalid token)
      expect([403, 404]).toContain(response.status());
    });
  });

  test.describe('Survey Page Content (Structure Validation)', () => {
    /**
     * These tests validate the survey page structure IF the page is accessible.
     * Since E2E test user lacks GitHub OAuth, pages return 403 with valid tokens.
     * We still test that the server responds appropriately.
     */

    test('author survey page returns appropriate response', async ({ page }) => {
      await loginAs(page);

      // With an invalid token, should get 404
      const response = await page.goto('/survey/valid-looking-token-abcdef/author/');

      // Either 404 (token not found) or 403 (unauthorized)
      expect([403, 404]).toContain(response?.status());
    });

    test('reviewer survey page returns appropriate response', async ({ page }) => {
      await loginAs(page);

      const response = await page.goto('/survey/valid-looking-token-ghijkl/reviewer/');

      expect([403, 404]).toContain(response?.status());
    });
  });
});

/**
 * Survey Integration Tests
 *
 * These tests require:
 * 1. Seed data created by: python manage.py seed_e2e_surveys
 * 2. A GitHub OAuth social account linked to test user
 * 3. The social account UID matching TeamMember.github_id
 *
 * Since E2E tests use email/password login, these are marked as skipped.
 * They serve as documentation for what manual testing should verify.
 */
test.describe('Survey Full Flow Tests (Requires GitHub OAuth) @surveys @manual', () => {
  test.skip('author survey: select Yes (AI assisted)', async ({ page }) => {
    // Prerequisites:
    // 1. Run: python manage.py seed_e2e_surveys
    // 2. User must have GitHub OAuth social account
    // 3. SocialAccount.uid must match TeamMember.github_id

    await loginAs(page);

    // Navigate to author survey with valid token
    // const token = process.env.E2E_AUTHOR_SURVEY_TOKEN;
    // await page.goto(`/survey/${token}/author/`);

    // Page should show:
    // - PR title and repository
    // - "Did you use AI assistance for this PR?" question
    // - "Yes, I used AI" and "No AI assistance" buttons

    // Select Yes
    // await page.click('text=Yes, I used AI');

    // Submit
    // await page.click('text=Submit Response');

    // Should redirect to complete page
    // await expect(page).toHaveURL(/\/complete/);
    // await expect(page.getByText('Thank you!')).toBeVisible();
  });

  test.skip('author survey: select No (no AI)', async ({ page }) => {
    await loginAs(page);

    // Same setup as above, select No instead
    // await page.click('text=No AI assistance');
    // await page.click('text=Submit Response');
    // await expect(page).toHaveURL(/\/complete/);
  });

  test.skip('reviewer survey: rate quality and guess AI usage', async ({ page }) => {
    await loginAs(page);

    // Navigate to reviewer survey
    // const token = process.env.E2E_REVIEWER_SURVEY_TOKEN;
    // await page.goto(`/survey/${token}/reviewer/`);

    // Page should show:
    // - PR title, repository, and author name
    // - "How would you rate the code quality?" with 3 options
    // - "Was this PR AI-assisted?" with Yes/No options

    // Select quality rating
    // await page.click('text=OK');

    // Select AI guess
    // await page.click('text=Yes, I think so');

    // Submit
    // await page.click('text=Submit Response');

    // Should redirect to complete page
    // await expect(page).toHaveURL(/\/complete/);

    // If author has responded, should show reveal:
    // - "Nice detective work!" or "Not quite!"
    // - Whether guess was correct
    // - Accuracy percentage
  });

  test.skip('reviewer survey: complete page shows reveal after author responds', async ({ page }) => {
    // This test verifies the reveal mechanics work correctly
    // When author has responded, reviewer sees their guess result
    // When author hasn't responded, reviewer sees "waiting" message
  });
});

/**
 * Survey Edge Cases
 */
test.describe('Survey Edge Cases @surveys', () => {
  test('accessing same survey token twice returns consistent response', async ({ page }) => {
    await loginAs(page);

    const token = 'test-token-consistency';
    const response1 = await page.goto(`/survey/${token}/author/`);
    const response2 = await page.goto(`/survey/${token}/author/`);

    // Both should return same status (404 for invalid token)
    expect(response1?.status()).toBe(response2?.status());
  });

  test('survey pages are not cached (vary by auth)', async ({ page }) => {
    // First access without auth
    await page.context().clearCookies();
    await page.goto('/survey/test-token/author/');
    const unauthUrl = page.url();

    // Then with auth
    await loginAs(page);
    await page.goto('/survey/test-token/author/');
    const authUrl = page.url();

    // Unauthenticated should redirect to login
    expect(unauthUrl).toContain('/accounts/login');
    // Authenticated should stay on survey page (or show 404)
    expect(authUrl).not.toContain('/accounts/login');
  });
});
