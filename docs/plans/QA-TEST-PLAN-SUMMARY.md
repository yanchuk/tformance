# QA Test Plan Summary — Public OSS Analytics 10-Feature Release

**Prepared by:** QA Engineer
**Date:** 2026-02-15
**Status:** Ready for Implementation
**Current Test Status:** ✅ 247/247 passing (0 failures)

---

## Executive Summary

This document provides a **comprehensive QA strategy** for testing 10 improvements to the public OSS analytics pages. The plan follows Tformance's established TDD patterns (Red-Green-Refactor) and leverages the existing test infrastructure at `apps/public/tests/`.

### Test Coverage Scope

| Category | Test Files | Test Count (Target) | Priority |
|----------|-----------|---------------------|----------|
| **Aggregations** | `test_aggregations.py` | +45 new tests | 🔴 CRITICAL |
| **Security Isolation** | `test_security.py` | +15 new tests | 🔴 CRITICAL |
| **Data Pipeline** | `test_tasks.py` | +20 new tests | 🟠 HIGH |
| **Regression (Story 4)** | `test_member_collision.py` | +5 new tests | 🔴 CRITICAL |
| **Views/Templates** | `test_views.py` | +10 new tests | 🟡 MEDIUM |
| **E2E Browser** | `tests/e2e/public-pages.spec.ts` | +12 new tests | 🟡 MEDIUM |

**Total New Tests:** ~107 tests (targeting **350+ total** test suite size)

---

## Current State Analysis

### ✅ What's Working

1. **Existing Test Infrastructure:**
   - 247 passing tests across 11 test files
   - Parallel test execution (pytest-xdist, 8 workers)
   - Factory-based test data generation (`TeamFactory`, `PullRequestFactory`, etc.)
   - PostgreSQL-specific test patterns (PERCENTILE_CONT, JSONB)
   - Security isolation testing (private teams never leak)

2. **Test Files Structure:**
   ```
   apps/public/tests/
   ├── test_models.py          ✅ Model creation/validation
   ├── test_views.py           ✅ View responses, status codes
   ├── test_services.py        ✅ Service layer logic
   ├── test_aggregations.py    ✅ Metric computations (REFERENCE PATTERN)
   ├── test_security.py        ✅ Data isolation (private team exclusion)
   ├── test_seo.py             ✅ Meta tags, JSON-LD, sitemap
   ├── test_tasks.py           ✅ Celery tasks
   ├── test_middleware.py      ✅ AI crawler logging
   ├── test_cloudflare.py      ✅ Cache purge
   └── test_request_form.py    ✅ Repo request form
   ```

3. **Key Testing Patterns Established:**
   - `setUpTestData()` for class-level fixtures (performance optimization)
   - `cache.clear()` in `setUp()` to avoid cache pollution
   - Simple `assert` statements (not `self.assertEqual`)
   - `# noqa: TEAM001` for intentional cross-team queries
   - Mock external APIs (GitHub, Groq) to avoid real API calls

### 🔍 What Needs Testing (The 10 Features)

| # | Feature | Files to Test | Key Risk Areas |
|---|---------|---------------|----------------|
| 1 | **Repos Analyzed List** | `test_aggregations.py` | Empty team, non-merged PRs |
| 2 | **Combined Cycle Time + AI Chart** | E2E only (template) | Chart.js dual-axis rendering |
| 3 | **PR Size Distribution** | `test_aggregations.py` | Boundary values (51, 201, 501, 1001 lines) |
| 4 | **PR Author Correctness** | `test_member_collision.py` | 🔴 **REGRESSION BUG** — github_id=0 collision |
| 5 | **Team Member Breakdown** | `test_aggregations.py` | Top 20 limit, avatar URL handling |
| 6 | **Org Logo Display** | E2E only (template) | Image loading, fallback |
| 7 | **Top Reviewers (10 limit)** | `test_aggregations.py` | Limit enforcement |
| 8 | **Enhanced PR Table** | `test_aggregations.py` | Type/tech/size data completeness |
| 9 | **Tech/PR Type Trends** | `test_aggregations.py` | Missing LLM data, multi-category PRs |
| 10 | **Data Pipeline Tasks** | `test_tasks.py` | Groq batch failures, GitHub API errors |

