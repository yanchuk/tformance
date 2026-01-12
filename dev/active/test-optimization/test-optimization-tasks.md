# Test Optimization Tasks - Phase 2 Expansion

**Last Updated:** 2026-01-11
**Previous Work:** 2025-12-31 (seeding tests optimized, 70% improvement achieved)
**This Phase:** Expand setUpTestData pattern to remaining ~600 test classes

---

## Phase 2.1: Quick Wins

**Effort:** Small | **Risk:** Low | **Impact:** Foundation for larger changes

### Tasks

- [ ] **2.1.1** Baseline measurement
  ```bash
  time make test
  make test-slow
  ```
  - Acceptance: Record current timing (~53s from previous work)

- [ ] **2.1.2** Fix AIFeedbackFactory anti-pattern
  - File: `apps/feedback/factories.py:22`
  - Change: `factory.LazyAttribute(lambda obj: TeamMemberFactory(team=obj.team))`
  - To: `factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))`
  - Acceptance: No redundant DB writes when creating AIFeedback

- [ ] **2.1.3** Create TeamTestMixin base class
  - File: `apps/utils/tests/base.py` (new file)
  - Content: Shared setUpTestData with team, admin_user, member_user
  - Acceptance: Mixin can be used by test classes

- [ ] **2.1.4** Run feedback tests to verify factory fix
  ```bash
  pytest apps/feedback/tests/ -v
  ```
  - Acceptance: All feedback tests pass

---

## Phase 2.2: Metrics App Optimization

**Effort:** Large | **Risk:** Low | **Impact:** High (~200 classes)

### Priority Files (by setUp count)

- [ ] **2.2.1** `test_chart_views.py` (10 setUp methods)
  - Convert 10 identical setUp patterns to setUpTestData
  - Pattern: team, admin_user, member_user, membership
  - Acceptance: All tests pass, single DB setup per class

- [ ] **2.2.2** `test_pr_list_service.py` (10 setUp methods)
  - File: `apps/metrics/tests/test_pr_list_service.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.2.3** `test_trends_views.py` (11 setUp methods)
  - File: `apps/metrics/tests/test_trends_views.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.2.4** `test_security_isolation.py` (10 setUp methods)
  - File: `apps/metrics/tests/test_security_isolation.py`
  - Note: These tests REQUIRE isolation - verify carefully
  - Acceptance: Security tests still verify isolation correctly

- [ ] **2.2.5** `test_insight_rules.py` (8 setUp methods)
  - File: `apps/metrics/tests/test_insight_rules.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.2.6** Dashboard tests directory (30+ setUp methods)
  - Directory: `apps/metrics/tests/dashboard/`
  - Acceptance: Convert applicable tests

- [ ] **2.2.7** Models tests directory (15+ setUp methods)
  - Directory: `apps/metrics/tests/models/`
  - Acceptance: Convert applicable tests

- [ ] **2.2.8** Verify metrics app tests
  ```bash
  pytest apps/metrics/tests/ -v --tb=short
  ```
  - Acceptance: All tests pass (0 failures)

---

## Phase 2.3: Integrations App Optimization

**Effort:** Large | **Risk:** Medium | **Impact:** High (~150 classes)

**Important:** Skip GraphQL tests (require TransactionTestCase for asyncio)

### Priority Files

- [ ] **2.3.1** `test_views.py` (15 setUp methods)
  - File: `apps/integrations/tests/test_views.py`
  - Acceptance: Non-async tests use setUpTestData

- [ ] **2.3.2** `test_sync_logging.py` (15 setUp methods)
  - File: `apps/integrations/tests/test_sync_logging.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.3.3** `test_github_app_installation.py` (12 setUp methods)
  - File: `apps/integrations/tests/test_github_app_installation.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.3.4** `test_two_phase_pipeline.py` (10 setUp methods)
  - File: `apps/integrations/tests/test_two_phase_pipeline.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.3.5** `test_historical_sync.py` (9 setUp methods)
  - File: `apps/integrations/tests/test_historical_sync.py`
  - Acceptance: Tests use shared class-level fixtures

