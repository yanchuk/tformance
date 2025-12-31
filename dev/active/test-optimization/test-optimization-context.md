# Test Optimization Context

**Last Updated:** 2025-12-31

---

## Key Files

### Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/integrations/tests/test_github_graphql_sync.py` | GraphQL sync tests | TransactionTestCase → TestCase |
| `apps/metrics/tests/test_seeding/test_data_generator.py` | Seeding tests | setUp → setUpTestData |

### Files to Reference

| File | Purpose |
|------|---------|
| `conftest.py` | Pytest configuration, shared fixtures |
| `pyproject.toml` | Pytest options (addopts, markers) |
| `apps/metrics/seeding/data_generator.py` | ScenarioDataGenerator class |
| `apps/metrics/seeding/scenarios/` | Scenario definitions (ai-success, etc.) |

---

## Key Decisions

### Decision 1: TransactionTestCase → TestCase

**Question:** Why are GraphQL tests using TransactionTestCase?

**Analysis:**
- TransactionTestCase is needed when testing actual database transactions
- These tests mock `GitHubGraphQLClient` - no real API calls
- No tests assert on rollback/commit behavior
- All database operations are standard ORM creates

**Decision:** Safe to convert to TestCase

**Evidence:**
```bash
# No transaction-specific assertions found:
grep -E "atomic|transaction|rollback|commit" apps/integrations/tests/test_github_graphql_sync.py
# Only found: "commits" (referring to git commits, not DB transactions)
```

---

### Decision 2: setUpTestData() for Seeding Tests

**Question:** Will shared test data cause test isolation issues?

**Analysis:**
- `setUpTestData()` creates data once, wrapped in transaction savepoint
- Each test method runs in its own transaction that rolls back
- Tests must be **read-only** on the shared data
- Tests that modify data need their own setup

**Decision:** Safe for most tests; 2 tests need separate classes

**Tests requiring separate handling:**
1. `test_same_seed_produces_same_counts` - runs generator twice
2. `test_different_seed_produces_different_results` - runs generator twice

**Solution:** Move these to a new class `TestScenarioDataGeneratorReproducibility`

---

### Decision 3: Skip Slow Tests by Default

**Question:** Should slow tests be excluded from default CI runs?

**Options:**
1. **Keep in default runs** - Ensures full coverage but slower feedback
2. **Exclude with marker** - Faster feedback, separate slow test job
3. **Optimize first, then decide** - Get data before changing workflow

**Decision:** Optimize first (Phases 1-2), then evaluate if separation needed

---

## Dependencies

### Internal Dependencies

```
test_data_generator.py
├── apps.metrics.seeding.data_generator.ScenarioDataGenerator
├── apps.metrics.seeding.scenarios.get_scenario
├── apps.metrics.models (PullRequest, PRReview, Commit, etc.)
└── apps.teams.models.Team

test_github_graphql_sync.py
├── apps.integrations.services.github_graphql_sync
├── apps.integrations.factories (GitHubIntegrationFactory, etc.)
├── apps.metrics.factories (TeamFactory, TeamMemberFactory)
└── apps.metrics.models (PullRequest, PRReview, Commit, etc.)
```

### External Dependencies

None - all tests use mocks for external services.

---

## Test Data Characteristics

### Seeding Test Data (ai-success scenario)

| Model | Count | Notes |
|-------|-------|-------|
| Team | 1 | Test team |
| TeamMember | 5 | 2 early_adopter, 2 follower, 1 skeptic |
| PullRequest | ~160 | 8 weeks × 5 members × 4 PRs |
| PRReview | ~150 | 1+ per non-open PR |
| Commit | ~400 | 2-5 per PR |
| WeeklyMetrics | 8 | 1 per week |

### GraphQL Test Data

Each test creates minimal fixtures:
- 1 Team (via TeamFactory)
- 1 TrackedRepository
- 1-2 TeamMembers
- Mock GraphQL responses

---

## Code Patterns

### TestCase with setUpTestData

```python
from django.test import TestCase

class TestMyFeature(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Create shared fixtures - runs ONCE per class."""
        cls.team = TeamFactory()
        cls.members = TeamMemberFactory.create_batch(5, team=cls.team)

    def test_read_only_query(self):
        """Safe - doesn't modify shared data."""
        count = TeamMember.objects.filter(team=self.team).count()
        self.assertEqual(count, 5)

    def test_another_read_only(self):
        """Also safe - same shared data available."""
        self.assertEqual(len(self.members), 5)
```

### Async Test Pattern (GraphQL)

```python
import asyncio
from django.test import TestCase  # NOT TransactionTestCase
from unittest.mock import AsyncMock, MagicMock, patch

class TestAsyncSync(TestCase):
    def setUp(self):
        self.team = TeamFactory()

    @patch("apps.integrations.services.github_graphql_sync.GitHubGraphQLClient")
    def test_async_operation(self, mock_client_class):
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_client.fetch_prs_bulk = AsyncMock(return_value={...})

        # Run async code
        result = asyncio.run(sync_repository_history_graphql(...))

        self.assertEqual(result["prs_synced"], 1)
```

---

## Performance Baselines

### Before Optimization (2025-12-31)

```
28.73s test_generator_uses_github_data_when_enabled
27.37s test_generator_creates_commits
23.65s test_generator_creates_prs
23.30s test_generator_creates_team_members
21.72s test_generator_creates_weekly_metrics
20.93s test_generator_creates_reviews
20.79s test_bottleneck_reviewer_gets_more_reviews
12.62s test_same_seed_produces_same_counts
9.61s  test_different_seed_produces_different_results
6.81s  test_generator_falls_back_to_factory_when_no_github

GraphQL tests: 4-6s each (22 tests)
Total suite: ~180s
```

### ACTUAL Results After Optimization (2025-12-31)

```
Seeding tests: ~15s total (was 188s) - 92% faster!
GraphQL tests: ~11s total (unchanged - async requires TransactionTestCase)
Total suite: 53.18s (was 180s) - 70% faster!
```

**Key insight:** GraphQL tests cannot be converted to TestCase because `asyncio.run()`
executes in a separate thread that cannot see uncommitted transaction data.

---

## Related Documentation

- [CLAUDE.md](../../../CLAUDE.md) - TDD requirements, test conventions
- [conftest.py](../../../conftest.py) - Shared pytest fixtures
- [pyproject.toml](../../../pyproject.toml) - Pytest configuration
