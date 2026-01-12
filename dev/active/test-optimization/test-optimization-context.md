# Test Optimization Context - Phase 2 Expansion

**Last Updated:** 2026-01-11
**Previous Phase:** 2025-12-31 (seeding tests - 70% improvement)
**This Phase:** Expand setUpTestData to remaining ~600 test classes

---

## Key Files

### Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/feedback/factories.py` | AIFeedbackFactory | Fix LazyAttribute anti-pattern |
| `apps/utils/tests/base.py` | New file | Create TeamTestMixin |
| `apps/metrics/tests/test_chart_views.py` | 10 test classes | setUp → setUpTestData |
| `apps/metrics/tests/test_pr_list_service.py` | 10 test classes | setUp → setUpTestData |
| `apps/metrics/tests/test_trends_views.py` | 11 test classes | setUp → setUpTestData |
| `apps/integrations/tests/test_views.py` | 15 test classes | setUp → setUpTestData |
| `apps/integrations/tests/test_sync_logging.py` | 15 test classes | setUp → setUpTestData |
| + ~600 more test files | Various apps | setUp → setUpTestData where applicable |

### Files to NOT Modify

| File | Reason |
|------|--------|
| `apps/integrations/tests/test_github_graphql_sync.py` | Uses asyncio.run() - requires TransactionTestCase |
| `apps/integrations/tests/test_github_graphql_sync_utils.py` | Uses asyncio.run() |
| `apps/metrics/tests/test_seeding/test_data_generator.py` | Already optimized in Phase 1 |

### Files to Reference

| File | Purpose |
|------|---------|
| `conftest.py` | Existing pytest fixtures (team_with_members, etc.) |
| `pyproject.toml` | Pytest configuration |
| `apps/metrics/factories.py` | Factory patterns documentation |
| `dev/guides/TESTING-GUIDE.md` | Testing best practices |

---

## Key Decisions

### Decision 1: Focus on setUp → setUpTestData Conversion

**Question:** What's the most impactful change for test speed?

**Analysis:**
- 645 setUp() methods vs 9 setUpTestData() methods
- Each setUp() runs per test method, setUpTestData() runs once per class
- Previous work proved 92% improvement on seeding tests with this pattern
- TeamFactory() called 763 times - many redundant

**Decision:** Systematically convert setUp to setUpTestData across all apps

---

### Decision 2: Fix AIFeedbackFactory Anti-Pattern

**Question:** Why is LazyAttribute with factory call problematic?

**Current Code:**
```python
reported_by = factory.LazyAttribute(lambda obj: TeamMemberFactory(team=obj.team))
```

**Problem:**
- `TeamMemberFactory()` without `.build()` creates a DB object
- Runs on EVERY AIFeedback creation
- N+1 writes when using create_batch()

**Solution:**
```python
reported_by = factory.SubFactory(TeamMemberFactory, team=factory.SelfAttribute("..team"))
```

**Decision:** Fix with SubFactory pattern (consistent with other factories)

---

### Decision 3: Create TeamTestMixin

**Question:** Should we create a shared mixin or convert each file individually?

**Options:**
1. Individual conversion - More work, but no new dependencies
2. TeamTestMixin - Less repetition, establishes pattern
3. Use conftest fixtures - Already exist but underutilized

**Decision:** Create TeamTestMixin AND update individual files
- Mixin provides template for common pattern
- Individual files may have unique requirements
- conftest fixtures good for pytest-style tests

---

### Decision 4: What to Keep as setUp()

Tests that MUST keep setUp():
- Tests that modify fixture data (update, delete, save)
- Tests that use `refresh_from_db()`
- Tests needing fresh Client() per test (stateful)
- Tests with per-test mock requirements
- Async tests using `asyncio.run()`

Tests that CAN use setUpTestData:
- Read-only assertions
- Response code checks
- Template rendering tests
- Context data validation
- Query count assertions

---

## Analysis Statistics

### setUp Count by App

| App | setUp Methods | Priority |
|-----|---------------|----------|
| metrics | 200+ | P1 |
| integrations | 150+ | P1 |
| onboarding | 40+ | P2 |
| web | 30+ | P2 |
| auth | 20+ | P3 |
| feedback | 10+ | P3 |
| teams | 15+ | P3 |
| others | 30+ | P3 |

### High-Impact Files

| File | setUp Count | Est. Test Methods |
|------|-------------|-------------------|
| `test_github_graphql_sync.py` | 23 | ~150 (SKIP - async) |
| `test_sync_logging.py` | 15 | ~50 |
| `test_views.py` (integrations) | 15 | ~80 |
| `test_chart_views.py` | 10 | ~100 |
| `test_pr_list_service.py` | 10 | ~60 |
| `test_trends_views.py` | 11 | ~50 |

---

## Performance Baselines

### Phase 1 Results (2025-12-31)

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Full test suite | 180s | 53s | 70% faster |
| Seeding tests | 188s | 15s | 92% faster |
| Tests passing | 3955 | 4404 | All pass |

### Phase 2 Target

| Metric | Current | Target | Expected Improvement |
|--------|---------|--------|----------------------|
| Full suite | 53s | <40s | 25% faster |
| setUp calls | 645 | <100 | 85% reduction |

---

## Code Patterns

### TeamTestMixin (New)

```python
# apps/utils/tests/base.py
from django.test import TestCase, Client
from apps.metrics.factories import TeamFactory
from apps.integrations.factories import UserFactory
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER

class TeamTestMixin:
    """Mixin providing team, admin, and member fixtures via setUpTestData."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.admin_user = UserFactory()
        cls.member_user = UserFactory()
        cls.team.members.add(cls.admin_user, through_defaults={"role": ROLE_ADMIN})
        cls.team.members.add(cls.member_user, through_defaults={"role": ROLE_MEMBER})

    def setUp(self):
        self.client = Client()
```

### Usage

```python
from apps.utils.tests.base import TeamTestMixin
from django.test import TestCase

class TestMyView(TeamTestMixin, TestCase):
    # team, admin_user, member_user, client available automatically

    def test_view_requires_auth(self):
        response = self.client.get("/my-url/")
        self.assertEqual(response.status_code, 302)
```

---

## Related Documentation

- [CLAUDE.md](../../../CLAUDE.md) - TDD requirements
- [TESTING-GUIDE.md](../../../dev/guides/TESTING-GUIDE.md) - Testing patterns
- [conftest.py](../../../conftest.py) - Existing fixtures
- [Previous plan](./test-optimization-plan.md) - Phase 1 details
