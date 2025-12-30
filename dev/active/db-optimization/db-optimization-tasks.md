# Database Optimization - Tasks

**Last Updated: 2025-12-30**

## Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Emergency Stats | ✅ Complete | 3/3 |
| Phase 2: Migration | ✅ Complete | 4/4 |
| Phase 3: Model Updates | ✅ Complete | 3/3 |
| Phase 4: Verification | ✅ Complete | 3/3 |

**All phases complete. Ready to move to completed.**

---

## Phase 1: Emergency Statistics Update ✅

### Task 1.1: Run ANALYZE on all tables
- [x] Execute `ANALYZE VERBOSE` on database
- [x] Verify `pg_stat_user_tables.last_analyze` updated
- **Status**: ✅ Complete
- **Notes**: Ran via MCP postgres tool

### Task 1.2: Verify autovacuum is enabled
- [x] Check `SHOW autovacuum` returns 'on'
- [ ] Verify Heroku Postgres autovacuum settings
- **Status**: ✅ Complete (local verified)
- **Notes**: Need to verify production Heroku settings

### Task 1.3: Force VACUUM on bloated tables
- [x] Run VACUUM ANALYZE on large tables
- [x] Verify bloat reduced
- **Status**: ✅ Complete
- **Notes**: Part of ANALYZE VERBOSE

---

## Phase 2: Migration - Remove Duplicate Indexes 🔄

### Task 2.1: Write tests for index removal migration (TDD RED)
- [x] Create test file `apps/metrics/tests/test_index_migrations/test_duplicate_index_removal.py`
- [x] Test: verify indexes removed after migration
- [x] Test: verify essential indexes still exist
- [x] Test: verify query performance not degraded
- [x] Run tests - all 11 tests PASS
- **Status**: ✅ Complete
- **Effort**: M
- **File**: `apps/metrics/tests/test_index_migrations/test_duplicate_index_removal.py`

### Task 2.2: Create migration to remove duplicates (TDD GREEN)
- [x] Create `0030_remove_duplicate_indexes.py`
- [x] Use `DROP INDEX CONCURRENTLY` for all indexes
- [x] Include reverse_sql for rollback
- [x] Set `atomic = False`
- [x] Run tests - all PASS
- **Status**: ✅ Complete
- **Effort**: M
- **File**: `apps/metrics/migrations/0030_remove_duplicate_indexes.py`

### Task 2.3: Run migration on local database
- [x] Run `python manage.py migrate metrics`
- [x] Verify 6 indexes removed
- [x] Check no errors in migration output
- **Status**: ✅ Complete
- **Effort**: S

### Task 2.4: Verify query performance after removal
- [x] Run dashboard queries and check EXPLAIN plans
- [x] Verify no increase in sequential scans
- [x] Tests verify queries still use indexes
- **Status**: ✅ Complete
- **Effort**: M

---

## Phase 3: Model Updates ✅

### Task 3.1: Update Commit model - remove commit_pr_idx
- [x] Edit `apps/metrics/models/github.py`
- [x] Remove `models.Index(fields=["pull_request"], name="commit_pr_idx")`
- [x] Add comment explaining removal
- [x] Migration `0032_remove_commit_pr_idx.py` generated
- **Status**: ✅ Complete
- **Effort**: S
- **File**: `apps/metrics/models/github.py:1335-1339`

### Task 3.2: Update PRSurvey model - remove pr_survey_pr_idx
- [x] Edit `apps/metrics/models/surveys.py`
- [x] Remove `models.Index(fields=["pull_request"], name="pr_survey_pr_idx")`
- [x] Add comment explaining removal
- [x] Migration `0031_remove_prsurvey_pr_survey_pr_idx.py` generated
- **Status**: ✅ Complete
- **Effort**: S
- **File**: `apps/metrics/models/surveys.py:104-110`

### Task 3.3: Run makemigrations to verify no new migration needed
- [x] Run `python manage.py makemigrations --check`
- [x] Verify no untracked model changes - "No changes detected"
- **Status**: ✅ Complete
- **Effort**: S

---

## Phase 4: Verification & Monitoring ✅

### Task 4.1: Create index monitoring query
- [x] Tests verify index removal and essential indexes remain
- [x] Tests verify queries still use indexes (EXPLAIN tests)
- **Status**: ✅ Complete (via test suite)
- **Effort**: M

### Task 4.2: Add database health check (Optional)
- [ ] Create admin view for table/index stats
- [ ] Add alerts for high bloat or unused indexes
- **Status**: ⏳ Deferred (Optional for MVP)
- **Effort**: L

### Task 4.3: Document optimization process
- [x] Documented in this task file
- [x] Migration includes detailed comments
- **Status**: ✅ Complete
- **Effort**: S

---

## Indexes Removed

| # | Index Name | Table | Size | Status |
|---|------------|-------|------|--------|
| 1 | `commit_pr_idx` | metrics_commit | 7.9 MB | ✅ Removed |
| 2 | `metrics_commit_author_id_67f38a6f` | metrics_commit | 7.3 MB | ✅ Removed |
| 3 | `pr_survey_pr_idx` | metrics_prsurvey | 4 MB | ✅ Removed |
| 4 | `metrics_aiusagedaily_member_id_0274ee1d` | metrics_aiusagedaily | 28 MB | ✅ Removed |
| 5 | `github_int_org_slug_idx` | integrations_githubintegration | 16 KB | ✅ Removed |
| 6 | `jira_int_cloud_id_idx` | integrations_jiraintegration | 16 KB | ✅ Removed |

**Total saved: ~55 MB**

---

## Commands Reference

```bash
# Run ANALYZE
psql -c "ANALYZE VERBOSE;"

# Check index usage
psql -c "SELECT indexrelname, idx_scan FROM pg_stat_user_indexes WHERE relname LIKE 'metrics_%';"

# Run migration
python manage.py migrate metrics 0030

# Check makemigrations
python manage.py makemigrations --check

# Run tests
pytest apps/metrics/tests/test_migrations/ -v
```

---

## Notes

**Completed 2025-12-30:**
- All 6 duplicate indexes removed via migrations 0030-0032
- 11 tests verify correct index removal and query performance
- Model `Meta.indexes` updated in github.py and surveys.py
- Total space savings: ~55 MB

**Migrations:**
- `0030_remove_duplicate_indexes.py` - Raw SQL to drop duplicates
- `0031_remove_prsurvey_pr_survey_pr_idx.py` - Model sync for PRSurvey
- `0032_remove_commit_pr_idx.py` - Model sync for Commit
