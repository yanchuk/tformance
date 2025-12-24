# GitHub Data Processing - Systematic Guide

**Last Updated:** 2025-12-23
**Purpose:** Ensure complete data processing when seeding from real GitHub data

## Overview

When fetching GitHub data for demo/seeding purposes, several post-processing steps are needed to ensure all metrics display correctly on dashboards.

## Lessons from Gumroad Data

Issues encountered and fixes applied:

| Issue | Root Cause | Fix Applied | Systematic Solution |
|-------|------------|-------------|---------------------|
| AI tools not detected | Missing patterns for Devin, autofix | Added to `ai_patterns.py` | ✅ Patterns now in codebase |
| Iteration metrics empty | Not calculated during sync | Management command | ❌ Should be calculated on PR merge |
| Old dates showing 0 metrics | Demo data outside date range | Date shift command | N/A (demo-specific) |

## Data Processing Checklist

### For Real GitHub Data Seeding

Run these commands **after** initial GitHub sync completes:

```bash
# 1. Re-parse AI co-authors (picks up any missed patterns)
python manage.py parse_ai_coauthors --team <TeamName>

# 2. Calculate iteration metrics for merged PRs
python manage.py calculate_iteration_metrics --team <TeamName>

# 3. Verify data (optional)
python manage.py shell
>>> from apps.metrics.models import PullRequest
>>> PullRequest.objects.filter(team__name="<TeamName>", state="merged", review_rounds__isnull=True).count()
# Should be 0
```

### For Demo Data Seeding

Additional step to ensure dates are current:

```bash
# Shift dates forward if needed (e.g., 68 days)
python manage.py fix_gumroad_dates --team <TeamName> --days 68
```

## Systematic Improvements Needed

### High Priority - Add to PR Sync Flow

**Iteration Metrics Calculation**: Currently calculated by management command. Should be calculated automatically when PR is merged.

**Location to modify:** `apps/integrations/tasks.py` or webhook handler

```python
# After PR merge is detected:
def on_pr_merged(pr: PullRequest):
    # Calculate iteration metrics
    reviews = pr.reviews.all()
    pr.review_rounds = reviews.values("reviewer").distinct().count()
    pr.total_comments = reviews.exclude(body="").count()
    # ... etc
    pr.save()
```

### Medium Priority - Already Fixed

**AI Pattern Detection**: Devin and autofix patterns added to `ai_patterns.py`. These are used during commit processing via `parse_co_authors()`.

### Low Priority - Demo-Specific

**Date Shifting**: Only needed for demo data. Not part of production flow.

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | AI tool detection patterns |
| `apps/metrics/services/ai_detector.py` | AI detection logic |
| `apps/integrations/tasks.py` | GitHub sync Celery tasks |
| `apps/metrics/management/commands/` | One-time processing commands |

## Celery Jobs That Process GitHub Data

| Task | Trigger | What It Does |
|------|---------|--------------|
| `sync_repository_task` | Manual/scheduled | Full repo sync |
| `sync_pr_task` | Webhook/manual | Single PR sync |
| `fetch_pr_complete_data_task` | PR merge | Fetch complete PR data |

## Future Improvements

1. **Add iteration metrics to PR merge flow** - Calculate review_rounds, commits_after_first_review, etc. when PR is merged
2. **Pattern version tracking** - Reprocess commits when PATTERNS_VERSION changes
3. **Data validation command** - Check for missing metrics across all PRs
