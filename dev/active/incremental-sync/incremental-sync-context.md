# Phase 2.6: Incremental Sync - Context Reference

> Last Updated: 2025-12-11

## Implementation Status

**Status:** NOT STARTED

---

## Key Files

### Existing Files to Modify

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/integrations/services/github_sync.py` | Sync service | Add incremental sync function |
| `apps/integrations/models.py` | TrackedRepository model | Add `last_sync_error` field (optional) |
| `tformance/settings.py` | Django settings | Add scheduled task config |
| `pyproject.toml` | Dependencies | Add PyGithub |

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/tasks.py` | Celery tasks for sync |
| `apps/integrations/services/github_client.py` | PyGithub client helper |
| `apps/integrations/tests/test_tasks.py` | Tests for Celery tasks |
| `apps/integrations/tests/test_github_client.py` | Tests for client helper |

---

## Key Patterns to Follow

### Existing Sync Pattern (from github_sync.py)

```python
def sync_repository_history(tracked_repo, days_back=90):
    """Full sync - fetches ALL PRs."""
    access_token = decrypt(tracked_repo.integration.credential.access_token)
    prs_data = get_repository_pull_requests(access_token, tracked_repo.full_name)
    # Process each PR...
    tracked_repo.last_sync_at = timezone.now()
    tracked_repo.save()
```

### Existing Celery Task Pattern (from subscriptions/tasks.py)

```python
@shared_task
def sync_subscriptions_task():
    for team in Team.get_items_needing_sync():
        try:
            sync_subscription_model_with_stripe(team)
        except StripeError as e:
            from sentry_sdk import capture_exception
            capture_exception(e)
```

### Scheduled Task Config Pattern (from settings.py)

```python
SCHEDULED_TASKS = {
    "sync-subscriptions-every-day": {
        "task": "apps.subscriptions.tasks.sync_subscriptions_task",
        "schedule": timedelta(days=1),
        "expire_seconds": 60 * 60,
    },
}
```

---

## GitHub API Strategy

### Problem: PRs API lacks `since` parameter

The `/repos/{owner}/{repo}/pulls` endpoint only supports:
- `state`: open, closed, all
- `sort`: created, updated, popularity
- `direction`: asc, desc
- `base`, `head`: branch filters

**No date filtering available!**

### Solution: Use Issues API

The `/repos/{owner}/{repo}/issues` endpoint supports:
- `since`: datetime - Only issues updated at or after this time

Since PRs are also issues in GitHub's data model, we can:
1. Use `repo.get_issues(since=last_sync_at)`
2. Filter results where `issue.pull_request` is not None
3. Fetch full PR details for each

### PyGithub Implementation

```python
from github import Github
from datetime import datetime, timezone

def get_updated_pull_requests(github_client, repo_full_name, since):
    """Fetch PRs updated since a given datetime using Issues API."""
    repo = github_client.get_repo(repo_full_name)

    # Issues API has 'since' parameter, PRs API doesn't
    issues = repo.get_issues(state="all", since=since, sort="updated")

    prs = []
    for issue in issues:
        if issue.pull_request:  # This is a PR
            # Get full PR object (issue doesn't have all PR fields)
            pr = repo.get_pull(issue.number)
            prs.append(pr)

    return prs
```

---

## Data Models

### TrackedRepository (existing)

```python
class TrackedRepository(BaseTeamModel):
    integration = ForeignKey(GitHubIntegration)
    github_repo_id = BigIntegerField()
    full_name = CharField(max_length=255)
    is_active = BooleanField(default=True)
    webhook_id = BigIntegerField(null=True)
    last_sync_at = DateTimeField(null=True)  # Used for incremental sync
```

### Potential Addition

```python
# Consider adding for error tracking
last_sync_error = CharField(max_length=500, blank=True)
sync_status = CharField(choices=[...], default="idle")
```

---

## Dependencies

### PyGithub

- **Docs**: https://pygithub.readthedocs.io/
- **GitHub**: https://github.com/PyGithub/PyGithub
- **Version**: 2.1.0+

Key features we'll use:
- `Github(token)` - Authenticated client
- `repo.get_issues(since=datetime)` - Date-filtered issues
- `repo.get_pull(number)` - Full PR details
- Built-in pagination handling
- Rate limit awareness

### Installation

```bash
uv add PyGithub
```

---

## Celery Configuration

### Current Setup

- Worker: `celery -A tformance worker`
- Beat: `celery -A tformance beat`
- Backend: Redis
- Scheduler: `django-celery-beat` (database)

### Task Registration

Tasks are auto-discovered from `apps/*/tasks.py` via:
```python
# tformance/celery.py
app.autodiscover_tasks()
```

### Periodic Task Bootstrap

```bash
python manage.py bootstrap_celery_tasks
```

---

## Testing Strategy

### Unit Tests

1. **github_client.py**
   - Test client creation with valid token
   - Test client creation with expired token
   - Mock Github class

2. **Incremental sync functions**
   - Test date filtering logic
   - Test PR-from-issue conversion
   - Test pagination handling
   - Mock PyGithub responses

3. **Celery tasks**
   - Test single repo sync task
   - Test all repos dispatch
   - Test retry behavior
   - Test error handling

### Integration Tests

- Not required for MVP - Celery tasks can be tested with `task.apply()`

---

## Error Handling

### Rate Limiting

GitHub API: 5,000 requests/hour for authenticated users

```python
from github import RateLimitExceededException

try:
    # API call
except RateLimitExceededException:
    # Get reset time, schedule retry
    reset_time = github_client.get_rate_limit().core.reset
    raise self.retry(eta=reset_time)
```

### Auth Failures

```python
from github import BadCredentialsException

try:
    # API call
except BadCredentialsException:
    # Mark integration as disconnected
    tracked_repo.integration.credential.delete()
    logger.error(f"GitHub auth failed for {tracked_repo.full_name}")
```

---

## Verification Commands

```bash
# Run Celery worker (for manual testing)
celery -A tformance worker -l info

# Run Celery beat (for scheduled tasks)
celery -A tformance beat -l info

# Trigger task manually
python manage.py shell
>>> from apps.integrations.tasks import sync_all_repositories_task
>>> sync_all_repositories_task.delay()

# Check task status
>>> from celery.result import AsyncResult
>>> result = AsyncResult('task-id')
>>> result.status, result.result
```

---

## Notes

- **Timezone**: Always use UTC for `last_sync_at` and `since` parameter
- **First sync**: If `last_sync_at` is None, fall back to full sync
- **Webhook coexistence**: Incremental sync complements webhooks, doesn't replace them
- **Order of operations**: Webhooks handle real-time, daily sync catches anything missed
