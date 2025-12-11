# Phase 2.5: Historical Data Sync - Implementation Plan

> Last Updated: 2025-12-11

## Executive Summary

This phase implements historical data synchronization for tracked GitHub repositories. When a repository is tracked, we need to import existing PRs (not just future webhook events) so teams don't start with empty dashboards. This includes fetching PRs, reviews, and commits from the last N days.

### Key Outcomes
- Fetch historical PRs from tracked repositories (configurable lookback period)
- Fetch reviews for each historical PR
- Fetch commits for each historical PR (optional, for detailed metrics)
- Calculate cycle time, review time for historical data
- Update `last_sync_at` on TrackedRepository after sync
- Provide sync status visibility in UI

### Dependencies
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete
- Phase 2.3 Organization Discovery ✅ Complete
- Phase 2.4 Repository Selection ✅ Complete
- Phase 2.5 Webhook Setup ✅ Complete (previous 2.5, now renumbered)

---

## Current State Analysis

### Existing Infrastructure

**GitHub API Service (apps/integrations/services/github_oauth.py)**
- `_make_github_api_request()` - GET requests to GitHub API
- `_make_paginated_github_api_request()` - Handles pagination with Link headers
- `get_organization_repositories()` - Fetches org repos with pagination

**PR Processor (apps/metrics/processors.py)**
- `handle_pull_request_event()` - Creates/updates PullRequest from webhook payload
- `handle_pull_request_review_event()` - Creates PRReview from webhook payload
- Helper functions for timestamp parsing, state determination, cycle time calculation

**Models Ready**
- `PullRequest` - Has all required fields, unique constraint on (team, github_pr_id, github_repo)
- `PRReview` - Has github_review_id for idempotency
- `Commit` - Ready for commit sync (optional)
- `TrackedRepository` - Has `last_sync_at` for tracking sync status

### Missing Components
- GitHub API functions to fetch PRs, reviews, commits
- Historical sync service that orchestrates the sync
- Celery task for async/background sync
- Trigger mechanism (on track + manual re-sync button)
- Progress/status visibility in UI

---

## Technical Architecture

### Sync Flow

```
User tracks repository
    │
    ▼
TrackedRepository created (webhook registered)
    │
    ▼
Trigger historical sync (sync or async)
    │
    ▼
Fetch PRs from GitHub API (paginated, filtered by date)
    │
    ▼
For each PR:
    ├─ Create/update PullRequest record
    ├─ Fetch reviews → Create PRReview records
    └─ (Optional) Fetch commits → Create Commit records
    │
    ▼
Update TrackedRepository.last_sync_at
    │
    ▼
Update GitHubIntegration.sync_status
```

### GitHub API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/repos/{owner}/{repo}/pulls` | GET | List PRs (paginated) |
| `/repos/{owner}/{repo}/pulls/{pull_number}` | GET | Get single PR details |
| `/repos/{owner}/{repo}/pulls/{pull_number}/reviews` | GET | Get PR reviews |
| `/repos/{owner}/{repo}/pulls/{pull_number}/commits` | GET | Get PR commits |

### API Parameters

**List PRs:**
```
GET /repos/{owner}/{repo}/pulls
?state=all           # Get open, closed, and merged
&sort=updated        # Sort by last updated
&direction=desc      # Most recent first
&per_page=100        # Max per page
```

### Rate Limiting Considerations

- GitHub API: 5,000 requests/hour for authenticated requests
- Each repo sync uses: 1 (PR list) + N (PR details) + N (reviews) requests
- For 100 PRs with reviews: ~200 API calls
- Mitigation: Use conditional requests (If-Modified-Since), batch processing

---

## Implementation Phases

### 2.5.1: GitHub API Functions for Historical Data [Effort: M]

Create API functions to fetch PRs, reviews, and commits.

**Deliverables:**
- `get_repository_pull_requests(access_token, repo_full_name, state, since)` - Paginated PR list
- `get_pull_request_details(access_token, repo_full_name, pr_number)` - Single PR with full details
- `get_pull_request_reviews(access_token, repo_full_name, pr_number)` - PR reviews
- `get_pull_request_commits(access_token, repo_full_name, pr_number)` - PR commits (optional)
- Handle pagination via Link headers
- Handle rate limiting gracefully

