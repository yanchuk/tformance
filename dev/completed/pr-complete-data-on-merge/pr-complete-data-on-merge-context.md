# PR Complete Data Fetch on Merge - Context

**Last Updated:** 2025-12-22

## Key Files

### Files to Modify

| File | Changes |
|------|---------|
| `apps/integrations/tasks.py` | Add `fetch_pr_complete_data_task` |
| `apps/metrics/processors.py` | Wire up task in `_trigger_pr_surveys_if_merged()` |

### Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/tests/test_fetch_pr_complete_data.py` | Unit tests for new task |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `apps/integrations/services/github_sync.py` | Contains sync functions to reuse |
| `apps/metrics/models/github.py` | PullRequest and related models |
| `apps/integrations/models.py` | TrackedRepository model |
| `apps/web/views.py` | Webhook endpoint (lines 108-196) |

## Key Functions to Reuse

### From `github_sync.py`

```python
# Sync commits for a PR
sync_pr_commits(pr, pr_number, access_token, repo_full_name, team, errors) -> int

# Sync files changed in a PR
sync_pr_files(pr, pr_number, access_token, repo_full_name, team, errors) -> int

# Sync CI/CD check runs
sync_pr_check_runs(pr, pr_number, access_token, repo_full_name, team, errors) -> int

# Sync issue comments (general PR comments)
sync_pr_issue_comments(pr, pr_number, access_token, repo_full_name, team, errors) -> int

# Sync review comments (inline code comments)
sync_pr_review_comments(pr, pr_number, access_token, repo_full_name, team, errors) -> int

# Calculate iteration metrics from synced data
calculate_pr_iteration_metrics(pr) -> None
```

### Current Task Pattern (from `tasks.py`)

```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_repository_task(self, repo_id: int) -> dict:
    # 1. Look up model by ID
    # 2. Get access token (auto-decrypted from EncryptedTextField)
    # 3. Call sync functions
    # 4. Handle errors with retry
    # 5. Return result dict
```

## Data Models

### PullRequest (apps/metrics/models/github.py:10)

Key fields updated by iteration metrics:
- `review_rounds` - Number of review cycles
- `avg_fix_response_hours` - Average time from changes_requested to next commit
- `commits_after_first_review` - Commits made after first review
- `total_comments` - Total comment count

### TrackedRepository (apps/integrations/models.py)

Key fields:
- `full_name` - "owner/repo" format
- `github_pr_id` - PR number (NOT the same as PR id!)
- `integration` - FK to GitHubIntegration (has `credential.access_token`)

## Lookup Pattern

To get TrackedRepository from PullRequest:

```python
from apps.integrations.models import TrackedRepository

pr = PullRequest.objects.get(id=pr_id)

tracked_repo = TrackedRepository.objects.filter(
    team=pr.team,
    full_name=pr.github_repo,
    is_active=True
).first()

if not tracked_repo:
    # Handle missing repo
    return {"error": "TrackedRepository not found"}

# Get decrypted access token
access_token = tracked_repo.integration.credential.access_token
```

## Webhook Payload Reference

When PR is merged, webhook payload contains:

```json
{
    "action": "closed",
    "pull_request": {
        "id": 123456789,
        "number": 42,
        "merged": true,
        "merged_at": "2025-01-02T15:00:00Z",
        ...
    },
    "repository": {
        "id": 98765,
        "full_name": "owner/repo"
    }
}
```

Note: `pr.github_pr_id` stores the `id` field (123456789), but API calls need the `number` (42).

**IMPORTANT:** The PullRequest model stores `github_pr_id` which is the PR's unique ID, but we need the PR number for API calls. Currently, this is NOT stored on the model!

### Current Workaround

The existing sync functions handle this by fetching PRs from API which gives us both. For the new task, we can:

1. **Option A:** Fetch PR from GitHub API using github_pr_id to get the number
2. **Option B:** Add `github_pr_number` field to PullRequest model

The webhook payload includes both `id` and `number`, so Option B is cleaner but requires migration.

For MVP, use Option A (fetch from API).

## Error Handling Pattern

```python
try:
    result = sync_function(...)
except Exception as exc:
    countdown = self.default_retry_delay * (2 ** self.request.retries)
    try:
        raise self.retry(exc=exc, countdown=countdown)
    except Retry:
        raise  # Allow Celery to retry
    except Exception:
        # Max retries exhausted
        from sentry_sdk import capture_exception
        capture_exception(exc)
        return {"error": str(exc)}
```

## Test Patterns

### Mocking Celery Task Dispatch

```python
from unittest.mock import patch

with patch("apps.integrations.tasks.fetch_pr_complete_data_task") as mock_task:
    result = handle_pull_request_event(team, payload)
    mock_task.delay.assert_called_once_with(result.id)
```

### Factory Usage

```python
from apps.metrics.factories import PullRequestFactory, TeamFactory
from apps.integrations.factories import TrackedRepositoryFactory, GitHubIntegrationFactory

team = TeamFactory()
integration = GitHubIntegrationFactory(team=team)
tracked_repo = TrackedRepositoryFactory(
    integration=integration,
    full_name="owner/repo"
)
pr = PullRequestFactory(
    team=team,
    github_repo="owner/repo",
    github_pr_id=123456789
)
```

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Trigger timing | On merge only | Complete data most valuable after PR is done; no point syncing during active development |
| Retry strategy | 3 retries, exponential backoff | Match existing pattern in tasks.py |
| Error independence | Each sync wrapped separately | Partial data better than none |
| PR number lookup | Fetch from API (MVP) | Avoid migration; can optimize later |

## Open Questions

1. **Should we add `github_pr_number` to PullRequest model?**
   - Pro: Avoids extra API call
   - Con: Requires migration
   - Decision: Defer to later optimization; use API lookup for MVP

2. **Should task run on separate Celery queue?**
   - Pro: Doesn't compete with time-sensitive tasks (surveys)
   - Con: Extra complexity
   - Decision: Use default queue; monitor and adjust if needed

3. **Should we re-fetch reviews too?**
   - Pro: Ensures reviews are complete
   - Con: Reviews already synced via webhook
   - Decision: Skip reviews (already have them); only fetch missing data
