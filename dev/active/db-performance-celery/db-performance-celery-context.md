# Database Performance & Celery Worker Configuration

## Overview

Analysis and optimization of database performance during seeding operations, plus production PostgreSQL and Celery worker recommendations.

## Key Findings

### Current Database State (Dec 2025)

| Metric | Value |
|--------|-------|
| Database Size | 955 MB |
| Total PRs | 51,465 |
| Cache Hit Ratio | 99.82% |
| Active Connections | 6 |
| Size per PR | ~19.5 KB (including related data) |

### Table Sizes

| Table | Rows | Total Size |
|-------|------|------------|
| metrics_aiusagedaily | 1.3M | 388 MB |
| metrics_prfile | 432K | 157 MB |
| metrics_pullrequest | 49K | 125 MB |
| metrics_commit | 203K | 100 MB |
| metrics_weeklymetrics | 253K | 65 MB |

### AIUsageDaily Structure

**Formula**: `Members × Days × 0.85 (workdays) × ai_adoption_rate`

This is **per-member per-day**, NOT per-repo:
- Vercel: 4,505 members × 66 days = 377,822 records
- LangChain: 4,660 members × 66 days = 360,190 records

### Seeding Bottlenecks (FIXED)

| Issue | Before | After |
|-------|--------|-------|
| AIUsageDaily | `update_or_create()` per record | `bulk_create(update_conflicts=True)` |
| WeeklyMetrics | Per-member per-week queries | Pre-fetch + bulk upsert |
| Queries | ~1.3M individual | ~260 bulk operations |
| Speed | ~30 min | ~2-3 min (estimated 10-15x faster) |

## Changes Made

### 1. AIUsageDaily Bulk Insert (`survey_ai_simulator.py`)

```python
# Before: O(n) individual queries
AIUsageDaily.objects.update_or_create(...)

# After: O(1) bulk upsert per 5000 records
AIUsageDaily.objects.bulk_create(
    records,
    update_conflicts=True,
    unique_fields=["team", "member", "date", "source"],
    update_fields=[...],
)
```

### 2. WeeklyMetrics Bulk Calculation (`real_project_seeder.py`)

- Pre-fetch all PR stats with `TruncWeek` aggregation
- Pre-fetch all commit stats with `TruncWeek` aggregation
- Build objects in memory
- Single bulk upsert at the end

### 3. Celery Worker Configuration (`settings.py`)

Added:
- `CELERY_WORKER_PREFETCH_MULTIPLIER = 4`
- `CELERY_TASK_ACKS_LATE = True`
- `CELERY_WORKER_MAX_TASKS_PER_CHILD = 100`
- Task routing for `sync`, `llm`, `compute` queues

## Files Modified

1. `apps/metrics/seeding/survey_ai_simulator.py` - Bulk AIUsageDaily
2. `apps/metrics/seeding/real_project_seeder.py` - Bulk WeeklyMetrics
3. `tformance/settings.py` - Celery configuration
