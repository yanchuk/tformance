# Database Security & Performance Audit - Context

**Last Updated:** 2026-01-05 (Session 3)

---

## Current State Summary

**Working in worktree:** `/Users/yanchuk/Documents/GitHub/tformance-db-audit`
**Branch:** `feature/db-perf-security-audit`
**Main venv:** `/Users/yanchuk/Documents/GitHub/tformance/.venv/bin/pytest`

### Completed (5 fixes)
1. **S1** - Integer validation in github.py:148 ✅
2. **P3** - Single aggregation query in _helpers.py ✅
3. **C1** - Fix N+1 in LLM batch (lines 304-305, NOT 307) ✅
4. **C2** - Requeue depth limit in metrics.py ✅
5. **P2** - Add .only() to ai_metrics.py:249-253 ✅

### Skipped (per user)
- **S2/S3** - Slack integration not active

---

## Critical Files Modified

### Security Files

| File | Line(s) | Status | Change |
|------|---------|--------|--------|
| `apps/integrations/views/github.py` | 148 | ✅ DONE | try/except for int() |
| `apps/integrations/webhooks/slack_interactions.py` | 109, 163 | ⏭️ SKIPPED | - |

### Performance Files (Views/Services)

| File | Line(s) | Status | Change |
|------|---------|--------|--------|
| `apps/metrics/services/dashboard/_helpers.py` | 57-70 | ✅ DONE | Single aggregate |
| `apps/metrics/services/dashboard/ai_metrics.py` | 249-253 | ✅ DONE | Added .only() |
| `apps/metrics/services/dashboard/pr_metrics.py` | 55-73 | ❓ DEFERRED | May be false positive |

### Celery Task Files

| File | Line(s) | Status | Change |
|------|---------|--------|--------|
| `apps/metrics/tasks.py` | 304-305 | ✅ DONE | Changed values_list to .all() |
| `apps/integrations/_task_modules/metrics.py` | 132, 243-266 | ✅ DONE | Added requeue_depth |

---

## Key Discoveries This Session

### 1. `values_list()` Bypasses Prefetch Cache

**Original diagnosis**: Plan said line 307 (`pr.reviews.all()`) was N+1
**Actual issue**: Lines 304-305 using `values_list()` which creates new query

```python
# WRONG - bypasses prefetch cache (triggers query per PR)
file_paths = list(pr.files.values_list("filename", flat=True))

# CORRECT - uses prefetch cache
file_paths = [f.filename for f in pr.files.all()]
```

### 2. QuerySet.count() Uses Result Cache

Django's count() method checks `_result_cache` first:
```python
def count(self):
    if self._result_cache is not None:
        return len(self._result_cache)
    return self.query.get_count(using=self.db)
```

So iteration followed by `.count()` = 1 query total (not 2).

### 3. Requeue Depth Pattern

```python
MAX_REQUEUE_DEPTH = 50

@shared_task(bind=True, ...)
def queue_llm_analysis_batch_task(self, team_id: int, batch_size: int = 50, requeue_depth: int = 0):
    # ... processing ...

    if remaining_prs > 0:
        if requeue_depth >= MAX_REQUEUE_DEPTH:
            logger.warning(f"Max requeue depth reached...")
            _advance_llm_pipeline_status(team)
            return {"warning": f"max_requeue_depth ({MAX_REQUEUE_DEPTH}) reached"}

        self.apply_async(
            args=[team_id],
            kwargs={"batch_size": batch_size, "requeue_depth": requeue_depth + 1},
            countdown=2,
        )
```

---

## Test Files Created/Modified

### New Test Files
- `apps/integrations/tests/test_metrics_task.py` - C2 requeue depth tests

### Modified Test Files
- `apps/integrations/tests/test_views.py` - S1 tests (2 new)
- `apps/metrics/tests/dashboard/test_key_metrics.py` - P3 test
- `apps/metrics/tests/test_llm_tasks.py` - C1 tests (2 new)
- `apps/metrics/tests/dashboard/test_ai_metrics.py` - P2 RED test

---

## Remaining Tasks

| Task | Priority | Status |
|------|----------|--------|
| P1: Survey prefetch | Deferred | May be false positive |
| C3: Parallelize insights | Medium | Not started |
| C4: Subscription errors | Medium | Not started |
| P4-5, C5 | Low | Not started |

---

## Commands Reference

```bash
# Working directory
cd /Users/yanchuk/Documents/GitHub/tformance-db-audit

# Run specific test
/Users/yanchuk/Documents/GitHub/tformance/.venv/bin/pytest \
  apps/path/to/test.py::TestClass::test_method -v --tb=short

# Run all tests for a module
/Users/yanchuk/Documents/GitHub/tformance/.venv/bin/pytest \
  apps/metrics/tests/dashboard/ -v --tb=short

# Check git status
git status

# Git diff to see all changes
git diff
```

---

## No Migrations Needed

All changes are query optimizations and logic fixes. No model changes were made.
