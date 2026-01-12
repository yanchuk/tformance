# Test Optimization Phase 2 - Context

**Last Updated:** 2026-01-11

---

## Key Files

### Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/metrics/tests/test_pr_list_service.py` | PR list service tests | 11 classes → use TeamWithMembersMixin |
| `apps/integrations/tests/test_github_app_installation.py` | GitHub App installation tests | 10 classes → use setUpTestData |

### Files to Reference

| File | Purpose |
|------|---------|
| `apps/utils/tests/mixins.py` | Existing test mixins |
| `dev/guides/TESTING-GUIDE.md` | Testing best practices |
| `apps/metrics/factories.py` | TeamFactory, TeamMemberFactory |

### Files NOT to Modify

| File | Reason |
|------|--------|
| `apps/integrations/tests/test_github_graphql_sync.py` | Uses asyncio.run() - requires TransactionTestCase |
| `apps/onboarding/tests/test_views.py` | Intentional user isolation patterns |

---

## Key Decisions

### Decision 1: Use TeamWithMembersMixin for test_pr_list_service.py

**Rationale:**
- All 11 test classes use identical pattern: `team + member1 + member2`
- Mixin provides: `team`, `member1` (Alice), `member2` (Bob), `member3` (Charlie)
- Tests only READ fixture data, never modify

### Decision 2: Use Simple setUpTestData for test_github_app_installation.py

**Rationale:**
- Tests only need `self.team` - no complex fixtures
- Creating a new mixin would be over-engineering
- Must preserve `tearDown()` for `unset_current_team()` cleanup

### Decision 3: Keep tearDown Separate from setUpTestData

**Rationale:**
- `tearDown()` cleans up global state (`unset_current_team()`)
- This is per-test cleanup, not per-class setup
- Must run after EVERY test method

---

## Existing Mixin Reference

```python
# apps/utils/tests/mixins.py

class TeamWithMembersMixin:
    """Mixin providing team with TeamMember instances."""

    @classmethod
    def setUpTestData(cls):
        """Set up TeamMember fixtures."""
        cls.team = TeamFactory()
        cls.member1 = TeamMemberFactory(team=cls.team, display_name="Alice")
        cls.member2 = TeamMemberFactory(team=cls.team, display_name="Bob")
        cls.member3 = TeamMemberFactory(team=cls.team, display_name="Charlie")
```

---

## Baseline Measurements

| Metric | Value |
|--------|-------|
| Total tests in target files | 130 |
| Tests passing before changes | 130 |
| setUp methods to convert | 21 |
| Execution time (baseline) | 9.03s |

---

## Conversion Patterns

### Pattern A: Simple Mixin Conversion (test_pr_list_service.py)

```python
# Before
class TestGetPrsQueryset(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")

# After
from apps.utils.tests.mixins import TeamWithMembersMixin

class TestGetPrsQueryset(TeamWithMembersMixin, TestCase):
    # Inherits: team, member1, member2, member3
    pass
```

### Pattern B: setUpTestData with tearDown (test_github_app_installation.py)

```python
# Before
class TestGitHubAppInstallationModelCreation(TestCase):
    def setUp(self):
        self.team = TeamFactory()

    def tearDown(self):
        unset_current_team()

# After
class TestGitHubAppInstallationModelCreation(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def tearDown(self):
        unset_current_team()  # Keep this!
```

---

## Verification Commands

```bash
# Run target files only
.venv/bin/pytest apps/metrics/tests/test_pr_list_service.py apps/integrations/tests/test_github_app_installation.py -v --reuse-db

# Run single class after conversion
.venv/bin/pytest apps/metrics/tests/test_pr_list_service.py::TestGetPrsQueryset -v --reuse-db

# Check for regressions in full suite
.venv/bin/pytest --reuse-db -q
```