---

## Critical Test Requirements

### 🔴 Priority 1: Security Isolation (ZERO TOLERANCE)

**Rule:** Private team data must NEVER appear on public pages.

**Test Strategy:**
```python
# Pattern from test_security.py
@classmethod
def setUpTestData(cls):
    # Public team (should appear)
    cls.public_team = TeamFactory()
    cls.public_profile = PublicOrgProfile.objects.create(
        team=cls.public_team,
        public_slug="visible-org",
        is_public=True,  # ← KEY FIELD
    )

    # Private team (MUST be excluded everywhere)
    cls.private_team = TeamFactory()
    cls.private_profile = PublicOrgProfile.objects.create(
        team=cls.private_team,
        public_slug="hidden-org",
        is_public=False,  # ← PRIVATE
    )

def test_new_feature_excludes_private_org(self):
    result = new_aggregation_function(self.public_team.id, year=2026)
    # Assert private team data never leaks
    assert "hidden-org" not in str(result)
```

**Security Tests Required for ALL 10 Features:**
- [ ] `test_repos_analyzed_excludes_private_org`
- [ ] `test_pr_size_distribution_excludes_private_org`
- [ ] `test_member_breakdown_excludes_private_members`
- [ ] `test_enhanced_pr_table_excludes_private_prs`
- [ ] `test_tech_trends_excludes_private_data`
- [ ] `test_pr_type_trends_excludes_private_data`
- [ ] `test_sync_task_skips_private_orgs`

---

## Story-by-Story Test Plan

### Story 1: Repos Analyzed List

**Test Class:** `ComputeReposAnalyzedTests` (in `test_aggregations.py`)

**Test Methods:**
1. ✅ `test_returns_all_repos` — Verify all unique repos returned
2. ✅ `test_sorted_by_pr_count_desc` — Verify descending sort
3. ✅ `test_includes_pr_counts` — Verify PR counts per repo
4. ✅ `test_includes_github_urls` — Verify URL format
5. ✅ `test_empty_team_returns_empty` — Edge case: no PRs
6. ✅ `test_excludes_non_merged_prs` — Only merged PRs counted
7. 🔒 `test_excludes_private_org_repos` — Security

**Setup Data:**
```python
@classmethod
def setUpTestData(cls):
    cls.team = TeamFactory()
    cls.member = TeamMemberFactory(team=cls.team)
    now = timezone.now()

    # 3 different repos with different PR counts
    PullRequestFactory.create_batch(10, team=cls.team, github_repo="org/backend")
    PullRequestFactory.create_batch(5, team=cls.team, github_repo="org/frontend")
    PullRequestFactory.create_batch(2, team=cls.team, github_repo="org/mobile")
```

**Edge Cases:**
- Empty team (0 PRs) → returns `[]`
- Non-merged PRs (state='open' or 'closed') → excluded
- Private org repos → never appear

---

### Story 3: PR Size Distribution

**Test Class:** `ComputePrSizeDistributionTests` (in `test_aggregations.py`)

**Test Methods:**
1. ✅ `test_returns_five_buckets` — XS, S, M, L, XL
2. ✅ `test_bucket_counts` — Verify counts per bucket
3. ✅ `test_bucket_percentages` — Verify percentages sum to 100%
4. ✅ `test_edge_case_zero_additions_and_deletions` — 0+0 = XS bucket
5. ✅ `test_boundary_value_51_lines_is_small` — Exactly 51 → S (not XS)
6. ✅ `test_boundary_value_201_lines_is_medium` — Exactly 201 → M
7. ✅ `test_boundary_value_501_lines_is_large` — Exactly 501 → L
8. ✅ `test_boundary_value_1001_lines_is_xl` — Exactly 1001 → XL
9. ✅ `test_empty_team_returns_zero_counts` — All buckets = 0