### 2.5.2: Historical Sync Service [Effort: M]

Create service to orchestrate historical data sync.

**Deliverables:**
- `sync_repository_history(tracked_repo, days_back=90)` - Main sync function
- Process PRs and create/update PullRequest records
- Process reviews and create PRReview records
- Update `first_review_at` and `review_time_hours` on PRs
- Update `TrackedRepository.last_sync_at` after sync
- Handle partial failures gracefully (continue on individual PR errors)

### 2.5.3: Celery Task for Background Sync [Effort: S]

Create async task for non-blocking sync.

**Deliverables:**
- `sync_repository_history_task(tracked_repo_id)` - Celery task wrapper
- `sync_all_pending_repositories_task()` - Batch task for pending repos
- Update `GitHubIntegration.sync_status` during sync
- Error handling and retry logic

### 2.5.4: Sync Trigger Integration [Effort: S]

Wire up sync triggers.

**Deliverables:**
- Auto-trigger sync when repository is tracked (in `github_repo_toggle`)
- Add "Sync Now" button to repo card for manual re-sync
- Create `github_repo_sync` view for manual trigger
- Show sync status on repo card (syncing/synced/error)

### 2.5.5: Commit Sync (Optional) [Effort: M]

Sync commits for each PR (can be deferred to later phase).

**Deliverables:**
- Fetch commits per PR
- Create Commit records
- Link commits to PullRequest
- Calculate additions/deletions if not in PR data

---

## API Endpoints

### New Internal Service Functions

```python
# apps/integrations/services/github_sync.py

def get_repository_pull_requests(
    access_token: str,
    repo_full_name: str,
    state: str = "all",
    since: datetime | None = None,
    per_page: int = 100,
) -> list[dict]:
    """Fetch pull requests from a repository with pagination."""

def get_pull_request_reviews(
    access_token: str,
    repo_full_name: str,
    pr_number: int,
) -> list[dict]:
    """Fetch reviews for a specific pull request."""

def sync_repository_history(
    tracked_repo: TrackedRepository,
    days_back: int = 90,
) -> dict:
    """Sync historical PR data for a tracked repository.

    Returns:
        {"prs_synced": int, "reviews_synced": int, "errors": list}
    """
```

### New Views

| Method | URL | View | Purpose |
|--------|-----|------|---------|
| POST | `/a/{team}/integrations/github/repos/{repo_id}/sync/` | `github_repo_sync` | Manual sync trigger |

---

## Data Flow

### PR List API Response → PullRequest Model

```python
# GitHub API response (GET /repos/{owner}/{repo}/pulls)
{
    "id": 123456789,           # → github_pr_id (note: this is the PR ID, not number)
    "number": 42,              # PR number for display/API calls
    "title": "Add new feature",
    "state": "closed",
    "merged_at": "2025-01-02T15:00:00Z",
    "user": {"id": 12345, "login": "developer"},
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-02T16:00:00Z",
    "additions": 150,
    "deletions": 50,
    "base": {"repo": {"full_name": "acme-corp/api-server"}}
}

# Maps to PullRequest model
{
    "team": <team>,
    "github_pr_id": 123456789,
    "github_repo": "acme-corp/api-server",
    "title": "Add new feature",
    "author": <TeamMember lookup by github_id=12345>,
    "state": "merged",  # derived from state + merged_at
    "pr_created_at": "2025-01-01T10:00:00Z",
    "merged_at": "2025-01-02T15:00:00Z",
    "cycle_time_hours": 29.0,
    "additions": 150,
    "deletions": 50,
}
```

### Review API Response → PRReview Model

```python
# GitHub API response (GET /repos/{owner}/{repo}/pulls/{number}/reviews)
{
    "id": 456789,
    "user": {"id": 54321, "login": "reviewer"},
    "state": "APPROVED",  # APPROVED, CHANGES_REQUESTED, COMMENTED
    "submitted_at": "2025-01-01T12:00:00Z"
}

# Maps to PRReview model
{
    "team": <team>,
    "github_review_id": 456789,
    "pull_request": <PullRequest>,
    "reviewer": <TeamMember lookup>,
    "state": "approved",  # lowercased
    "submitted_at": "2025-01-01T12:00:00Z"
}
```

