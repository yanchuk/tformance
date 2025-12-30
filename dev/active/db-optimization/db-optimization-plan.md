# Database Optimization Plan

**Last Updated: 2025-12-30**

## Executive Summary

This plan addresses critical PostgreSQL performance issues identified in a database audit:
1. **No VACUUM/ANALYZE running** - All tables show NULL for last_vacuum/analyze
2. **~55 MB of duplicate indexes** consuming space and slowing writes
3. **High index-to-data ratio** on some tables (aiusagedaily: 1.43x)
4. **Excessive sequential scans** due to stale statistics

**Expected Impact:**
- ~55 MB storage savings (duplicate index removal)
- Improved query planning (after ANALYZE runs)
- Faster write operations (fewer indexes to maintain)
- Better autovacuum behavior

---

## Current State Analysis

### Table Statistics (Key Tables)

| Table | Rows | Data Size | Index Size | Ratio | Seq Scans |
|-------|------|-----------|------------|-------|-----------|
| metrics_aiusagedaily | 2.76M | 321 MB | 460 MB | 1.43x | 1 |
| metrics_prfile | 1.34M | 198 MB | 249 MB | 1.26x | 3 |
| metrics_pullrequest | 168K | 198 MB | 94 MB | 0.47x | 65 |
| metrics_commit | 675K | 152 MB | 137 MB | 0.90x | 0 |
| metrics_prsurvey | 129K | 13 MB | 25 MB | 1.92x | 145 ⚠️ |
| metrics_weeklymetrics | 271K | 34 MB | 36 MB | 1.06x | 1 |

### Critical Issues

1. **VACUUM/ANALYZE Never Run**
   - All metrics tables show `last_vacuum: NULL`, `last_autovacuum: NULL`
   - Query planner has no statistics → poor index selection
   - Dead rows accumulating → bloat

2. **Duplicate Indexes Identified**

   | Index to DROP | Duplicates | Size |
   |---------------|------------|------|
   | `commit_pr_idx` | `metrics_commit_pull_request_id_*` | 7.9 MB |
   | `pr_survey_pr_idx` | `metrics_prsurvey_pull_request_id_key` | 4 MB |
   | `metrics_aiusagedaily_member_id_*` | Covered by `ai_usage_member_date_idx` | 28 MB |
   | `metrics_commit_author_id_*` | Covered by `commit_author_date_idx` | 7.3 MB |
   | `github_int_org_slug_idx` | Auto-generated index | 16 KB |
   | `jira_int_cloud_id_idx` | Auto-generated index | 16 KB |

3. **Redundant _like Indexes** (~6 MB)
   - Pattern indexes for `varchar_pattern_ops` that aren't used

---

## Proposed Future State

### After Implementation

1. **Autovacuum properly configured and running**
2. **Duplicate indexes removed** saving ~55 MB
3. **Index-to-data ratios normalized**
4. **Sequential scans reduced** via proper statistics
5. **Monitoring in place** for future optimization

### Target Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Total index overhead | ~1.2 GB | ~1.1 GB |
| Duplicate indexes | 6 pairs | 0 |
| Tables with stale stats | ALL | 0 |
| prsurvey seq_scans | 145 | <10 |

---

## Implementation Phases

### Phase 1: Emergency Statistics Update (Day 1)
Run ANALYZE immediately to fix query planning issues.

### Phase 2: Migration - Remove Duplicate Indexes (Day 1-2)
Create and test migration to drop duplicate indexes.

### Phase 3: Model Updates (Day 2)
Update Django models to remove explicit index definitions.

### Phase 4: Verification & Monitoring (Day 3+)
Verify changes and set up ongoing monitoring.

---

## Detailed Tasks

### Phase 1: Emergency Statistics Update

**Task 1.1: Run ANALYZE on all tables**
- Effort: S
- Dependencies: None
- Acceptance Criteria:
  - `ANALYZE VERBOSE` completes successfully
  - `pg_stat_user_tables.last_analyze` shows recent timestamp

**Task 1.2: Verify autovacuum is enabled**
- Effort: S
- Dependencies: None
- Acceptance Criteria:
  - `SHOW autovacuum` returns 'on'
  - Autovacuum thresholds are appropriate for table sizes