- [ ] **2.3.6** Remaining integration test files
  - Convert other files with 3+ setUp methods
  - Skip: `test_github_graphql_sync.py`, `test_github_graphql_sync_utils.py`
  - Acceptance: All non-async tests converted

- [ ] **2.3.7** Verify integrations app tests
  ```bash
  pytest apps/integrations/tests/ -v --tb=short
  ```
  - Acceptance: All tests pass (0 failures)

---

## Phase 2.4: Remaining Apps

**Effort:** Medium | **Risk:** Low | **Impact:** Medium

### Apps to Optimize

- [ ] **2.4.1** `apps/onboarding/tests/` (~40 classes)
  - Multiple setUp methods in views.py, copilot_step.py, etc.
  - Acceptance: Applicable tests converted

- [ ] **2.4.2** `apps/web/tests/` (~30 classes)
  - Multiple setUp methods
  - Acceptance: Applicable tests converted

- [ ] **2.4.3** `apps/auth/tests/` (~20 classes)
  - OAuth callback tests, etc.
  - Acceptance: Applicable tests converted

- [ ] **2.4.4** `apps/feedback/tests/` (~10 classes)
  - Acceptance: Applicable tests converted

- [ ] **2.4.5** `apps/teams/tests/` (~15 classes)
  - Acceptance: Applicable tests converted

- [ ] **2.4.6** `apps/users/tests/` (~5 classes)
  - Acceptance: Applicable tests converted

---

## Phase 2.5: Verification & Documentation

**Effort:** Small | **Risk:** Low | **Impact:** Long-term maintainability

### Tasks

- [ ] **2.5.1** Full test suite verification
  ```bash
  make test
  ```
  - Acceptance: All 4404+ tests pass

- [ ] **2.5.2** Performance measurement
  ```bash
  time make test
  make test-slow
  ```
  - Acceptance: Total time < 40s (down from 53s)

- [ ] **2.5.3** Update TESTING-GUIDE.md
  - Add setUpTestData patterns and when to use them
  - Document when to keep setUp (data modification, async)
  - Acceptance: Guide updated with clear examples

- [ ] **2.5.4** Update dev documentation
  - Mark this task as complete
  - Document final metrics
  - Acceptance: Documentation complete

---

## Progress Summary

| Phase | Status | Classes Converted | Time Saved |
|-------|--------|-------------------|------------|
| 2.1 Quick Wins | Pending | 0 | TBD |
| 2.2 Metrics | Pending | 0/~200 | TBD |
| 2.3 Integrations | Pending | 0/~150 | TBD |
| 2.4 Other Apps | Pending | 0/~100 | TBD |
| 2.5 Verification | Pending | N/A | TBD |

**Previous Result (Phase 1):** 180s → 53s (70% improvement)
**Target (Phase 2):** 53s → <40s (additional 25% improvement)

---

## Verification Commands

```bash
# Baseline
time make test
make test-slow

# Test specific app
pytest apps/metrics/tests/ -v --tb=short
pytest apps/integrations/tests/ -v --tb=short

# Single file verification
pytest apps/metrics/tests/test_chart_views.py -v --durations=10

# Full verification
make test
```

---

## Conversion Pattern Reference

```python
# BEFORE: Per-test setup (slow)
class TestMyView(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.admin_user = UserFactory()
        self.team.members.add(self.admin_user, through_defaults={"role": ROLE_ADMIN})
        self.client = Client()

# AFTER: Class-level setup (fast)
class TestMyView(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.admin_user = UserFactory()
        cls.team.members.add(cls.admin_user, through_defaults={"role": ROLE_ADMIN})

    def setUp(self):
        self.client = Client()  # Only stateful items
```
