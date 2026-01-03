# Insight QA Fixes - Context & Key Files

**Last Updated:** 2026-01-02

## Backlog Reference

Source: `dev/active/insight-qa-backlog/BACKLOG.md`

| Issue | Status | Priority | Description |
|-------|--------|----------|-------------|
| ISS-005 | Open | High | Onboarding sync page shows wrong team |
| ISS-006 | Open | High | AI Adoption sparkline uses different data source than card |
| ISS-001 | Open | Medium | Sparkline trend misleading during low-data periods |
| ISS-007 | Open | Medium | Review Time sparkline extreme percentages (same root cause as ISS-001) |

---

## Key Files

### ISS-005: Onboarding Team Context

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/onboarding/views.py` | Contains `sync_progress` and `start_sync` views | 474-520 |
| `apps/onboarding/tests/test_views.py` | Existing tests for onboarding views | 183-238 |

**Current buggy code (`views.py:479`):**
```python
team = request.user.teams.first()  # Ignores request.team
```

**Fix approach:**
```python
team = getattr(request, 'team', None) or getattr(request, 'default_team', None)
if not team:
    team = request.user.teams.first()
```

---

### ISS-006: AI Adoption Data Source

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/metrics/services/dashboard_service.py` | Dashboard metrics service | 79-92, 158-214, 2068-2170 |
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Sparkline tests | All |
| `apps/metrics/models/surveys.py` | PRSurvey model | N/A |

**Card calculation (`get_key_metrics`, line 200-201):**
```python
surveys = PRSurvey.objects.filter(pull_request__in=prs)
ai_assisted_pct = _calculate_ai_percentage(surveys)
```

**Sparkline calculation (`get_sparkline_data`, line 2103-2115):**
```python
ai_adoption_data = (
    prs.annotate(week=TruncWeek("merged_at"))
    .values("week")
    .annotate(
        total=Count("id"),
        ai_count=Count("id", filter=Q(is_ai_assisted=True)),  # Uses pattern detection!
    )
    .order_by("week")
)
```

**Fix approach:** Update sparkline to use survey data:
```python
ai_adoption_data = (
    prs.annotate(week=TruncWeek("merged_at"))
    .values("week")
    .annotate(
        total_with_survey=Count("survey", filter=Q(survey__author_ai_assisted__isnull=False)),
        ai_count=Count("survey", filter=Q(survey__author_ai_assisted=True)),
    )
    .order_by("week")
)
```

---

### ISS-001/ISS-007: Low-Data Week Handling

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `apps/metrics/services/dashboard_service.py` | `_calculate_change_and_trend` function | 2123-2145 |
| `apps/metrics/tests/dashboard/test_sparkline_data.py` | Sparkline tests | All |

**Current calculation (line 2123-2145):**
```python
def _calculate_change_and_trend(values: list) -> tuple[int, str]:
    if len(values) < 2:
        return 0, "flat"

    first_val = values[0]  # No sample size check
    last_val = values[-1]  # No sample size check

    if first_val == 0:
        if last_val > 0:
            return 100, "up"
        return 0, "flat"

    change_pct = int(round(((last_val - first_val) / first_val) * 100))
    # ...
```

**Fix approach:** Add sample size parameter:
```python
def _calculate_change_and_trend(
    values: list,
    sample_sizes: list | None = None,
    min_sample_size: int = 3
) -> tuple[int, str]:
    if len(values) < 2:
        return 0, "flat"

    # Find first/last week with sufficient data
    first_idx = 0
    last_idx = len(values) - 1

    if sample_sizes:
        # Find first valid week
        for i, size in enumerate(sample_sizes):
            if size >= min_sample_size:
                first_idx = i
                break
        else:
            return 0, "flat"

        # Find last valid week
        for i in range(len(sample_sizes) - 1, -1, -1):
            if sample_sizes[i] >= min_sample_size:
                last_idx = i
                break

    first_val = values[first_idx]
    last_val = values[last_idx]
    # ... rest unchanged
```

---

## Test Factories

| Factory | Location | Usage |
|---------|----------|-------|
| `TeamFactory` | `apps/metrics/factories.py` | Create test teams |
| `TeamMemberFactory` | `apps/metrics/factories.py` | Create team members |
| `PullRequestFactory` | `apps/metrics/factories.py` | Create PRs with various states |
| `PRSurveyFactory` | `apps/metrics/factories.py` | Create survey responses |
| `GitHubIntegrationFactory` | `apps/integrations/factories.py` | Create integrations |
| `TrackedRepositoryFactory` | `apps/integrations/factories.py` | Create tracked repos |

---

## Related Constants

| Constant | Value | Location | Purpose |
|----------|-------|----------|---------|
| `MIN_SPARKLINE_SAMPLE_SIZE` | 3 (proposed) | `dashboard_service.py` | Minimum PRs for valid trend |

---

## Team Context Middleware

The `request.team` attribute is set by middleware based on:
1. URL parameter `?team=<id>`
2. Session storage
3. `request.default_team` as fallback

**Key files:**
- `apps/teams/middleware.py` - Team context middleware
- `apps/teams/context.py` - Team context helpers

---

## Testing Commands

```bash
# Run specific test files
make test ARGS='apps.onboarding.tests.test_views'
make test ARGS='apps.metrics.tests.dashboard.test_sparkline_data'

# Run with pattern match
make test ARGS='-k sync_progress'
make test ARGS='-k sparkline'
make test ARGS='-k ai_adoption'

# Run single test
make test ARGS='apps.onboarding.tests.test_views::SyncProgressViewTests::test_shows_sync_progress_page'
```

---

## Decisions Made

1. **Survey data is source of truth for AI adoption** - Pattern detection (`is_ai_assisted`) is supplementary
2. **Minimum sample size of 3** - Below this, weeks are excluded from trend calculation
3. **Backward compatibility** - `request.user.teams.first()` is kept as fallback
4. **No breaking changes to API** - `_calculate_change_and_trend` remains backward compatible with optional params
