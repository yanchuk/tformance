# Database Performance & Celery Tasks

## Completed

- [x] Analyze database load during seeding
- [x] Document AIUsageDaily structure (per-member-per-day)
- [x] Optimize AIUsageDaily with bulk_create
- [x] Optimize WeeklyMetrics with pre-fetch + bulk upsert
- [x] Add Celery worker configuration
- [x] Add task routing for production queues

## Production Recommendations

### PostgreSQL Configuration

#### Tier 1: Starter (5-10 teams, ~100K PRs)
- Instance: 2 vCPU, 4 GB RAM, 50 GB SSD
- Cost: $50-100/mo

```ini
shared_buffers = 1GB
effective_cache_size = 3GB
work_mem = 16MB
maintenance_work_mem = 256MB
random_page_cost = 1.1
effective_io_concurrency = 200
max_connections = 100
```

#### Tier 2: Growth (20-50 teams, ~500K PRs)
- Instance: 4 vCPU, 8 GB RAM, 100 GB SSD
- Cost: $150-300/mo

```ini
shared_buffers = 2GB
effective_cache_size = 6GB
work_mem = 32MB
max_parallel_workers_per_gather = 4
max_connections = 200
```

#### Tier 3: Scale (100+ teams, ~2M PRs)
- Instance: 8+ vCPU, 32 GB RAM, 500 GB SSD + Read Replica
- Cost: $500-1000/mo + PgBouncer

### Celery Worker Commands

```bash
# Development (single worker)
celery -A tformance worker -l info -c 4

# Production: Separate queues
celery -A tformance worker -Q sync -c 8 --pool=gevent      # IO-bound
celery -A tformance worker -Q llm -c 4 --pool=gevent       # LLM (rate limited)
celery -A tformance worker -Q compute -c 4 --pool=prefork  # CPU-bound
```

### Worker Sizing by Team Count

| Teams | Sync Workers | LLM Workers | Compute Workers |
|-------|--------------|-------------|-----------------|
| 5-10  | 4 (-c 4)     | 2           | 2               |
| 20-50 | 8 (-c 8)     | 4           | 4               |
| 100+  | 16 (-c 16)   | 8           | 8               |

## Potential Future Optimizations

- [ ] Remove unused indexes (save 5MB, faster writes):
  - `pr_llm_tech_languages_gin_idx` (0 scans)
  - `pr_llm_tech_categories_gin_idx` (0 scans)
  - `unique_team_jira_issue` (0 scans)

- [ ] Add PgBouncer for connection pooling at Tier 2+

- [ ] Enable `pg_stat_statements` for slow query analysis

- [ ] Investigate `teams_team` sequential scans (2.4M scans)
