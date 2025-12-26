# Database Scaling Strategy

Last updated: 2025-12-26

## Current State

| Metric | Value |
|--------|-------|
| PostgreSQL Version | 17.7 |
| Database Size | ~1.2 GB |
| Total Rows | ~3M |
| Cache Hit Ratio | 99.4% |
| Largest Table | `metrics_aiusagedaily` (43%) |

## Table Growth Projections

### AIUsageDaily (Copilot/Cursor metrics)
Only teams with active Copilot/Cursor integration generate data.

| Teams with Copilot | Members | Days/Year | Rows | Storage |
|--------------------|---------|-----------|------|---------|
| 10 | 500 | 365 | ~365K | ~40 MB |
| 50 | 2,500 | 365 | ~1.8M | ~200 MB |
| 100 | 5,000 | 365 | ~3.6M | ~400 MB |
| 500 | 25,000 | 365 | ~18M | ~2 GB |

### PullRequest
Grows with team activity.

| Teams | PRs/Year | Total PRs | Storage |
|-------|----------|-----------|---------|
| 50 | 500/team | 25K | ~500 MB |
| 100 | 500/team | 50K | ~1 GB |
| 500 | 500/team | 250K | ~5 GB |

## Scaling Tiers

### Tier 1: MVP (Current - 50 teams)
**No changes needed**

- PostgreSQL handles 10-20 GB easily
- Current indexes are efficient
- Cache hit ratio excellent

### Tier 2: Growth (50-200 teams)
**Recommended changes:**

1. **Enable Redis cache**
   ```bash
   USE_REDIS_CACHE=True  # in .env
   ```

2. **Add read replica** for dashboard queries
   - Point `for_team` manager to replica
   - Keep writes on primary

3. **Connection pooling** (PgBouncer)
   ```
   # If > 50 concurrent connections
   DATABASES['default']['CONN_MAX_AGE'] = 0  # Let PgBouncer handle
   ```

### Tier 3: Scale (200-1000 teams)
**Major changes:**

1. **Partition AIUsageDaily by month**
   ```python
   # Migration to add partitioning
   class Migration(migrations.Migration):
       operations = [
           migrations.RunSQL("""
               ALTER TABLE metrics_aiusagedaily
               RENAME TO metrics_aiusagedaily_old;

               CREATE TABLE metrics_aiusagedaily (
                   LIKE metrics_aiusagedaily_old INCLUDING ALL
               ) PARTITION BY RANGE (date);

               -- Create monthly partitions
               CREATE TABLE metrics_aiusagedaily_2025_01
                   PARTITION OF metrics_aiusagedaily
                   FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
               -- ... more partitions
           """)
       ]
   ```

2. **Consider TimescaleDB** for time-series data
   - Better compression (10x)
   - Automatic partitioning
   - Continuous aggregates

3. **Move to managed PostgreSQL**
   - **Neon**: Best for variable workloads (scale-to-zero)
   - **Supabase**: Best for full-stack features
   - **AWS RDS**: Best for compliance/control

### Tier 4: Enterprise (1000+ teams)
**Architecture changes:**

1. **Sharding by team_id**
   - Use Citus or application-level sharding
   - Route queries based on team context

2. **Separate databases**
   - Analytics DB (read-heavy, aggregated)
   - Operational DB (write-heavy, transactional)

3. **Data warehouse**
   - Move historical data to ClickHouse/BigQuery
   - Keep only recent data in PostgreSQL

## Data Retention

### Automatic Cleanup
Monthly Celery task removes old data:

```bash
# Preview what would be deleted
python manage.py cleanup_old_data --dry-run

# Manual cleanup with custom retention
python manage.py cleanup_old_data --days 365
```

### Retention Periods
| Table | Default | Configurable |
|-------|---------|--------------|
| AIUsageDaily | 365 days | Yes |
| WeeklyMetrics | 730 days | Yes |
| PullRequest | Forever | No (core data) |

## Index Maintenance

### Unused Indexes (Dropped 2025-12-26)
- `ai_usage_date_idx` (13 MB)
- `ai_usage_source_date_idx` (15 MB)
- `commit_repo_date_idx` (16 MB)
- `weekly_metrics_week_idx` (1.7 MB)

### Monitor Index Usage
```sql
-- Find unused indexes
SELECT indexrelname, idx_scan, pg_size_pretty(pg_relation_size(indexrelid))
FROM pg_stat_user_indexes
WHERE idx_scan < 100
ORDER BY pg_relation_size(indexrelid) DESC;
```

### Regular Maintenance
```sql
-- Run weekly
VACUUM ANALYZE;

-- After bulk deletes
VACUUM FULL metrics_aiusagedaily;  -- Warning: locks table
```

## Hosting Recommendations

| Scale | Provider | Monthly Cost | Notes |
|-------|----------|--------------|-------|
| MVP (<50 teams) | Self-hosted/Render | $0-20 | Simple, predictable |
| Growth (50-200) | Neon | $19-69 | Scale-to-zero |
| Scale (200-1000) | Supabase/RDS | $100-500 | Read replicas |
| Enterprise (1000+) | AWS RDS/Aurora | $500+ | Multi-AZ, sharding |

## Monitoring Checklist

### Weekly
- [ ] Check cache hit ratio (should be >99%)
- [ ] Review slow query log
- [ ] Monitor connection count

### Monthly
- [ ] Run `cleanup_old_data --dry-run`
- [ ] Check table bloat with `pg_stat_user_tables`
- [ ] Review index usage statistics

### Quarterly
- [ ] Analyze query patterns for new indexes
- [ ] Review storage growth trends
- [ ] Plan capacity for next quarter

## Emergency Procedures

### Database Too Large
```bash
# 1. Check what's taking space
python manage.py dbshell
\dt+ metrics_*

# 2. Run cleanup with shorter retention
python manage.py cleanup_old_data --days 180

# 3. Reclaim space
VACUUM FULL;
```

### Slow Queries
```sql
-- Find slow queries
SELECT query, calls, mean_time, total_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 20;

-- Check for missing indexes
SELECT relname, seq_scan, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan * 10
AND n_live_tup > 10000;
```
