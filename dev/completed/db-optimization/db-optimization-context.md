# Database Optimization - Context

**Last Updated: 2025-12-30**

## Key Files

### Models (Index Definitions)
- `apps/metrics/models/github.py` - PullRequest, PRReview, Commit, PRFile, PRComment
- `apps/metrics/models/surveys.py` - PRSurvey, PRSurveyReview
- `apps/metrics/models/aggregations.py` - AIUsageDaily, WeeklyMetrics, ReviewerCorrelation
- `apps/metrics/models/team.py` - TeamMember
- `apps/integrations/models.py` - GitHubIntegration, JiraIntegration

### Existing Migration Files
- `apps/metrics/migrations/0026_cleanup_unused_indexes.py` - Previous index cleanup
- `apps/metrics/migrations/0028_drop_unused_indexes_optimize_db.py` - More cleanup
- `apps/metrics/migrations/0030_remove_duplicate_indexes.py` - **NEW** (created)

### Services Using Indexes
- `apps/metrics/services/dashboard_service.py` - Dashboard queries with select_related/prefetch_related
- `apps/metrics/services/pr_list_service.py` - PR list queries
- `apps/metrics/services/quick_stats.py` - Quick stats queries
- `apps/metrics/services/aggregation_service.py` - Aggregation queries

---

## Key Decisions Made

### 1. Which indexes to remove (duplicate pairs)

| Keep | Drop | Reason |
|------|------|--------|
| `metrics_commit_pull_request_id_06f35677` | `commit_pr_idx` | Django auto-generates FK indexes |
| `metrics_prsurvey_pull_request_id_key` | `pr_survey_pr_idx` | OneToOneField has unique constraint |
| `ai_usage_member_date_idx` | `metrics_aiusagedaily_member_id_*` | Composite covers single-column |
| `commit_author_date_idx` | `metrics_commit_author_id_*` | Composite covers single-column |
| Auto-generated org_slug | `github_int_org_slug_idx` | Duplicate manual index |
| Auto-generated cloud_id | `jira_int_cloud_id_idx` | Duplicate manual index |

### 2. Why use DROP INDEX CONCURRENTLY
- Non-blocking - doesn't lock the table
- Safe for production deployment
- Required for `atomic = False` in migration

### 3. Index removal strategy
- Remove from Django model Meta.indexes
- Create migration with RunSQL to drop
- Include reverse_sql for rollback capability

---

## Dependencies

### Database
- PostgreSQL 17.7 (from MCP connection info)
- Autovacuum must be enabled

### Django
- Django 5.2.9
- Migration framework with RunSQL support

### Heroku (Production)
- Heroku Postgres manages autovacuum settings
- `heroku pg:settings` can verify configuration

---

## SQL Queries for Verification

### Check duplicate indexes
```sql
SELECT
    a.indexrelid::regclass AS index1,
    b.indexrelid::regclass AS index2,
    a.indrelid::regclass AS table_name
FROM pg_index a
JOIN pg_index b ON a.indrelid = b.indrelid
    AND a.indexrelid != b.indexrelid
    AND a.indkey::text = b.indkey::text
WHERE a.indrelid::regclass::text LIKE 'metrics_%';
```

### Check unused indexes
```sql
SELECT
    schemaname || '.' || relname AS table_name,
    indexrelname AS index_name,
    idx_scan AS times_used,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE relname LIKE 'metrics_%' AND idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Check vacuum status
```sql
SELECT
    relname,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables
WHERE relname LIKE 'metrics_%';
```

### Check table bloat
```sql
SELECT
  tablename,
  ROUND((CASE WHEN otta=0 THEN 0.0 ELSE sml.relpages/otta::numeric END),1) AS tbloat,
  pg_size_pretty(CASE WHEN relpages < otta THEN 0
    ELSE bs*(sml.relpages-otta)::bigint END) AS wastedsize
FROM ... -- (full bloat query from analysis)
```

---

## Test Patterns

### Testing index existence
```python
from django.db import connection

def test_index_exists(index_name):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 1 FROM pg_indexes
            WHERE indexname = %s
        """, [index_name])
        return cursor.fetchone() is not None
```

### Testing migration runs without error
```python
from django.core.management import call_command

def test_migration_applies():
    call_command('migrate', 'metrics', '0030', verbosity=0)
    # Verify indexes removed
```

---

## Related Documentation

- `CLAUDE.md` - Project coding guidelines
- `prd/DATA-MODEL.md` - Database schema documentation
- `dev/guides/HEROKU-DEPLOYMENT.md` - Deployment procedures

---

## Notes

### Why autovacuum wasn't running
Possible causes:
1. Tables not meeting autovacuum thresholds (unlikely with 2.7M rows)
2. Autovacuum disabled at Heroku level
3. Database recently restored from backup (stats reset)

### Expected behavior after ANALYZE
- Query planner will use statistics to choose indexes
- Sequential scans on `metrics_prsurvey` should decrease
- Index scans should increase on properly-indexed columns

### Future optimization candidates
If more optimization needed:
1. Table partitioning for `metrics_aiusagedaily` (2.7M+ rows)
2. Partial indexes for common query patterns
3. Consider archiving old data (data retention policy)
