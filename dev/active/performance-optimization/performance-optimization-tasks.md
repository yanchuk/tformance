# Performance Optimization Tasks

**Last Updated:** 2025-12-31
**Branch:** `perf-optimization`
**Worktree:** `../tformance-perf-optimization`

---

## Phase 0: CRITICAL - Sync Scalability (P0)

### 0.1 Fix sync_repository_history to honor days_back parameter
**Effort:** M | **TDD:** Required | **Status:** ✅ COMPLETE

**Solution Implemented:**
- Modified `get_repository_pull_requests()` to accept `days_back` parameter
- Function now returns a generator (not list) for memory efficiency
- PRs sorted by `updated_at desc`, iteration stops when hitting old PRs
- `sync_repository_history()` now passes `days_back` to the fetcher

**Acceptance Criteria:**
- [x] Test exists verifying days_back filtering works
- [x] Test fails before implementation (RED)
- [x] Implementation filters PRs by updated_at within days_back
- [x] Test passes after implementation (GREEN)
- [x] Large repos don't load all PRs into memory (generator pattern)

**Test Location:** `apps/integrations/tests/test_github_sync_days_back.py`

**Files Modified:**
- `apps/integrations/services/github_sync.py` (lines 68-119, 670-686)
- `apps/integrations/tests/github_sync/test_pr_fetch.py` (updated for generator)

---

### 0.2 Add chunked/paginated PR fetching
**Effort:** M | **TDD:** Required | **Status:** ✅ COMPLETE

**Solution Implemented:**
- Same generator pattern from 0.1 provides memory-efficient iteration
- PyGithub's PaginatedList handles API pagination automatically
- Generator yields one PR at a time - constant memory usage

**Acceptance Criteria:**
- [x] Test exists verifying memory-efficient pattern
- [x] Implementation uses generator/iterator pattern (not list)
- [x] Memory usage stable regardless of repo size
- [x] Test passes after implementation (GREEN)

**Test Location:** `apps/integrations/tests/test_github_sync_days_back.py`

---

### 0.3 Add GIN indexes for JSONFields
**Effort:** S | **TDD:** Not Required | **Status:** ✅ COMPLETE

**What's Done:**
- [x] GIN indexes already exist from migration 0020 (created via raw SQL)
- [x] Added `GinIndex` import to `apps/metrics/models/github.py`
- [x] Added indexes to PullRequest model Meta class (matching existing DB indexes)

**Note:** Indexes were already created in migration 0020. Added to model Meta for Django tracking.

**Files Modified:**
- `apps/metrics/models/github.py` - Added GinIndex definitions

---

## Phase A: Query Optimization

### A.4 Add CELERY_RESULT_EXPIRES setting
**Effort:** S | **TDD:** Not Required | **Status:** ✅ COMPLETE

**What's Done:**
- [x] `CELERY_RESULT_EXPIRES = 86400` added to settings (24 hours)
- [x] Auto-cleanup of stale results from Redis

**Files Modified:**
- `tformance/settings.py`

---

## Phase D: Scaling Preparation

### D.2 Celery Worker Split (Documentation Only)
**Effort:** S | **TDD:** Not Required | **Status:** ✅ ALREADY EXISTS

**Note:** Task routing is already configured in `tformance/settings.py` (CELERY_TASK_ROUTES).

**Production Recommendation:**
```yaml
# Worker for IO-bound sync tasks (gevent pool)
- name: tformance-worker-sync
  dockerCommand: celery -A tformance worker -Q sync -l INFO --pool=gevent --concurrency=50

# Worker for CPU-bound compute tasks (prefork pool)
- name: tformance-worker-compute
  dockerCommand: celery -A tformance worker -Q compute -l INFO --pool=prefork --concurrency=4

# Worker for rate-limited LLM tasks (low concurrency)
- name: tformance-worker-llm
  dockerCommand: celery -A tformance worker -Q llm -l INFO --pool=threads --concurrency=2
```

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| 0: Sync Scalability | 3 | 3 | 100% |
| A: Query Optimization | 1 | 1 | 100% |
| D: Scaling Preparation | 1 | 1 | 100% |
| **Total** | **5** | **5** | **100%** |

---

## Quick Reference

### Run Tests
```bash
cd /Users/yanchuk/Documents/GitHub/tformance-perf-optimization
/Users/yanchuk/Documents/GitHub/tformance/.venv/bin/pytest apps/integrations/ -v
```

### Check Uncommitted Changes
```bash
cd /Users/yanchuk/Documents/GitHub/tformance-perf-optimization
git status
git diff --stat
```