**Bucket Definitions:**
```python
XS: 1-50 lines
S:  51-200 lines
M:  201-500 lines
L:  501-1000 lines
XL: 1001+ lines
```

**Critical Boundary Tests:**
- 50 → XS, 51 → S
- 200 → S, 201 → M
- 500 → M, 501 → L
- 1000 → L, 1001 → XL

---

### Story 4: PR Author Correctness (REGRESSION BUG FIX)

**⚠️ CRITICAL BUG:** Cached PRs from GraphQL have `author_id=0`, causing all PRs to collide on the same GitHub ID, resulting in wrong author attribution.

**Root Cause:**
- `RealProjectSeeder._create_team_members()` uses `github_id` as dict key
- `RealProjectSeeder._find_member()` looks up by `github_id` first
- When all cached PRs have `author_id=0`, they all map to the SAME key → first author wins, all other authors are ignored

**Test File:** `apps/metrics/tests/seeding/test_member_collision.py` (NEW FILE)

**Test Class 1:** `CreateTeamMembersCollisionTests`

Test Methods:
1. 🔴 `test_multiple_contributors_with_github_id_zero_create_distinct_members`
   - Create 3 contributors, all with `github_id=0`
   - Assert 3 distinct `TeamMember` records created (not collapsed to 1)
   - Assert all 3 usernames are distinct

2. 🔴 `test_find_member_with_github_id_zero_resolves_by_username`
   - Create members with `github_id=0` but different usernames
   - Call `_find_member(login="bob", github_id=0)`
   - Assert returns Bob, NOT the first cached member (Alice)

3. 🔴 `test_members_by_github_id_dict_does_not_cache_zero`
   - Create members with `github_id=0`
   - Assert `"0"` is NOT in `_members_by_github_id` dict
   - Prevents collision at the source

4. 🔴 `test_mixed_zero_and_nonzero_ids_handled_correctly`
   - Create mix of valid GitHub IDs and `id=0`
   - Assert valid IDs are in `_members_by_github_id`
   - Assert `"0"` is NOT in `_members_by_github_id`
   - Assert both are in `_members_by_username`

**Test Class 2:** `CreatePrsWithZeroAuthorIdTests`

Test Method:
1. 🔴 `test_prs_assign_correct_author_when_all_ids_zero`
   - Create 3 PRs: Alice #1, Bob #1, Alice #2
   - All with `author_id=0` (simulating cache)
   - Assert PR #1 author = Alice
   - Assert PR #2 author = Bob (NOT Alice!)
   - Assert PR #3 author = Alice

**Expected Fix:**
```python
# In RealProjectSeeder._create_team_members()
for contributor in contributors:
    member = TeamMember.objects.create(...)

    # BEFORE (BUG):
    self._members_by_github_id[str(contributor.github_id)] = member

    # AFTER (FIX):
    if contributor.github_id != 0:  # ← Skip zero IDs
        self._members_by_github_id[str(contributor.github_id)] = member

    self._members_by_username[contributor.github_login] = member  # Always cache by username

# In RealProjectSeeder._find_member()
def _find_member(self, login: str, github_id: int) -> TeamMember | None:
    # BEFORE (BUG):
    if member := self._members_by_github_id.get(str(github_id)):
        return member

    # AFTER (FIX):
    if github_id != 0:  # ← Skip lookup by zero
        if member := self._members_by_github_id.get(str(github_id)):
            return member

    return self._members_by_username.get(login)  # Always fallback to username
```

---

### Story 8: Enhanced PR Table

**Test Class:** `ComputeRecentPrsEnhancedTests` (in `test_aggregations.py`)

