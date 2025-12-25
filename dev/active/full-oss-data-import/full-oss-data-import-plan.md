# Full OSS Data Import Plan

**Last Updated: 2025-12-25**

## Executive Summary

Import complete PR data from OSS repos without artificial limits to enable:
1. Real-world data analysis with actual team sizes
2. Full 2025 data for yearly trends
3. Quarter-over-Quarter and Month-over-Month comparisons

## Current State

| Setting | Current Value | Issue |
|---------|---------------|-------|
| max_prs | 300 | Misses older PRs |
| max_members | 50 | Excludes contributors |
| days_back | 90 | Only 3 months of data |
| files | Unlimited per PR | Could be kept or limited |

## Proposed Changes

### Phase 1: Batch Import Infrastructure

**Goal:** Import data in time-based batches to handle rate limits and timeouts

```python
# New command options
python manage.py seed_real_projects \
    --project twenty \
    --start-date 2025-01-01 \
    --end-date 2025-03-31 \
    --no-pr-limit \
    --no-member-limit \
    --max-files-per-pr 100  # Optional limit
```

**Batch Strategy:**
- Split 2025 into 4 quarters: Q1, Q2, Q3, Q4
- Each quarter runs as separate command
- Cache checkpoints between runs
- Resume capability if interrupted

### Phase 2: Remove Artificial Limits

**Changes to `real_projects.py`:**
```python
@dataclass
class RealProjectConfig:
    max_prs: int | None = None  # None = unlimited
    max_members: int | None = None  # None = unlimited
    max_files_per_pr: int = 100  # Keep reasonable limit
    days_back: int = 90
    # New fields
    start_date: datetime | None = None
    end_date: datetime | None = None
```

### Phase 3: Period Comparison Analytics

**New views in `apps/metrics/views/analytics_views.py`:**
- Quarter-over-Quarter comparison
- Month-over-Month comparison
- Year-to-date trends

**Data requirements:**
- Full 2025 data (Jan 1 - Dec 31)
- ~12 months × repos = significant data volume

## Implementation Phases

### Immediate (Phase 1): Batch Import Commands

1. Add `--start-date` and `--end-date` to management command
2. Add `--no-pr-limit` and `--no-member-limit` flags
3. Modify GraphQL fetcher to accept date range
4. Test with Q4 2025 (Oct-Dec) as pilot

### Short-term (Phase 2): Full 2025 Import

1. Import Q4 2025 (current quarter)
2. Import Q3 2025 (Jul-Sep)
3. Import Q2 2025 (Apr-Jun)
4. Import Q1 2025 (Jan-Mar)

### Medium-term (Phase 3): Period Analytics

1. Add QoQ comparison dashboard
2. Add MoM comparison dashboard
3. Add yearly trend charts

## Risk Assessment

### Rate Limits
- **Risk:** GitHub API rate limits (5000/hour authenticated)
- **Mitigation:** Use GraphQL (fewer calls), add delays, use token rotation

### Data Volume
- **Risk:** Large PRs with many files could slow import
- **Mitigation:** Keep `--max-files-per-pr 100` limit

### Timeouts
- **Risk:** Large repos timeout during fetch
- **Mitigation:** Batch by time period, checkpoint progress

## Recommended Immediate Action

**Stop current process and run batch imports:**

```bash
# Q4 2025 (Oct 1 - Dec 25)
python manage.py seed_real_projects \
    --project twenty \
    --start-date 2025-10-01 \
    --end-date 2025-12-25 \
    --no-check-runs

# Then Q3, Q2, Q1...
```

## Success Metrics

1. All OSS repos have complete 2025 PR data
2. Team member count matches actual repo contributors
3. QoQ/MoM comparisons show meaningful trends
4. No data gaps between quarters
