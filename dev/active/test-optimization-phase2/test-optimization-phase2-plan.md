# Test Optimization Phase 2 - Plan

**Last Updated:** 2026-01-11
**Status:** ✅ COMPLETE
**Approach:** Strict TDD (Red-Green-Refactor)

---

## Executive Summary

Convert 2 high-impact test files to use `setUpTestData` and reusable mixins, following strict TDD practices. This phase focuses on the **safest conversions** identified by plan-reviewer analysis.

### Scope

| File | Classes | Conversion Rate | Risk Level |
|------|---------|-----------------|------------|
| `test_pr_list_service.py` | 10 → 11 | 100% | Low |
| `test_github_app_installation.py` | 12 | 83% (~10 classes) | Medium |

**Total: ~21 classes to convert**

---

## Current State Analysis

### test_pr_list_service.py (apps/metrics/tests/)
- **11 test classes** with identical setUp pattern
- Pattern: `team + member1 + member2` (TeamMemberFactory)
- All tests are **read-only** - safe for setUpTestData
- **Recommended mixin:** `TeamWithMembersMixin`

### test_github_app_installation.py (apps/integrations/tests/)
- **12 test classes** with simple setUp pattern
- Pattern: `team` only (TeamFactory)
- All classes have `tearDown()` calling `unset_current_team()`
- Some tests use `set_current_team()` - need cleanup handling
- **Recommended approach:** Simple setUpTestData + custom tearDown

---

## Proposed Future State

### After Conversion

```python
# test_pr_list_service.py - BEFORE
class TestGetPrsQueryset(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")

# test_pr_list_service.py - AFTER
class TestGetPrsQueryset(TeamWithMembersMixin, TestCase):
    # Uses TeamWithMembersMixin: self.team, self.member1, self.member2, self.member3
    pass  # No setUp needed
```

```python
# test_github_app_installation.py - BEFORE
class TestGitHubAppInstallationModelCreation(TestCase):
    def setUp(self):
        self.team = TeamFactory()

    def tearDown(self):
        unset_current_team()

# test_github_app_installation.py - AFTER
class TestGitHubAppInstallationModelCreation(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def tearDown(self):
        unset_current_team()
```

---

## Implementation Phases

### Phase 1: test_pr_list_service.py (Low Risk)

**TDD Approach:**
1. RED: Run existing tests (should pass - baseline)
2. GREEN: Convert one class at a time
3. REFACTOR: Remove duplicate code after each conversion

**Classes to Convert (all 11):**
1. `TestGetPrsQueryset`
2. `TestGetPrStats`
3. `TestGetFilterOptions`
4. `TestPrSizeBuckets`
5. `TestTechCategoriesFilter`
6. `TestEffectiveTechCategories`
7. `TestEffectiveAIDetection`
8. `TestAICategoryFilter`
9. `TestAICategoryFilterOptions`
10. `TestReviewerNameFilterPendingState`
11. `TestAICategoryStats`

### Phase 2: test_github_app_installation.py (Medium Risk)

**Special Considerations:**
- Preserve `tearDown()` for `unset_current_team()`
- Tests using `set_current_team()` modify global state - OK since tearDown cleans it

**Classes to Convert (10 of 12):**
1. `TestGitHubAppInstallationModelCreation`
2. `TestGitHubAppInstallationUniqueConstraint`
3. `TestGitHubAppInstallationTeamRelationship`
4. `TestGitHubAppInstallationDefaults`
5. `TestGitHubAppInstallationEncryptedToken`
6. `TestGitHubAppInstallationAdditionalFields`
7. `TestGitHubAppInstallationDbTable`
8. `TestGitHubAppInstallationGetAccessToken`
9. `TestGetAccessTokenRaceCondition`
10. `TestGetAccessTokenIsActiveCheck`

**Classes to Keep setUp (2):**
- `TestSuspendedVsDeletedErrorMessages` - May modify installation state
- `TestRaceBetweenWebhookAndSyncCheck` - Race condition testing

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data pollution between tests | Low | High | Only convert read-only tests |
| tearDown not called | Medium | Medium | Preserve tearDown in each class |
| Test failures after conversion | Low | Low | Run tests after each class conversion |
| Mixin doesn't match fixture needs | Low | Low | Check each class's setUp before converting |

---

## Success Metrics

| Metric | Target |
|--------|--------|
| All 130 tests pass | Required |
| Classes converted | 21 of 23 |
| Lines of duplicate code removed | ~150 lines |
| Test execution time | Same or faster |

---

## Dependencies

- `apps/utils/tests/mixins.py` - TeamWithMembersMixin (already exists)
- Existing factories: TeamFactory, TeamMemberFactory
- No new migrations required
- No new dependencies required