**New Fields to Test:**
- `pr_type` (from `llm_summary.summary.type` or inferred from labels)
- `tech_categories` (from `llm_summary.tech.categories`)
- `size_label` (XS/S/M/L/XL based on additions + deletions)
- `additions` (line count)
- `deletions` (line count)

**Test Methods:**
1. ✅ `test_includes_pr_type`
2. ✅ `test_includes_tech_categories`
3. ✅ `test_includes_size_label`
4. ✅ `test_includes_additions_deletions`
5. ✅ `test_pr_with_no_llm_summary_falls_back_to_labels`
6. ✅ `test_pr_with_no_llm_no_labels_returns_unknown`

**Fallback Logic Testing:**
```python
# Priority order:
1. llm_summary.summary.type → "feature"
2. labels contain "bug" → "bugfix"
3. labels contain "docs" → "docs"
4. No data → "unknown"
```

---

### Story 9: Technology & PR Type Trends

**Test Class 1:** `ComputeTechCategoryTrendsTests`

Test Methods:
1. ✅ `test_returns_monthly_data`
2. ✅ `test_january_categories` — Verify category counts
3. ✅ `test_february_categories`
4. ✅ `test_sorted_by_month` — Ascending month order
5. ✅ `test_handles_missing_llm_data` — Don't crash on NULL
6. ✅ `test_pr_with_multiple_categories` — Count in each
7. ✅ `test_empty_team_returns_empty`

**Test Class 2:** `ComputePrTypeTrendsTests`

Test Methods:
1. ✅ `test_returns_monthly_data`
2. ✅ `test_january_types` — Verify type counts
3. ✅ `test_february_types`
4. ✅ `test_handles_unknown_type` — Missing data → "unknown"
5. ✅ `test_sorted_by_month`
6. ✅ `test_empty_team_returns_empty`

---

### Story 10: Automated Daily Data Refresh Pipeline

**Test File:** `apps/public/tests/test_tasks.py`

**Test Class 1:** `SyncPublicReposTaskTests`

Test Methods:
1. 🟠 `test_fetches_new_prs_for_all_public_orgs` — Mock GitHub API
2. 🟠 `test_uses_incremental_sync` — Verify `since_date` parameter
3. 🟠 `test_handles_api_errors_gracefully` — 403 rate limit
4. 🟠 `test_idempotency_running_twice_does_not_duplicate`

**Mock Strategy:**
```python
@patch("apps.public.tasks.GitHubGraphQLFetcher")
@patch("apps.public.tasks.RealProjectSeeder")
def test_fetches_new_prs(self, mock_seeder, mock_fetcher):
    mock_fetcher.return_value.fetch_prs_with_details.return_value = []
    sync_public_repos_task()
    assert mock_fetcher.called
```

**Test Class 2:** `ProcessPublicPrsLlmTaskTests`

Test Methods:
1. 🟠 `test_processes_only_null_llm_summary_prs`
2. 🟠 `test_uses_groq_batch_mode` — Verify batch API call
3. 🟠 `test_handles_groq_batch_failure` — Exception handling
4. 🟠 `test_uses_cheapest_model` — `openai/gpt-oss-20b`

**Test Class 3:** `GeneratePublicInsightsTaskTests`

Test Methods:
1. 🟠 `test_generates_insights_for_all_public_orgs`
2. 🟠 `test_uses_last_30_days_window`
3. 🟠 `test_stores_insights_as_daily_insight_records`

**Test Class 4:** `RunDailyPublicPipelineTests`

Test Methods:
1. 🟠 `test_chains_tasks_in_correct_order` — sync → llm → stats
2. 🟠 `test_stops_chain_on_sync_failure` — Error propagation

---

## Error Handling & Edge Cases

### GitHub API Errors

**Test Class:** `GitHubApiErrorHandlingTests` (in `test_tasks.py`)

