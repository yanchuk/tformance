# Phase 2.5: Historical Data Sync - Context Reference

> Last Updated: 2025-12-11

## Current Implementation Status

**Status:** ✅ COMPLETE - Committed as `c3a1d23`

**All 560 tests pass.**

---

## What Was Implemented

### 1. GitHub API Functions (`apps/integrations/services/github_sync.py`)

```python
def get_repository_pull_requests(access_token, repo_full_name, state="all", per_page=100) -> list[dict]
def get_pull_request_reviews(access_token, repo_full_name, pr_number) -> list[dict]
def sync_repository_history(tracked_repo, days_back=90) -> dict
```

**Key patterns:**
- Uses `_make_paginated_github_request()` helper to avoid duplication
- Imports shared utilities from `github_oauth.py` (constants, `_parse_next_link()`)
- `sync_repository_history()` extracts `_sync_pr_reviews()` helper for cleaner code

### 2. View Integration (`apps/integrations/views.py`)

**Auto-trigger sync on track:**
```python
# In github_repo_toggle(), after creating TrackedRepository:
try:
    github_sync.sync_repository_history(tracked_repo)
except Exception as e:
    logger.error(f"Failed to sync historical data for {full_name}: {e}")
```

**Manual sync endpoint:**
```python
@login_and_team_required
def github_repo_sync(request, team_slug, repo_id):
    # POST only, returns JSON with sync results
```

### 3. URL Pattern (`apps/integrations/urls.py`)

```python
path("github/repos/<int:repo_id>/sync/", views.github_repo_sync, name="github_repo_sync"),
```

### 4. UI Updates (`repo_card.html`)

- "Synced" badge (info) when `last_sync_at` is set
- "Not synced" badge (ghost) when `last_sync_at` is None
- Sync button with HTMX `hx-post` to trigger manual sync
- Added `tracked_repo_id` and `last_sync_at` to repo context

### 5. Shared Helper (`apps/metrics/processors.py`)

Extracted `_map_github_pr_to_fields()` to eliminate duplication between:
- `handle_pull_request_event()` (webhook handler)
- `sync_repository_history()` (batch sync)

---

## Key Decisions Made

1. **Sync is synchronous for MVP** - No Celery task yet (can add in Phase 2.6)
2. **days_back parameter defined but not implemented** - Always syncs all PRs for now
3. **Graceful degradation** - Sync failures don't block repo tracking
4. **Review sync included** - Creates PRReview records, calculates `review_time_hours`
5. **Shared helper for PR mapping** - `_map_github_pr_to_fields()` used by both webhook and sync

---

## Files Modified

| File | Changes |
|------|---------|
| `apps/integrations/services/github_sync.py` | NEW - Sync service (246 lines) |
| `apps/integrations/tests/test_github_sync.py` | NEW - 24 tests |
| `apps/integrations/views.py` | Added auto-sync in toggle, new `github_repo_sync` view |
| `apps/integrations/urls.py` | Added `github_repo_sync` URL |
| `apps/integrations/tests/test_views.py` | Added 14 tests for sync triggers |
| `apps/integrations/templates/.../repo_card.html` | Sync status badges + button |
| `apps/metrics/processors.py` | Extracted `_map_github_pr_to_fields()` helper |

---

## Test Coverage

- `apps/integrations/tests/test_github_sync.py` - 24 tests
- `apps/integrations/tests/test_views.py` - 14 new tests for sync

All 560 tests pass.

---

## No Migrations Needed

No model changes were made in this phase. The existing `TrackedRepository.last_sync_at` field is now populated by sync.

---

## What's Next

### Phase 2.6: Incremental Sync (Optional)
- Daily Celery task to sync only updated PRs
- Use `since` parameter in API calls
- Track `last_sync_at` per repo for delta syncs

### Phase 3: Jira Integration
- OAuth flow for Atlassian
- Project selection
- Issue sync with user matching

---

## Verification Commands

```bash
# Run all tests
make test ARGS='--keepdb'

# Run sync-specific tests
make test ARGS='apps.integrations.tests.test_github_sync --keepdb'

# Check for lint issues
make ruff

# Start dev server
make dev
```

---

## Session Handoff Notes

**Completed this session:**
- Full implementation of Phase 2.5: Historical Data Sync
- 6 TDD cycles (RED-GREEN-REFACTOR each)
- 38 new tests written
- All code committed

**No unfinished work** - Phase 2.5 is complete and committed.

**Next conversation can:**
1. Start Phase 2.6 (Incremental Sync with Celery)
2. Start Phase 3 (Jira Integration)
3. Test the app manually with real GitHub repos
