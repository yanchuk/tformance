# Test Optimization Phase 2 - Tasks

**Last Updated:** 2026-01-11

---

## Pre-flight Checklist

- [x] Baseline tests pass (130/130)
- [x] Plan reviewed by plan-reviewer agent
- [x] Documentation created
- [x] Start implementation

---

## Phase 1: test_pr_list_service.py (11 classes) ✅ COMPLETE

### Setup
- [x] **1.1** Read current file and verify setUp patterns match expectation
- [x] **1.2** Add import for TeamWithMembersMixin

### Class Conversions (TDD: verify tests pass after each)
- [x] **1.3** Convert `TestGetPrsQueryset` → TeamWithMembersMixin
- [x] **1.4** Convert `TestGetPrStats` → TeamWithMembersMixin
- [x] **1.5** Convert `TestGetFilterOptions` → TeamWithMembersMixin
- [x] **1.6** Convert `TestPrSizeBuckets` → TeamWithMembersMixin (no setUp needed - tests constants only)
- [x] **1.7** Convert `TestTechCategoriesFilter` → TeamWithMembersMixin
- [x] **1.8** Convert `TestEffectiveTechCategories` → TeamWithMembersMixin
- [x] **1.9** Convert `TestEffectiveAIDetection` → TeamWithMembersMixin
- [x] **1.10** Convert `TestAICategoryFilter` → TeamWithMembersMixin
- [x] **1.11** Convert `TestAICategoryFilterOptions` → TeamWithMembersMixin
- [x] **1.12** Convert `TestReviewerNameFilterPendingState` → custom setUpTestData (needs specific github_usernames)
- [x] **1.13** Convert `TestAICategoryStats` → TeamWithMembersMixin

### Verification
- [x] **1.14** Run all tests in file - verify 100% pass (97 tests)
- [x] **1.15** Clean up unused imports (kept TeamFactory, TeamMemberFactory - still needed)

---

## Phase 2: test_github_app_installation.py (12 classes) ✅ COMPLETE

### Setup
- [x] **2.1** Read current file and verify setUp/tearDown patterns
- [x] **2.2** Identify which classes can safely convert

### Class Conversions (TDD: verify tests pass after each)
- [x] **2.3** Convert `TestGitHubAppInstallationModelCreation`
- [x] **2.4** Convert `TestGitHubAppInstallationUniqueConstraint`
- [x] **2.5** Convert `TestGitHubAppInstallationTeamRelationship`
- [x] **2.6** Convert `TestGitHubAppInstallationDefaults`
- [x] **2.7** Convert `TestGitHubAppInstallationEncryptedToken`
- [x] **2.8** Convert `TestGitHubAppInstallationAdditionalFields`
- [x] **2.9** Convert `TestGitHubAppInstallationDbTable`
- [x] **2.10** Convert `TestGitHubAppInstallationGetAccessToken`
- [x] **2.11** Convert `TestGetAccessTokenRaceCondition`
- [x] **2.12** Convert `TestGetAccessTokenIsActiveCheck`

### Classes Kept with setUp
- [x] **2.13** `TestSuspendedVsDeletedErrorMessages` - kept setUp (modifies installation state)
- [x] **2.14** `TestRaceBetweenWebhookAndSyncCheck` - kept setUp (race condition testing)

### Verification
- [x] **2.15** Run all tests in file - verify 100% pass (33 tests)
- [x] **2.16** tearDown preserved in all classes for unset_current_team()

---

## Final Verification

- [x] **3.1** Run both converted files together - 130 tests pass in 7.29s
- [x] **3.2** Run full test suite - no regressions from our changes (pre-existing failures in slack_tasks unrelated)
- [x] **3.3** Baseline execution time: 9.03s → Current: 7.29s-11.26s (variable due to parallel execution)
- [x] **3.4** Update dev docs with results

---

## Acceptance Criteria

| Criteria | Status |
|----------|--------|
| All 130 tests pass | ✅ PASS |
| 21+ classes converted to setUpTestData | ✅ PASS (21 classes converted) |
| No regressions in full test suite | ✅ PASS (no new failures) |
| tearDown preserved where needed | ✅ PASS (all tearDown methods preserved) |
| Documentation updated | ✅ PASS |

---

## Notes

- Each class conversion should be followed by running that class's tests
- If a test fails after conversion, investigate before moving to next class
- Keep tearDown() methods - they clean up global state
