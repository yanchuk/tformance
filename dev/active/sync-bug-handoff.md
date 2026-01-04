# Sync Bug Handoff: Files/Commits Not Saving

**Date:** 2026-01-04
**Status:** Blocked - needs fresh eyes

---

## User Story

**As a** CTO onboarding to Tformance,
**I want** my GitHub PR history to sync with files and commits,
**So that** I can see tech stack breakdown and AI-generated insights on my dashboard.

**Current Behavior:** PRs sync (14 records created), but `PRFile` and `Commit` tables remain empty.

**Expected Behavior:** Each PR should have associated files and commits from GitHub API.

---

## Architecture Overview

### Sync Pipeline Flow

```
Onboarding UI → Celery Task → OnboardingSyncService → sync_repository_history_graphql()
                                                              ↓
                                                    GitHubGraphQLClient.fetch_prs_bulk()
                                                              ↓
                                                    _process_pr_async() [@sync_to_async]
                                                              ↓
                                        ┌─────────────────────┼─────────────────────┐
                                        ↓                     ↓                     ↓
                              _process_reviews()    _process_commits()    _process_files()
                                        ↓                     ↓                     ↓
                              PRReview.objects     Commit.objects        PRFile.objects
                              .update_or_create()  .update_or_create()   .update_or_create()
```

### Key Files

| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | Celery tasks, calls sync service |
| `apps/integrations/services/onboarding_sync.py` | `OnboardingSyncService.sync_repository()` |
| `apps/integrations/services/github_graphql_sync.py` | Core sync logic, `_process_files()` |
| `apps/integrations/services/github_graphql.py` | GraphQL client, API calls |

### Async/Sync Bridge

The sync uses Django's async features:
- Main function is `async def sync_repository_history_graphql()`
- Called from sync Celery context via `async_to_sync()` wrapper
- DB operations wrapped with `@sync_to_async` decorator

```python
# In onboarding_sync.py (line 99)
sync_graphql = async_to_sync(sync_repository_history_graphql)
result = sync_graphql(repo, days_back=days_back, skip_recent=skip_recent)
```

---

## Problem Description

### Symptoms

1. PRs are created in `metrics_pullrequest` (14 records, correct data)
2. PR has `additions=5, deletions=0` (metadata saved correctly)
3. `metrics_prfile` table is empty (0 records)
4. `metrics_commit` table is empty (0 records)
5. No errors in logs - silent failure

### Verified Working

- GraphQL API returns files correctly (tested with direct API call)
- `_process_files()` works when called manually in Django shell
- OAuth token has correct scopes (`repo` provides file access)

### Suspected Root Cause

**`asyncio.run()` was breaking `@sync_to_async` in Celery workers.**

When `asyncio.run()` creates a new event loop, it breaks Django's `@sync_to_async(thread_sensitive=True)` thread context management. DB operations execute but don't commit properly.

### Fix Applied (Not Working Yet)

Changed all `asyncio.run()` to `async_to_sync()` in 5 locations:
- `apps/integrations/services/onboarding_sync.py:99`
- `apps/integrations/tasks.py:161, 213, 487, 1624`

**But files still aren't saving after re-sync.**

---

## What We've Tried

1. ✅ Verified GraphQL returns files (direct API test)
2. ✅ Verified `_process_files()` works manually
3. ✅ Changed `asyncio.run()` → `async_to_sync()` (5 locations)
4. ✅ Added `make celery-dev` with auto-reload (watchdog)
5. ✅ Killed old Celery worker, restarted with new code
6. ✅ Deleted team 154, re-onboarded as team 155
7. ❌ Files still not saving

---

## Reproduction Steps

```bash
# 1. Ensure Celery is running with latest code
make celery-dev

# 2. Trigger sync for team 155
.venv/bin/python manage.py shell -c "
from apps.integrations.models import TrackedRepository
from apps.integrations.tasks import sync_historical_data_task
repo = TrackedRepository.objects.get(team_id=155)
sync_historical_data_task.delay(155, [repo.id], days_back=30)
"

# 3. Check results
psql tformance -c "
SELECT COUNT(*) as prs,
       (SELECT COUNT(*) FROM metrics_prfile WHERE team_id=155) as files,
       (SELECT COUNT(*) FROM metrics_commit WHERE team_id=155) as commits
FROM metrics_pullrequest WHERE team_id=155;
"
```

**Expected:** `prs=14, files>0, commits>0`
**Actual:** `prs=14, files=0, commits=0`

---

## Questions for Review

1. Is `@sync_to_async` + `async_to_sync()` the correct pattern for Celery + async Django?
2. Could there be a transaction isolation issue?
3. Should `_process_files()` be async or stay sync?
4. Are we missing an `await` somewhere in the chain?
5. Could Celery's thread pool (`--pool=threads`) be interfering?

---

## Key Code Sections

### _process_files() - github_graphql_sync.py:565

```python
def _process_files(team, pr: PullRequest, file_nodes: list[dict], result: SyncResult) -> None:
    """Process PR files from GraphQL response."""
    for file_data in file_nodes:
        filename = file_data.get("path")
        if not filename:
            continue

        PRFile.objects.update_or_create(
            team=team,
            pull_request=pr,
            filename=filename,
            defaults={...}
        )
        result.files_synced += 1
```

### _process_pr_async() - github_graphql_sync.py:315

```python
@sync_to_async
def _process_pr_async(team_id, github_repo, pr_data, cutoff_date, skip_before_date, result):
    """Process a single PR (async wrapper for DB operations)."""
    # ... creates PR, then calls:
    _process_reviews(team, pr, reviews_nodes, result)
    _process_commits(team, pr, github_repo, commits_nodes, result)
    _process_files(team, pr, files_nodes, result)  # <-- This should save files
```

---

## Test Data

- **Team ID:** 155
- **Repo:** railsware/mailtrap-halon-scripts
- **PRs in last 30 days:** 14
- **Sample PR:** #2408 has 2 files (.go and .csv)

---

## Contact

Ask @yanchuk for access to:
- Local dev environment
- GitHub OAuth token for testing
- Database access
