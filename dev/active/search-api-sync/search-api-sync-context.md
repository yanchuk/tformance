# Search API Sync - Context & Key Files

**Last Updated:** 2026-01-04

---

## Key Files to Modify

### Primary Files

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/integrations/services/github_graphql.py` | GraphQL client | Add `SEARCH_PRS_BY_DATE_QUERY`, `search_prs_by_date_range()` |
| `apps/integrations/services/github_graphql_sync.py` | Sync service | Add `sync_repository_history_by_search()`, update existing sync |
| `apps/integrations/onboarding_pipeline.py` | Pipeline orchestration | Update to use Search API sync |

### Related Files (Reference)

| File | Purpose |
|------|---------|
| `apps/integrations/_task_modules/github_sync.py` | Celery tasks (calls sync service) |
| `apps/integrations/_task_modules/__init__.py` | Task module exports |
| `apps/integrations/tasks.py` | Main task exports |
| `apps/integrations/services/onboarding_sync.py` | Onboarding sync wrapper |
| `apps/integrations/models.py` | `TrackedRepository` model with progress fields |

### Test Files to Create/Modify

| File | Purpose |
|------|---------|
| `apps/integrations/tests/services/test_github_graphql.py` | Unit tests for new query |
| `apps/integrations/tests/services/test_github_graphql_sync.py` | Unit tests for sync service |
| `apps/integrations/tests/test_onboarding_pipeline.py` | Integration tests |

---

## Architecture Context

### Refactored Structure (as of Jan 4, 2026)

```
apps/integrations/
├── _task_modules/           # Celery tasks (split from tasks.py)
│   ├── __init__.py          # Re-exports for Celery autodiscover
│   ├── github_sync.py       # Repository sync tasks
│   ├── metrics.py           # LLM analysis tasks
│   └── pr_data.py           # PR data fetch tasks
├── services/
│   ├── github_graphql.py    # GraphQL client ← ADD NEW QUERY HERE
│   ├── github_graphql_sync.py  # Sync service ← ADD NEW FUNCTION HERE
│   ├── onboarding_sync.py   # Onboarding wrapper
│   └── ...
├── tasks.py                 # Main exports (backward compat)
├── onboarding_pipeline.py   # Pipeline orchestration ← UPDATE HERE
└── ...
```

### Call Flow

```
OnboardingView → start_onboarding_pipeline_task
                           ↓
                 sync_historical_data_task
                           ↓
                 _sync_with_graphql_or_rest()
                           ↓
                 sync_repository_history_graphql()  ← MODIFY TO USE SEARCH API
                           ↓
                 GitHubGraphQLClient.fetch_prs_bulk()  ← REPLACE WITH search_prs_by_date_range()
```

---

## Key Decisions Made

### Decision 1: Use Search API Instead of pullRequests Connection

**Why:** GitHub's `pullRequests` connection has no date filtering. Search API supports `created:>=DATE` and `created:DATE1..DATE2` syntax.

**Source:** [GitHub Community Discussion](https://github.com/orgs/community/discussions/24611)

### Decision 2: Get Progress Total from Search Response

**Why:** Search API returns `issueCount` in every response - no separate count query needed.

**Before:**
```python
prs_total = client.get_pr_count_in_date_range(...)  # Separate API call
fetch_prs_bulk(...)  # Another API call
```

**After:**
```python
response = client.search_prs_by_date_range(...)
prs_total = response['issueCount']  # Same response!
prs = response['nodes']
```

### Decision 3: Keep Sequential Processing (For Now)

**Why:** User confirmed streaming batch processing is acceptable to defer. Sequential is simpler to implement and test.

**Future:** Document streaming approach in plan for later implementation if 1000+ PR repos become common.

### Decision 4: Add New Function, Don't Modify Existing

**Why:** Safer rollout - can switch back easily if issues arise.

**Pattern:**
```python
# Keep existing
async def sync_repository_history_graphql(...):
    # Uses fetch_prs_bulk (pullRequests connection)

# Add new
async def sync_repository_history_by_search(...):
    # Uses search_prs_by_date_range (Search API)
```

---

## Dependencies

### External
- GitHub GraphQL API (v4)
- GitHub Search API (via GraphQL)

### Internal
- `gql` library for GraphQL client
- `asgiref.sync` for async/sync bridging
- `async_to_sync()` pattern (CRITICAL - see CLAUDE.md Celery async warning)

---

## Model Fields for Progress Tracking

### TrackedRepository Model

```python
# apps/integrations/models.py (line ~150)
class TrackedRepository(BaseTeamModel):
    # Progress tracking fields
    prs_total = models.IntegerField(null=True, blank=True)
    prs_processed = models.IntegerField(default=0)
    sync_status = models.CharField(...)
    sync_progress_message = models.TextField(...)
```

### Progress Update Pattern

```python
# In sync service
tracked_repo.prs_total = search_result['issueCount']
tracked_repo.save(update_fields=['prs_total'])

# After each PR processed
tracked_repo.prs_processed = F('prs_processed') + 1
tracked_repo.save(update_fields=['prs_processed'])
```

---

## Search API Query Syntax

### Phase 1: Last 30 Days

```
repo:owner/repo is:pr created:>=2024-12-05 sort:created-desc
```

### Phase 2: Days 31-90

```
repo:owner/repo is:pr created:2024-10-05..2024-12-04 sort:created-desc
```

### Date Format

Use `YYYY-MM-DD` format (ISO 8601 date only, no time).

```python
from datetime import datetime, timedelta
from django.utils import timezone

cutoff_30d = (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d')
cutoff_90d = (timezone.now() - timedelta(days=90)).strftime('%Y-%m-%d')
cutoff_31d = (timezone.now() - timedelta(days=31)).strftime('%Y-%m-%d')
```

---

## Testing Strategy (TDD)

### Unit Tests

1. **Query string generation** - Verify date formats and escaping
2. **Response parsing** - Handle edge cases (empty results, missing fields)
3. **Progress calculation** - issueCount → prs_total mapping

### Integration Tests

1. **End-to-end sync** - Mock API, verify DB state
2. **Two-phase sync** - Phase 1 then Phase 2, verify no duplicates
3. **Error handling** - API errors, rate limits

### Manual Verification

1. Trigger sync on test repo
2. Watch progress bar in UI
3. Verify total matches final count

---

## Related Documentation

- [CLAUDE.md](/CLAUDE.md) - Project guidelines, especially Celery async warning
- [prd/ONBOARDING.md](/prd/ONBOARDING.md) - Onboarding flow requirements
- [dev/active/sync-progress-fix/](/dev/active/sync-progress-fix/) - Previous fix attempt docs
- [dev/active/sync-bug-handoff.md](/dev/active/sync-bug-handoff.md) - Related bug context

---

## Git Context

**Branch:** main (or create feature branch)

**Recent Related Commits:**
```
b21ecb8 refactor(integrations): split tasks.py into domain-focused modules
45508ea fix(prompts): add anti-bias rules for tech detection v8.2.0
b96be7a chore(sync): add debug logging for PR count progress tracking
3f106d8 fix(sync): only count actually processed PRs in progress tracking
38d65f9 fix(sync): resolve async DB operations and progress tracking bugs
```