1. 🟡 `test_rate_limited_403_error` — Don't crash, log error
2. 🟡 `test_network_timeout_error` — Retry with exponential backoff
3. 🟡 `test_invalid_token_401_error` — Alert admin

### Groq Batch Failures

**Test Class:** `GroqBatchErrorHandlingTests` (in `test_tasks.py`)

1. 🟡 `test_batch_submit_fails` — Exception handling
2. 🟡 `test_partial_batch_failure` — Process successful PRs, log failures

### Empty/Invalid Data

**Test Class:** `EmptyDataEdgeCasesTests` (in `test_aggregations.py`)

1. 🟡 `test_org_with_zero_merged_prs` — Don't crash stats computation
2. 🟡 `test_pr_with_malformed_llm_summary` — Graceful degradation
3. 🟡 `test_pr_with_zero_additions_and_deletions` — Handle edge case

---

## E2E Test Plan (Playwright)

**Test File:** `tests/e2e/public-pages.spec.ts`

### Visual Rendering Tests

```typescript
test.describe('Public Pages - Enhanced Features', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/open-source/posthog/');
  });

  test('renders repos analyzed list', async ({ page }) => {
    const reposSection = page.locator('text=Repositories Analyzed');
    await expect(reposSection).toBeVisible();
  });

  test('renders combined cycle time + AI adoption chart', async ({ page }) => {
    const chartCanvas = page.locator('canvas#combined-chart');
    await expect(chartCanvas).toBeVisible();
  });

  test('enhanced PR table shows type, size, tech columns', async ({ page }) => {
    await expect(page.locator('th:has-text("Type")')).toBeVisible();
    await expect(page.locator('th:has-text("Size")')).toBeVisible();
    await expect(page.locator('th:has-text("Tech")')).toBeVisible();
  });

  test('org image displays at top', async ({ page }) => {
    const orgImage = page.locator('img[alt*="PostHog"]').first();
    await expect(orgImage).toBeVisible();
  });

  test('top reviewers limited to 10', async ({ page }) => {
    const reviewerRows = page.locator('table:has-text("Top Reviewers") tbody tr');
    const count = await reviewerRows.count();
    expect(count).toBeLessThanOrEqual(10);
  });
});
```

### PostHog Analytics Events

```typescript
test('PostHog events fire on page load', async ({ page }) => {
  await page.addInitScript(() => {
    (window as any).posthog = {
      capture: (event: string, props: any) => {
        console.log('PostHog event:', event, props);
      }
    };
  });

  await page.goto('/open-source/posthog/');
  // Verify events captured
});
```

---

## Cache TTL Change Testing

**Change:** Cache TTL increased from 1 hour to 24 hours

**Test Strategy:**
1. 🟡 `test_cache_ttl_is_24_hours` (in `test_views.py`)
   - Verify `Cache-Control: public, max-age=86400`
2. 🟡 `test_cache_invalidation_after_sync` (in `test_cloudflare.py`)
   - Verify Cloudflare purge after daily sync

---

## PostHog Analytics Testing

**Events to Track:**
- `public_page_view` (on all pages)
- `public_org_detail_view` (with org slug)
- `public_repo_request` (form submission)

**Test Approach:**
```python
# Manual QA only — PostHog events verified in browser console
# E2E test can mock PostHog and check console.log output
```

---

## Regression Testing Strategy

### Critical Regression Test: All 247 Existing Tests Must Pass

**Command:**
```bash
make test  # Run all tests in parallel
```

**Expected Outcome:**
- ✅ 247/247 existing tests pass (before adding new tests)
- ✅ 350+/350+ tests pass (after adding new tests)

**CI Pipeline Integration:**
```yaml
# .github/workflows/ci.yml
- name: Run all tests
  run: make test
- name: Fail if any test fails
  run: exit 1
```

---

## Test Execution Plan

### Phase 1: TDD Regression Tests (Story 4) — Day 1