**Task 1.3: Force VACUUM on bloated tables**
- Effort: S
- Dependencies: Task 1.1
- Acceptance Criteria:
  - `VACUUM ANALYZE` runs on aiusagedaily, pullrequest, prfile
  - Bloat reduced (check with bloat query)

### Phase 2: Migration - Remove Duplicate Indexes

**Task 2.1: Write tests for index removal migration**
- Effort: M
- Dependencies: None (TDD: RED phase)
- Acceptance Criteria:
  - Test verifies indexes exist before migration
  - Test verifies indexes removed after migration
  - Test covers all 6 duplicate index pairs

**Task 2.2: Create migration to remove duplicates**
- Effort: M
- Dependencies: Task 2.1 (TDD: GREEN phase)
- Acceptance Criteria:
  - Migration uses `DROP INDEX CONCURRENTLY`
  - Migration has reverse operations
  - All 6 duplicate indexes removed

**Task 2.3: Run migration on local database**
- Effort: S
- Dependencies: Task 2.2
- Acceptance Criteria:
  - Migration applies without errors
  - Index count reduced by 6
  - No query performance regression

**Task 2.4: Verify query performance after removal**
- Effort: M
- Dependencies: Task 2.3
- Acceptance Criteria:
  - Dashboard queries still use indexes
  - No increase in sequential scans
  - Response times maintained or improved

### Phase 3: Model Updates

**Task 3.1: Update Commit model - remove commit_pr_idx**
- Effort: S
- Dependencies: Task 2.2
- Acceptance Criteria:
  - `Meta.indexes` no longer includes `commit_pr_idx`
  - Comment explains why index removed

**Task 3.2: Update PRSurvey model - remove pr_survey_pr_idx**
- Effort: S
- Dependencies: Task 2.2
- Acceptance Criteria:
  - `Meta.indexes` no longer includes `pr_survey_pr_idx`
  - Comment explains OneToOneField has implicit unique index

**Task 3.3: Run makemigrations to verify no new migration needed**
- Effort: S
- Dependencies: Tasks 3.1, 3.2
- Acceptance Criteria:
  - `makemigrations --check` passes
  - No untracked model changes

### Phase 4: Verification & Monitoring

**Task 4.1: Create index monitoring query**
- Effort: M
- Dependencies: Phase 2
- Acceptance Criteria:
  - Query shows unused indexes
  - Query shows duplicate indexes
  - Can be run periodically

**Task 4.2: Add database health check to admin**
- Effort: L (Optional)
- Dependencies: Task 4.1
- Acceptance Criteria:
  - Admin view shows table/index stats
  - Alerts on high bloat or unused indexes

**Task 4.3: Document optimization process**
- Effort: S
- Dependencies: All phases
- Acceptance Criteria:
  - `dev/guides/DATABASE-OPTIMIZATION.md` created
  - Documents audit process
  - Documents ongoing monitoring

---

## Risk Assessment

### High Risk
- **Query performance regression** after index removal
  - Mitigation: Test on staging first, monitor after deploy
  - Rollback: Migration has reverse operations

### Medium Risk
- **Autovacuum not configured in production**
  - Mitigation: Verify Heroku Postgres settings
  - Mitigation: Document expected autovacuum behavior

### Low Risk
- **Migration fails on production**
  - Mitigation: Uses `CONCURRENTLY` for non-blocking
  - Mitigation: Test on staging first

---

## Success Metrics

1. **Storage reduced** by ~55 MB after index removal
2. **Query plans improved** - fewer sequential scans on prsurvey
3. **Autovacuum running** - tables show recent vacuum timestamps
4. **No performance regression** in dashboard load times
5. **Tests passing** - all existing tests continue to pass

---

## Required Resources

### Technical
- PostgreSQL superuser access (for ANALYZE/VACUUM)
- Django migrations
- Test coverage

### Time Estimates
- Phase 1: 1 hour
- Phase 2: 2-3 hours
- Phase 3: 30 minutes
- Phase 4: 2-4 hours
- **Total: 1 day**

### Dependencies
- Heroku Postgres configuration (verify autovacuum settings)
- Staging environment for testing migration
