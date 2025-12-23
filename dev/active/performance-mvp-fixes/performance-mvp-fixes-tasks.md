# Performance MVP Fixes - Tasks

**Last Updated: 2025-12-23**

## Overview

| Phase | Description | Effort | Status |
|-------|-------------|--------|--------|
| Phase 1 | Critical N+1 Fixes | 1.5 hrs | ✅ Complete |
| Phase 2 | Caching & Config | 30 min | ✅ Complete |
| Phase 3 | Database Indexes | 1 hr | ✅ Complete |
| Phase 4 | Weekly Aggregation | 1.5 hrs | ✅ Complete |
| Phase 5 | Dashboard Cache | 1 hr | ✅ Complete |

---

## Phase 1: Critical N+1 Fixes ✅

### 1.1 Fix Team Breakdown N+1 [M] ✅
- [x] Read current implementation in `dashboard_service.py:get_team_breakdown()`
- [x] Write failing test that asserts query count (N+1 will fail)
- [x] Rewrite function to use single annotated query with `values()` and `annotate()`
- [x] Verify test passes with constant query count
- [x] Run full dashboard service tests
- **Result**: Query count reduced from 31 → 2 (94% reduction)
- **File**: `apps/metrics/services/dashboard_service.py`

### 1.2 Fix Copilot Sync N+1 [S] ✅
- [x] Read current implementation in `tasks.py:sync_copilot_metrics_task()`
- [x] Write failing test with 10+ users per day
- [x] Extract usernames before loop, batch lookup with `filter(github_username__in=...)`
- [x] Use dictionary for O(1) lookup in loop
- [x] Verify test passes
- [x] Run Copilot sync tests
- **Result**: Query count reduced from 73 → 64 (eliminated 9 member lookups)
- **File**: `apps/integrations/tasks.py`

### 1.3 Fix PR Export select_related [S] ✅
- [x] Read current implementation in `pr_list_views.py:pr_list_export()`
- [x] Write failing test that asserts no N+1 on export
- [x] Verified `.select_related("author", "team")` already present - no fix needed
- [x] Verify test passes
- **Result**: Already optimized, added test to verify (8 queries constant)
- **File**: `apps/metrics/views/pr_list_views.py`

---

## Phase 2: Caching & Config ✅

### 2.1 Enable Redis Cache in Development [S] ✅
- [x] Read current cache config in `settings.py`
- [x] Add `USE_REDIS_CACHE` env var (default: False)
- [x] Update CACHES dict to use env var instead of DEBUG check
- **Result**: Added `USE_REDIS_CACHE` env var to enable Redis in dev mode
- **File**: `tformance/settings.py`

---

## Phase 3: Database Indexes ✅

### 3.1 Add PullRequest Composite Indexes [M] ✅
- [x] Create new migration file
- [x] Add index: `(team, state, merged_at)` - dashboard queries
- [x] Add index: `(team, author, merged_at)` - team breakdown
- [x] Add index: `(team, pr_created_at)` - date range queries
- [x] Run migration locally
- **Result**: Migration `0016_add_performance_indexes.py` created and applied
- **File**: `apps/metrics/migrations/0016_add_performance_indexes.py`

### 3.2 Add TeamMember Composite Index [S] ✅
- [x] Add to same migration
- [x] Add index: `(team, github_username)` - Copilot lookup
- [x] Add index: `(team, is_active)` - weekly aggregation
- [x] Run migration locally
- **Result**: Added to same migration `0016_add_performance_indexes.py`
- **File**: `apps/metrics/migrations/0016_add_performance_indexes.py`

---

## Phase 4: Weekly Aggregation Optimization ✅

### 4.1 Batch Weekly Metrics Computation [L] ✅
- [x] Read current implementation in `aggregation_service.py:aggregate_team_weekly_metrics()`
- [x] Identify all queries inside `compute_member_weekly_metrics()` loop
- [x] Write failing test that asserts constant query count
- [x] Refactor to:
  - [x] Fetch all PR metrics for team/week in single query
  - [x] Fetch all commit counts for team/week in single query
  - [x] Fetch all survey metrics for team/week in single query
  - [x] Fetch all review metrics for team/week in single query
  - [x] Compute metrics in-memory per member with dict lookups
- [x] Verify test passes
- [x] Run aggregation service tests
- **Result**: Query count reduced from 111 → 65 (42% reduction)
- **File**: `apps/metrics/services/aggregation_service.py`

---

## Phase 5: Dashboard Service Optimization ✅

### 5.1 Cache Key Metrics Results [M] ✅
- [x] Identify `get_key_metrics()` function
- [x] Add cache key generation: `f"key_metrics:{team.id}:{start_date}:{end_date}"`
- [x] Add cache.get/set with manual cache logic
- [x] Set TTL to 5 minutes (300 seconds)
- [x] Write 4 tests for cache hit/miss behavior
- **Result**: Second dashboard load hits cache (0 DB queries)
- **File**: `apps/metrics/services/dashboard_service.py`

---

## Verification Checklist

- [x] All unit tests pass: `make test`
- [x] No N+1 queries in modified functions (use `assertNumQueries`)
- [x] Dashboard cache tests pass (4 new tests)
- [ ] Dashboard loads in < 500ms for 50-member team
- [ ] CSV export works for 1000+ PRs without timeout
- [ ] Copilot sync handles 100+ users/day efficiently
- [ ] Migrations can be reversed cleanly

---

## Summary of Performance Improvements

| Fix | Before | After | Improvement |
|-----|--------|-------|-------------|
| Team Breakdown | 31 queries | 2 queries | 94% reduction |
| Copilot Sync | 73 queries | 64 queries | 12% reduction |
| PR Export | Already optimized | Verified | Test added |
| Weekly Aggregation | 111 queries | 65 queries | 42% reduction |
| Dashboard Cache | No caching | 5 min TTL | 0 queries on cache hit |

**Total tests added**: 8 query count tests + 4 cache behavior tests = 12 new tests

---

## Files Modified

### Services
- `apps/metrics/services/dashboard_service.py` - N+1 fix + caching
- `apps/metrics/services/aggregation_service.py` - N+1 fix with batch queries
- `apps/integrations/tasks.py` - N+1 fix with batch member lookup

### Configuration
- `tformance/settings.py` - USE_REDIS_CACHE env var

### Migrations
- `apps/metrics/migrations/0016_add_performance_indexes.py` - 5 composite indexes

### Models
- `apps/metrics/models/github.py` - PullRequest indexes in Meta
- `apps/metrics/models/team.py` - TeamMember indexes in Meta

### Tests
- `apps/metrics/tests/dashboard/test_team_breakdown.py` - Query count test
- `apps/metrics/tests/dashboard/test_key_metrics.py` - 4 cache tests
- `apps/integrations/tests/test_copilot_sync.py` - Query count test class
- `apps/metrics/tests/test_pr_list_views.py` - Query count test
- `apps/metrics/tests/test_aggregation_service.py` - Query count test

---

## Notes

- Run `make test-slow` after changes to identify any new slow tests
- Use Django Debug Toolbar to verify query counts during manual testing
- To enable Redis caching in dev: `USE_REDIS_CACHE=true` in `.env`
- Consider adding `django-silk` for production profiling (future work)