**Priority:** 🔴 CRITICAL
**File:** `apps/metrics/tests/seeding/test_member_collision.py`

1. Write 5 failing tests for github_id=0 collision bug
2. Implement fix in `RealProjectSeeder`
3. Verify all 5 tests pass
4. Run full test suite (ensure no regressions)

**Exit Criteria:** ✅ All 5 new tests pass, ✅ 247 existing tests pass

---

### Phase 2: Aggregation Function Tests — Day 2-3

**Priority:** 🔴 CRITICAL
**File:** `apps/public/tests/test_aggregations.py`

**Test Classes to Add:**
1. `ComputeReposAnalyzedTests` (7 tests)
2. `ComputePrSizeDistributionTests` (9 tests)
3. `ComputeRecentPrsEnhancedTests` (6 tests)
4. `ComputeTechCategoryTrendsTests` (7 tests)
5. `ComputePrTypeTrendsTests` (6 tests)

**Approach:**
- Follow existing pattern from `test_aggregations.py` EXACTLY
- Use `setUpTestData()` for class-level fixtures
- Use factories for test data
- Test security isolation for each function

**Exit Criteria:** ✅ 35 new tests pass, ✅ 282 total tests pass

---

### Phase 3: Data Pipeline Tests — Day 4

**Priority:** 🟠 HIGH
**File:** `apps/public/tests/test_tasks.py`

**Test Classes to Add:**
1. `SyncPublicReposTaskTests` (4 tests)
2. `ProcessPublicPrsLlmTaskTests` (4 tests)
3. `GeneratePublicInsightsTaskTests` (3 tests)
4. `RunDailyPublicPipelineTests` (2 tests)
5. `GitHubApiErrorHandlingTests` (3 tests)
6. `GroqBatchErrorHandlingTests` (2 tests)
7. `EmptyDataEdgeCasesTests` (3 tests)

**Exit Criteria:** ✅ 21 new tests pass, ✅ 303 total tests pass

---

### Phase 4: Security & View Tests — Day 5

**Priority:** 🔴 CRITICAL
**Files:** `test_security.py`, `test_views.py`

**Security Tests to Add:**
- `test_repos_analyzed_excludes_private_org`
- `test_pr_size_distribution_excludes_private_org`
- `test_member_breakdown_excludes_private_members`
- `test_enhanced_pr_table_excludes_private_prs`
- `test_tech_trends_excludes_private_data`
- `test_pr_type_trends_excludes_private_data`
- `test_sync_task_skips_private_orgs`

**Exit Criteria:** ✅ 15 new tests pass, ✅ 318 total tests pass

---

### Phase 5: E2E Browser Tests — Day 6

**Priority:** 🟡 MEDIUM
**File:** `tests/e2e/public-pages.spec.ts`

**Tests to Add:**
- Repos analyzed list rendering
- Combined chart rendering
- PR size chart rendering
- Enhanced PR table columns
- Org logo display
- Team member avatars
- Top reviewers limit (10)
- Tech trends chart
- PR type trends chart
- PostHog event tracking

**Exit Criteria:** ✅ 12 E2E tests pass

---

### Phase 6: Full Regression & Manual QA — Day 7

**Manual QA Checklist:**
- [ ] All charts render on desktop (1920px)
- [ ] All charts render on mobile (375px)
- [ ] Org logos load correctly (with fallback)
- [ ] Team member avatars load correctly
- [ ] PostHog events fire in browser console
- [ ] Cache headers correct (`Cache-Control: public, max-age=86400`)
- [ ] No private org data leaks (manual audit)
- [ ] All 350+ automated tests pass

**Exit Criteria:** ✅ Full test suite passes, ✅ Manual QA sign-off

---

## Test Data Requirements

### Factory Usage

