# Performance MVP Fixes - Context

**Last Updated: 2025-12-23**

## Key Files

### Primary Files to Modify

| File | Purpose | Priority |
|------|---------|----------|
| `apps/metrics/services/dashboard_service.py` | Dashboard data aggregation | 🔴 Critical |
| `apps/integrations/tasks.py` | Celery sync tasks | 🔴 Critical |
| `apps/metrics/views/pr_list_views.py` | PR list export | 🔴 Critical |
| `apps/metrics/services/aggregation_service.py` | Weekly metrics | 🟡 High |
| `tformance/settings.py` | Cache configuration | 🟡 High |

### Model Files (for migrations)

| File | Contains |
|------|----------|
| `apps/metrics/models/github.py` | PullRequest, PRReview, Commit models |
| `apps/metrics/models/team.py` | TeamMember model |

### Test Files

| Test File | Tests For |
|-----------|-----------|
| `apps/metrics/tests/test_dashboard_service.py` | Dashboard service functions |
| `apps/integrations/tests/test_copilot_sync.py` | Copilot sync task |
| `apps/metrics/tests/test_pr_list_views.py` | PR list views |
| `apps/metrics/tests/test_aggregation_service.py` | Weekly aggregation |

---

## Technical Decisions

### Decision 1: Query Optimization Approach

**Chosen**: Use Django ORM `annotate()` with `values()` for aggregations
**Rationale**:
- More readable than raw SQL
- Maintains ORM safety guarantees
- Easier to test and maintain

**Alternative Rejected**: Raw SQL queries
- Reason: Harder to maintain, bypass ORM protections

### Decision 2: Caching Strategy

**Chosen**: Redis cache with short TTL (5 minutes)
**Rationale**:
- Redis already configured in project
- Short TTL avoids stale data issues
- Simple to implement and debug

**Alternative Rejected**: Database-level caching
- Reason: More complex, overkill for MVP

### Decision 3: Index Strategy

**Chosen**: Composite indexes on frequently-joined columns
**Rationale**:
- Covers common query patterns
- PostgreSQL can use partial indexes efficiently
- Low maintenance overhead

**Indexes to Add**:
```python
# PullRequest
models.Index(fields=["team", "state", "merged_at"], name="pr_team_state_merged_idx")
models.Index(fields=["team", "author", "merged_at"], name="pr_team_author_merged_idx")
models.Index(fields=["team", "pr_created_at"], name="pr_team_created_idx")

# TeamMember
models.Index(fields=["team", "github_username"], name="member_team_gh_username_idx")
models.Index(fields=["team", "is_active"], name="member_team_active_idx")
```

---

## Code Patterns

### N+1 Fix Pattern

**Before (N+1)**:
```python
for member in members:
    member_prs = prs.filter(author=member)  # Query in loop
    count = member_prs.count()
```

**After (Single Query)**:
```python
result = (
    prs
    .values("author__id", "author__display_name")
    .annotate(count=Count("id"))
)
```

### Batch Lookup Pattern

**Before (N+1)**:
```python
for username in usernames:
    member = TeamMember.objects.get(github_username=username)
```

**After (Batch)**:
```python
members_by_username = {
    m.github_username: m
    for m in TeamMember.objects.filter(github_username__in=usernames)
}
for username in usernames:
    member = members_by_username.get(username)
```

### Select Related Pattern

**Before (N+1)**:
```python
for pr in prs.iterator():
    author_name = pr.author.display_name  # Lazy load triggers query
```

**After (Prefetched)**:
```python
for pr in prs.select_related("author").iterator():
    author_name = pr.author.display_name  # Already loaded
```

---

## Dependencies

### Internal Dependencies

- `apps.teams.models.Team` - Team model for filtering
- `apps.metrics.models.*` - All metrics models
- `apps.integrations.models.GitHubIntegration` - For Copilot sync

### External Dependencies

- `django.core.cache` - Cache framework
- `redis` - Cache backend (already installed)
- `celery` - Task queue (already configured)

### Database

- PostgreSQL 17.7
- Current index count: ~20 across metrics models
- New indexes: 5 composite indexes

---

## Testing Strategy

### Unit Tests

Each optimization should have tests verifying:
1. **Correctness**: Results match before/after
2. **Query count**: Using `assertNumQueries()` or `django-test-plus`
3. **Edge cases**: Empty results, single item, null authors

### Performance Benchmarks

```python
# Example benchmark test
def test_team_breakdown_query_count(self):
    """Team breakdown should use constant queries regardless of team size."""
    # Create 50 team members
    members = TeamMemberFactory.create_batch(50, team=self.team)

    with self.assertNumQueries(3):  # Base query + surveys + AI calc
        result = get_team_breakdown(self.team, start_date, end_date)

    self.assertEqual(len(result), 50)
```

### Integration Tests

- Dashboard load with realistic data
- Copilot sync with 100+ users
- CSV export with 1000+ PRs

---

## Rollback Plan

All changes are backward-compatible and can be reverted:

1. **Code changes**: Standard git revert
2. **Migrations**: Can be reversed (indexes drop cleanly)
3. **Cache config**: Env var makes it toggleable

---

## Related Documentation

- `prd/ARCHITECTURE.md` - System architecture
- `prd/DATA-MODEL.md` - Database schema
- `CLAUDE.md` - Coding guidelines (ORM best practices)
