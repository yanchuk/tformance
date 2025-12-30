# Database Optimization - Tasks

**Last Updated: 2025-12-30**

## Progress Summary

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 1: Emergency Stats | ✅ Complete | 3/3 |
| Phase 2: Migration | 🔄 In Progress | 1/4 |
| Phase 3: Model Updates | ⏳ Pending | 0/3 |
| Phase 4: Verification | ⏳ Pending | 0/3 |

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
- [ ] Create test file `apps/metrics/tests/test_migrations/test_index_cleanup.py`
- [ ] Test: verify indexes exist before migration
- [ ] Test: verify indexes removed after migration
- [ ] Test: verify query performance not degraded
- [ ] Run tests - confirm they FAIL (RED phase)
- **Status**: ⏳ Pending
- **Effort**: M
- **Acceptance Criteria**: Tests fail because indexes still exist

### Task 2.2: Create migration to remove duplicates (TDD GREEN)
- [x] Create `0030_remove_duplicate_indexes.py`
- [x] Use `DROP INDEX CONCURRENTLY` for all indexes
- [x] Include reverse_sql for rollback
- [x] Set `atomic = False`
- [ ] Run tests - confirm they PASS (GREEN phase)
- **Status**: 🔄 Migration created, tests pending
- **Effort**: M
- **File**: `apps/metrics/migrations/0030_remove_duplicate_indexes.py`

### Task 2.3: Run migration on local database
- [ ] Run `python manage.py migrate metrics 0030`
- [ ] Verify 6 indexes removed
- [ ] Check no errors in migration output
- **Status**: ⏳ Pending
- **Effort**: S
- **Depends on**: Task 2.2

### Task 2.4: Verify query performance after removal
- [ ] Run dashboard queries and check EXPLAIN plans
- [ ] Verify no increase in sequential scans
- [ ] Check response times maintained
- **Status**: ⏳ Pending
- **Effort**: M
- **Depends on**: Task 2.3

---

## Phase 3: Model Updates ⏳

### Task 3.1: Update Commit model - remove commit_pr_idx
- [ ] Edit `apps/metrics/models/github.py`
- [ ] Remove `models.Index(fields=["pull_request"], name="commit_pr_idx")`
- [ ] Add comment explaining removal
- **Status**: ⏳ Pending
- **Effort**: S
- **File**: `apps/metrics/models/github.py:1335-1339`

### Task 3.2: Update PRSurvey model - remove pr_survey_pr_idx
- [x] Edit `apps/metrics/models/surveys.py`
- [x] Remove `models.Index(fields=["pull_request"], name="pr_survey_pr_idx")`
- [x] Add comment explaining removal
- **Status**: ✅ Complete
- **Effort**: S
- **File**: `apps/metrics/models/surveys.py:104-110`

### Task 3.3: Run makemigrations to verify no new migration needed
- [ ] Run `python manage.py makemigrations --check`
- [ ] Verify no untracked model changes
- **Status**: ⏳ Pending
- **Effort**: S
- **Depends on**: Tasks 3.1, 3.2

---

## Phase 4: Verification & Monitoring ⏳

### Task 4.1: Create index monitoring query
- [ ] Create SQL query for unused indexes
- [ ] Create SQL query for duplicate indexes
- [ ] Save queries in `dev/guides/DATABASE-MONITORING.md`
- **Status**: ⏳ Pending
- **Effort**: M

### Task 4.2: Add database health check (Optional)
- [ ] Create admin view for table/index stats
- [ ] Add alerts for high bloat or unused indexes
- **Status**: ⏳ Pending (Optional)
- **Effort**: L

### Task 4.3: Document optimization process
- [ ] Create `dev/guides/DATABASE-OPTIMIZATION.md`
- [ ] Document audit process
- [ ] Document ongoing monitoring procedures
- **Status**: ⏳ Pending
- **Effort**: S

---

## Indexes Being Removed

| # | Index Name | Table | Size | Status |
|---|------------|-------|------|--------|
| 1 | `commit_pr_idx` | metrics_commit | 7.9 MB | ⏳ |
| 2 | `metrics_commit_author_id_67f38a6f` | metrics_commit | 7.3 MB | ⏳ |
| 3 | `pr_survey_pr_idx` | metrics_prsurvey | 4 MB | ⏳ |
| 4 | `metrics_aiusagedaily_member_id_0274ee1d` | metrics_aiusagedaily | 28 MB | ⏳ |
| 5 | `github_int_org_slug_idx` | integrations_githubintegration | 16 KB | ⏳ |
| 6 | `jira_int_cloud_id_idx` | integrations_jiraintegration | 16 KB | ⏳ |

**Total to save: ~55 MB**

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

- Migration `0030_remove_duplicate_indexes.py` already created
- PRSurvey model already updated (Task 3.2 complete)
- Need to complete Commit model update (Task 3.1)
- Tests should be written before running migration (TDD)