**Required Factories:**
- `TeamFactory` — Create teams
- `TeamMemberFactory` — Create contributors
- `PullRequestFactory` — Create PRs
- `PRReviewFactory` — Create reviews
- `PRCheckRunFactory` — Create CI checks
- `PublicOrgProfileFactory` (NEW) — Create public org profiles
- `PublicOrgStatsFactory` (NEW) — Create pre-computed stats

**Data Setup Pattern:**
```python
@classmethod
def setUpTestData(cls):
    cls.team = TeamFactory()
    cls.member = TeamMemberFactory(team=cls.team)
    now = timezone.now()

    # Create test data with explicit dates/values
    PullRequestFactory(
        team=cls.team,
        author=cls.member,
        state="merged",
        pr_created_at=datetime(2026, 1, 1, tzinfo=UTC),
        merged_at=datetime(2026, 1, 2, tzinfo=UTC),
        cycle_time_hours=Decimal("10.0"),
    )
```

---

## Performance Testing

### Database Query Performance

**Target:** All aggregation functions < 500ms on 167K PRs

**Test Strategy:**
```python
def test_compute_repos_analyzed_performance(self):
    import time
    start = time.time()
    result = compute_repos_analyzed(self.team.id, year=2026)
    duration = time.time() - start
    assert duration < 0.5, f"Query took {duration}s (expected < 0.5s)"
```

**Critical Queries:**
- `compute_team_summary()` — Single query with aggregates
- `compute_pr_size_distribution()` — Single query with CASE
- `compute_tech_category_trends()` — Single query with JSONB unnesting

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:17
        env:
          POSTGRES_PASSWORD: postgres
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: make install
      - name: Run tests
        run: make test
      - name: Run E2E tests
        run: make e2e
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Private data leak** | LOW | 🔴 CRITICAL | ✅ Comprehensive security test suite |
| **GitHub API rate limit** | MEDIUM | 🟠 HIGH | ✅ Incremental sync, error handling |
| **Groq batch failure** | LOW | 🟡 MEDIUM | ✅ Retry logic, fallback to sync mode |
| **Chart rendering bug** | MEDIUM | 🟡 MEDIUM | ✅ E2E tests, manual QA |
| **Cache invalidation failure** | LOW | 🟡 MEDIUM | ✅ Cloudflare purge tests |
| **Performance regression** | LOW | 🟠 HIGH | ✅ Query performance tests |

---

## Success Metrics

### Test Coverage Targets

- **Unit Test Coverage:** 95%+ (critical paths)
- **Security Test Coverage:** 100% (all public endpoints)
- **E2E Test Coverage:** All user-facing features

### Quality Gates

- ✅ All 350+ tests pass (0 failures)
- ✅ No private data leaks (manual audit + automated tests)
- ✅ All aggregation functions < 500ms
- ✅ E2E tests pass on Chrome, Firefox, Safari
- ✅ Manual QA sign-off (charts, images, PostHog)

---

## Conclusion

This test plan provides **comprehensive coverage** for all 10 features with a strong emphasis on:

1. **Security-first testing** — Private data isolation verified at every layer
2. **TDD approach** — Red-Green-Refactor for Story 4 regression bug
3. **Pattern consistency** — All tests follow `test_aggregations.py` reference pattern
4. **Edge case coverage** — Empty data, malformed JSON, API failures
5. **Performance validation** — Query performance targets enforced

**Estimated Test Count:** 350+ total tests (107 new + 247 existing)
**Estimated Implementation Time:** 7 days (1 developer)
**Risk Level:** LOW (with comprehensive test coverage)

---

**Next Steps:**
1. ✅ Review this plan with team lead
2. ✅ Implement Phase 1 (Story 4 TDD regression tests)
3. ✅ Implement Phases 2-6 sequentially
4. ✅ Manual QA sign-off before production deployment

**Questions/Clarifications:**
- Should we add load testing for 167K+ PRs?
- Do we need accessibility (a11y) tests for charts?
- Should PostHog events be tested in E2E or manual QA only?