---

## Configuration

### Settings

```python
# settings.py or environment variables

# Number of days to look back for historical sync
GITHUB_SYNC_DAYS_BACK = 90

# Maximum PRs to sync per repository (safety limit)
GITHUB_SYNC_MAX_PRS = 1000

# Whether to sync commits (can be expensive)
GITHUB_SYNC_COMMITS = False
```

---

## Error Handling

### Sync Failures

```python
def sync_repository_history(tracked_repo, days_back=90):
    errors = []
    prs_synced = 0

    try:
        prs = get_repository_pull_requests(...)
    except GitHubOAuthError as e:
        # Total failure - can't fetch PRs
        tracked_repo.integration.sync_status = "error"
        tracked_repo.integration.save()
        raise

    for pr_data in prs:
        try:
            process_pr(pr_data)
            prs_synced += 1
        except Exception as e:
            # Individual PR failure - log and continue
            errors.append({"pr": pr_data.get("number"), "error": str(e)})
            continue

    # Update sync timestamp even with partial errors
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()

    return {"prs_synced": prs_synced, "errors": errors}
```

### Rate Limiting

```python
def handle_rate_limit(response):
    """Check for rate limiting and wait if necessary."""
    remaining = int(response.headers.get("X-RateLimit-Remaining", 1))
    if remaining == 0:
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        wait_seconds = max(reset_time - time.time(), 0) + 1
        time.sleep(wait_seconds)
```

---

## Testing Strategy

### Unit Tests
- API function pagination handling
- PR data mapping to model fields
- Review data mapping
- Cycle time calculation for historical PRs
- Error handling for individual PR failures

### Integration Tests
- Full sync flow with mocked GitHub API
- Celery task execution
- Idempotency (running sync twice produces same result)
- Partial failure handling

### Manual Testing Checklist
1. Track a repository with existing PRs
2. Verify historical PRs appear in database
3. Verify reviews are linked to PRs
4. Verify cycle_time_hours calculated correctly
5. Click "Sync Now" - verify it re-syncs
6. Verify last_sync_at updated

---

## File Structure

```
apps/integrations/
├── services/
│   ├── github_oauth.py        # Existing OAuth functions
│   ├── github_webhooks.py     # Existing webhook functions
│   └── github_sync.py         # ❌ CREATE - Historical sync functions
├── views.py                   # ⬆️ EXTEND - Add github_repo_sync view
├── urls.py                    # ⬆️ EXTEND - Add sync URL
└── tests/
    └── test_github_sync.py    # ❌ CREATE

apps/integrations/
└── tasks.py                   # ❌ CREATE - Celery tasks

apps/integrations/templates/integrations/components/
└── repo_card.html             # ⬆️ EXTEND - Add sync button, status
```

---

## Risk Assessment

### High Risk
1. **Rate Limiting**
   - Large repos could hit GitHub API limits
   - Mitigation: Implement rate limit handling, batch processing

2. **Sync Duration**
   - Large repos with many PRs could take minutes
   - Mitigation: Async processing via Celery, progress indicators

### Medium Risk
1. **Partial Data**
   - Some PRs might fail to sync
   - Mitigation: Continue on errors, log failures, allow re-sync

2. **Duplicate Data**
   - Running sync multiple times
   - Mitigation: Use `update_or_create` with unique constraints

### Low Risk
1. **Stale Data**
   - Historical data doesn't update
   - Mitigation: Webhooks handle real-time updates going forward

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| PRs synced per repo | 90 days worth | Count after sync |
| Sync success rate | >95% | Successful syncs / attempts |
| Average sync time | <30s for 100 PRs | Time from start to completion |
| Data accuracy | 100% | Compare with GitHub UI |

---

## MVP vs Full Implementation

### MVP (This Phase)
- Sync PRs and reviews
- Basic error handling
- Manual sync trigger
- Sync on track

### Future Enhancements (Phase 2.6)
- Commit sync
- Incremental sync (only fetch new/updated)
- Scheduled daily sync
- Webhook fallback (if webhook missed events)
- Sync progress indicator (percentage complete)
