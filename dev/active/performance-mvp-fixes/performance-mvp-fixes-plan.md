# Performance Optimization - MVP Quick Fixes

**Last Updated: 2025-12-23**

## Executive Summary

This plan addresses critical performance issues identified during a comprehensive codebase audit before MVP launch. The focus is on N+1 query patterns, missing indexes, and caching configuration that could impact user experience at scale.

**Scope**: 4 critical fixes + 4 high-priority improvements
**Total Estimated Effort**: ~4-6 hours
**Risk Level**: Low (isolated changes, no breaking API changes)

---

## Current State Analysis

### Identified Performance Issues

| Severity | Issue | Location | Impact |
|----------|-------|----------|--------|
| 🔴 Critical | Team Breakdown N+1 | `dashboard_service.py:314-324` | 4+ queries per member in loop |
| 🔴 Critical | Copilot Sync N+1 | `integrations/tasks.py:971` | 1 query per user (500+ potential) |
| 🔴 Critical | PR Export Missing select_related | `pr_list_views.py:164` | N+1 on author access |
| 🔴 Critical | Cache Disabled in DEBUG | `settings.py:526` | No caching during dev |
| 🟡 High | Duplicate Metrics Queries | `chart_views.py` | 2x queries for period comparison |
| 🟡 High | Missing Composite Indexes | Models | Slow dashboard queries |
| 🟡 High | Weekly Aggregation Loop | `aggregation_service.py:172` | 5-6 queries × members |
| 🟡 High | No API Response Caching | Sync tasks | Re-fetches all data |

### Current Query Patterns

**Problem 1: Team Breakdown Loop (dashboard_service.py:314-324)**
```python
for member in members:
    member_prs = prs.filter(author=member)  # N+1 query
    prs_merged = member_prs.count()          # N+1 query
    avg_cycle_time = member_prs.aggregate()  # N+1 query
    member_surveys = PRSurvey.objects.filter(...)  # N+1 query
```

**Problem 2: Copilot Sync Loop (tasks.py:971)**
```python
for user_data in day_data["per_user_data"]:
    member = TeamMember.objects.get(team=team, github_username=github_username)  # N+1
```

**Problem 3: PR Export (pr_list_views.py:164)**
```python
for pr in prs.iterator():
    pr.author.display_name  # N+1 - author not prefetched
```

---

## Proposed Future State

### Optimized Query Patterns

**Fix 1: Team Breakdown - Single Annotated Query**
```python
# Replace loop with single aggregated query
result = (
    prs
    .values("author__id", "author__display_name", "author__github_id")
    .annotate(
        prs_merged=Count("id"),
        avg_cycle_time=Avg("cycle_time_hours"),
    )
)
```

**Fix 2: Copilot Sync - Batch Lookup**
```python
# Pre-fetch all team members before loop
usernames = [u.get("github_username") for u in day_data["per_user_data"] if u.get("github_username")]
members_by_username = {
    m.github_username: m
    for m in TeamMember.objects.filter(team=team, github_username__in=usernames)
}
```

**Fix 3: PR Export - Add select_related**
```python
prs = get_prs_queryset(team, filters).select_related("author").order_by(...)
```

---

## Implementation Phases

### Phase 1: Critical N+1 Fixes (1.5 hours)

**1.1 Fix Team Breakdown N+1** [Effort: M]
- File: `apps/metrics/services/dashboard_service.py`
- Function: `get_team_breakdown()`
- Change: Replace member loop with single annotated query
- Test: Verify query count drops from N+1 to 2

**1.2 Fix Copilot Sync N+1** [Effort: S]
- File: `apps/integrations/tasks.py`
- Function: `sync_copilot_metrics_task()`
- Change: Pre-fetch TeamMembers using `__in` filter before loop
- Test: Verify query count drops from N to 2

**1.3 Fix PR Export select_related** [Effort: S]
- File: `apps/metrics/views/pr_list_views.py`
- Function: `pr_list_export()`
- Change: Chain `.select_related("author")` on queryset
- Test: Verify no N+1 on CSV export with 100+ PRs

### Phase 2: Caching & Config (30 minutes)

**2.1 Enable Redis Cache in Development** [Effort: S]
- File: `tformance/settings.py`
- Change: Make cache configurable via env var, default to Redis
- Test: Verify cache operations work in dev mode

### Phase 3: Database Indexes (1 hour)

**3.1 Add Composite Indexes to PullRequest** [Effort: M]
- File: New migration
- Indexes to add:
  - `(team, state, merged_at)` - for dashboard queries
  - `(team, author, merged_at)` - for team breakdown
  - `(team, pr_created_at)` - for date range queries
- Test: Run EXPLAIN ANALYZE on common queries

**3.2 Add Composite Index to TeamMember** [Effort: S]
- File: New migration
- Indexes to add:
  - `(team, github_username)` - for Copilot sync lookup
  - `(team, is_active)` - for weekly aggregation
- Test: Verify index usage in queries

### Phase 4: Weekly Aggregation Optimization (1.5 hours)

**4.1 Batch Weekly Metrics Computation** [Effort: L]
- File: `apps/metrics/services/aggregation_service.py`
- Function: `aggregate_team_weekly_metrics()`
- Change: Fetch all data in bulk queries, then compute in-memory
- Test: Verify query count is constant regardless of team size

### Phase 5: Dashboard Service Optimization (1 hour)

**5.1 Cache Key Metrics Results** [Effort: M]
- File: `apps/metrics/services/dashboard_service.py`
- Function: `get_key_metrics()`
- Change: Add 5-minute cache with team+date range key
- Test: Verify cache hit on subsequent dashboard loads

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Query results differ after optimization | Low | High | Compare before/after results in tests |
| Cache invalidation issues | Medium | Medium | Use short TTL (5 min) for MVP |
| Index creation locks table | Low | Low | Create indexes CONCURRENTLY |
| Breaking existing tests | Medium | Medium | Run full test suite after each change |

---

## Success Metrics

1. **Query Count Reduction**
   - Team breakdown: N+1 → 2 queries (where N = team size)
   - Copilot sync: N → 2 queries (where N = users per day)
   - PR export: N+1 → 1 query

2. **Dashboard Load Time**
   - Target: < 500ms for teams with 50+ members
   - Measure: Add timing logs before/after

3. **Database Load**
   - Reduced CPU usage on PostgreSQL
   - Fewer connections during sync tasks

---

## Required Resources & Dependencies

### Technical Requirements
- PostgreSQL 17+ (current)
- Redis (configured, needs enabling)
- Django Debug Toolbar or django-silk (optional, for validation)

### Testing Requirements
- Unit tests for each optimized function
- Performance benchmarks with realistic data (50+ members, 1000+ PRs)
- Full test suite must pass

### Documentation
- Update CLAUDE.md with performance patterns (optional)
- Add comments explaining optimization choices

---

## Appendix: Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/services/dashboard_service.py` | Fix N+1 in `get_team_breakdown()` |
| `apps/integrations/tasks.py` | Fix N+1 in `sync_copilot_metrics_task()` |
| `apps/metrics/views/pr_list_views.py` | Add `select_related("author")` |
| `apps/metrics/services/aggregation_service.py` | Batch weekly metrics |
| `tformance/settings.py` | Make cache configurable |
| `apps/metrics/models/github.py` | Add composite indexes (migration) |
| `apps/metrics/models/team.py` | Add composite index (migration) |
