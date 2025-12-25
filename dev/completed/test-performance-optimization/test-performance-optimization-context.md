# Test Performance Optimization - Context

**Last Updated:** 2025-12-25 (Session 2)

## Current State

### Phases Completed
- **Phase 1** ✅ - Quick wins (mocking sleeps, marking slow tests)
- **Phase 2** ✅ - Factory optimization (fixtures, documentation, audit)

### Phase 3 Status: Analysis Complete
Analyzed dashboard tests - they're already fast (<1s per file). Key finding:
- Dashboard tests use date-range filtering for isolation
- Each test creates its own PRs in specific date ranges
- Converting to `setUpTestData` would break isolation (tests would see each other's data)
- **Decision**: Skip Phase 3 for dashboard tests - effort not worth the small gains

### Test Suite Performance
| Metric | Before | After Phase 1+2 |
|--------|--------|-----------------|
| Full suite | ~94s | ~50-54s |
| Tests | 3051 | 3074 |
| Improvement | - | **42% faster** |

## Files Modified This Session

### Phase 1 (Previous Session)
- `apps/integrations/tests/test_github_graphql.py` - Added `@patch("asyncio.sleep")` mocks
- `apps/metrics/tests/test_llm_tasks.py` - Added `@patch("apps.metrics.tasks.time.sleep")` mocks
- `apps/metrics/tests/test_seeding/test_data_generator.py` - Added `@pytest.mark.slow`
- `Makefile` - Added `test-quick` target

### Phase 2 (This Session)
- `conftest.py` - Added 4 new fixtures:
  - `team_with_members` - team + 5 members tuple
  - `team_context` - sets/unsets team context var
  - `authenticated_team_client` - client + team + user with membership
  - `sample_prs` - 10 PRs with reviews and commits
- `apps/metrics/factories.py` - Added comprehensive performance docs:
  - Module-level docstring with 5 best practices
  - Inline docs on PullRequestFactory and PRReviewFactory

## Key Discoveries

### Dashboard Tests Already Fast
Individual dashboard test file timings:
```
test_channel_metrics.py: 53 tests in 0.96s
test_review_metrics.py: 23 tests in 0.83s
test_pr_metrics.py: 45 tests in 0.80s
test_team_breakdown.py: 17 tests in 0.68s
(all others < 0.6s)
```
No optimization needed - tests are well-written.

### Factory Audit Results
All top 5 test files already use proper patterns:
- `test_ai_detector.py` - 0 factory usage (pure unit tests)
- `test_views.py` - 44 factories, all use team= ✅
- `test_llm_prompts.py` - 18 factories, all use team= ✅
- `test_chart_views.py` - uses Team/User only ✅
- `test_models.py` - 2 factories, all use team= ✅

### setUpTestData Limitation
Cannot blindly convert setUp→setUpTestData because:
1. Tests create PRs for specific date ranges
2. Service calls aggregate all PRs for team in date range
3. Shared team = tests would see each other's PRs = broken assertions

## Next Steps (For Continuation)

1. **Skip Phase 3 for dashboard/chart tests** - Already optimized
2. **Consider Phase 3 for other test files** if needed:
   - Look for tests that only READ shared fixtures
   - Avoid tests that count/aggregate data
3. **Phase 4 is optional** - CI checks, query count assertions

## Commands to Run on Restart

```bash
# Verify current state
make test  # Should pass with ~3074 tests in ~50-54s

# Check for pending migrations (none expected)
make migrations  # Should say "No changes detected"

# Run quick tests (excludes slow seeding tests)
make test-quick
```

## No Migrations Needed
No model changes were made - only test infrastructure improvements.

## Key Decisions Made

### 1. Mock asyncio.sleep at service level
**Decision:** Patch `apps.integrations.services.github_graphql.asyncio.sleep`
**Rationale:** This is where the actual sleep happens. Patching at test level would miss the real behavior.

### 2. Use class-level fixtures (setUpTestData) over module fixtures
**Decision:** Prefer `setUpTestData` over pytest module-scoped fixtures
**Rationale:** Django's transaction handling works better with TestCase.setUpTestData

### 3. Keep slow seeding tests, but mark them
**Decision:** Don't delete seeding tests, mark with `@pytest.mark.slow`
**Rationale:** These tests catch real integration issues but shouldn't block quick feedback

### 4. Factory pattern: explicit over implicit
**Decision:** Always pass `team=` and `author=` explicitly
**Rationale:** Reduces hidden database inserts, makes test data explicit

## Dependencies Between Tasks

```
Phase 1.1 (mock sleeps) ──────────────────────────┐
Phase 1.2 (mark slow) ────────────────────────────┤
Phase 1.3 (fix imports) ──────────────────────────┼──► Phase 2.1 (fixtures)
                                                  │
                                                  ├──► Phase 2.3 (audit) ──► Phase 3.x
                                                  │
                                                  └──► Phase 4.1 (query counts)
```

## Performance Baseline Data

### Slowest Tests (as of 2025-12-25)

```
4.24s call  test_llm_tasks.py::TestRunLLMAnalysisBatchTask::test_respects_limit_parameter
4.23s call  test_llm_tasks.py::TestRunLLMAnalysisBatchTask::test_handles_api_errors_gracefully
3.01s call  test_github_graphql.py::TestRetryOnTimeout::test_fetch_prs_bulk_fails_after_max_retries
3.01s call  test_github_graphql.py::TestTimeoutHandling::test_fetch_prs_bulk_raises_timeout_error
3.01s call  test_github_graphql.py::TestRetryOnTimeout::test_fetch_org_members_fails_after_max_retries
3.01s call  test_github_graphql.py::TestRetryOnTimeout::test_fetch_single_pr_retries_on_timeout
3.01s call  test_github_graphql.py::TestRetryOnTimeout::test_fetch_prs_bulk_retries_on_timeout
3.01s call  test_github_graphql.py::TestTimeoutHandling::test_fetch_single_pr_raises_timeout_error
3.01s call  test_github_graphql.py::TestTimeoutHandling::test_fetch_org_members_raises_timeout_error
3.01s call  test_github_graphql.py::TestRetryOnTimeout::test_fetch_single_pr_fails_after_max_retries
```

### Factory Cascade Analysis

```python
# Current cascade for PRReviewFactory():
PRReviewFactory()
├── team = SubFactory(TeamFactory)              # +1 Team
├── pull_request = SubFactory(PullRequestFactory)
│   ├── team = SubFactory(TeamFactory)          # +1 Team (duplicate!)
│   └── author = SubFactory(TeamMemberFactory)
│       └── team = SubFactory(TeamFactory)      # +1 Team (triplicate!)
└── reviewer = SubFactory(TeamMemberFactory)
    └── team = SubFactory(TeamFactory)          # +1 Team (quadruplicate!)

# Total: 4 Teams, 2 TeamMembers, 1 PullRequest, 1 PRReview
# Should be: 1 Team, 2 TeamMembers, 1 PullRequest, 1 PRReview
```

## Testing Commands

```bash
# Run with timing data
.venv/bin/pytest --durations=50 -n 0 --tb=no -q

# Run specific module serially
.venv/bin/pytest apps/integrations/tests/test_github_graphql.py -n 0 -v

# Run excluding slow tests (after adding markers)
.venv/bin/pytest -m "not slow" --reuse-db -n auto

# Verify no network calls
.venv/bin/pytest --disable-socket  # Requires pytest-socket

# Count database queries in a test
# Add assertNumQueries in test code
```

## Related Documentation

- `pyproject.toml` - pytest configuration (lines 102-121)
- `conftest.py` - existing fixtures
- `apps/metrics/factories.py` - factory definitions
- `CLAUDE.md` - TDD workflow and test conventions

## Notes for Implementation

### When Converting to setUpTestData

1. Only use for data that won't be modified by tests
2. Never mutate `cls.` attributes in test methods
3. For tests that modify data, create fresh objects in the test method
4. Remember: data is shared across all test methods in the class

### When Mocking asyncio.sleep

```python
from unittest.mock import AsyncMock, patch

# Correct: patch where it's used
@patch("apps.integrations.services.github_graphql.asyncio.sleep", new_callable=AsyncMock)

# Incorrect: patching the built-in
@patch("asyncio.sleep", new_callable=AsyncMock)  # Won't work if already imported
```

### When Auditing Factory Usage

Look for patterns like:
```python
# Bad: creates new team for each PR
for _ in range(5):
    PullRequestFactory()

# Good: reuse team
team = TeamFactory()
for _ in range(5):
    PullRequestFactory(team=team)

# Better: use create_batch
team = TeamFactory()
author = TeamMemberFactory(team=team)
PullRequestFactory.create_batch(5, team=team, author=author)
```
