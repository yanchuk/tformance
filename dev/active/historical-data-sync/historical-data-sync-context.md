# Phase 2.5: Historical Data Sync - Context Reference

> Last Updated: 2025-12-11

## Current Implementation Status

**Status:** NOT STARTED

**Depends on:**
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete
- Phase 2.3 Organization Discovery ✅ Complete
- Phase 2.4 Repository Selection ✅ Complete
- Phase 2.5 Webhook Setup ✅ Complete

---

## Key Files Reference

### Existing Models

**TrackedRepository (apps/integrations/models.py:140-196)**
```python
class TrackedRepository(BaseTeamModel):
    integration = models.ForeignKey(GitHubIntegration, on_delete=models.CASCADE)
    github_repo_id = models.BigIntegerField()
    full_name = models.CharField(max_length=255)  # owner/repo
    is_active = models.BooleanField(default=True)
    webhook_id = models.BigIntegerField(null=True)
    last_sync_at = models.DateTimeField(null=True)  # ← Update after sync
```

**GitHubIntegration (apps/integrations/models.py:72-138)**
```python
class GitHubIntegration(BaseTeamModel):
    credential = models.OneToOneField(IntegrationCredential, on_delete=models.CASCADE)
    organization_slug = models.CharField(max_length=100)
    organization_id = models.BigIntegerField()
    webhook_secret = models.CharField(max_length=100)
    last_sync_at = models.DateTimeField(null=True)
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES)
    # SYNC_STATUS_CHOICES: pending, syncing, complete, error
```

**PullRequest (apps/metrics/models.py:97-231)**
```python
class PullRequest(BaseTeamModel):
    github_pr_id = models.BigIntegerField()
    github_repo = models.CharField(max_length=255)
    title = models.TextField(blank=True)
    author = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES)  # open, merged, closed
    pr_created_at = models.DateTimeField(null=True)
    merged_at = models.DateTimeField(null=True)
    first_review_at = models.DateTimeField(null=True)
    cycle_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    review_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    is_revert = models.BooleanField(default=False)
    is_hotfix = models.BooleanField(default=False)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_pr_id", "github_repo"],
                name="unique_team_pr",
            )
        ]
```

**PRReview (apps/metrics/models.py:233-303)**
```python
class PRReview(BaseTeamModel):
    github_review_id = models.BigIntegerField(null=True, blank=True)
    pull_request = models.ForeignKey(PullRequest, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES)  # approved, changes_requested, commented
    submitted_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_review_id"],
                condition=models.Q(github_review_id__isnull=False),
                name="unique_team_review",
            )
        ]
```

**Commit (apps/metrics/models.py:305-386)**
```python
class Commit(BaseTeamModel):
    github_sha = models.CharField(max_length=40)
    github_repo = models.CharField(max_length=255)
    author = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True)
    message = models.TextField(blank=True)
    committed_at = models.DateTimeField(null=True)
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    pull_request = models.ForeignKey(PullRequest, on_delete=models.SET_NULL, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["team", "github_sha"],
                name="unique_team_commit",
            )
        ]
```

### Existing Services

**GitHub OAuth Service (apps/integrations/services/github_oauth.py)**
```python
# Reusable for sync
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github.v3+json"

def _make_github_api_request(endpoint: str, access_token: str) -> dict | list:
    """Make GET request to GitHub API."""

def _make_paginated_github_api_request(endpoint: str, access_token: str) -> list:
    """Make paginated GET request, follows Link headers."""

def _parse_next_link(link_header: str) -> str | None:
    """Parse Link header for next page URL."""
```

**PR Processor (apps/metrics/processors.py)**
```python
def _parse_github_timestamp(timestamp_str: str | None) -> datetime | None:
    """Parse GitHub ISO8601 timestamp string."""

def _determine_pr_state(github_state: str, is_merged: bool) -> str:
    """Determine PR state from GitHub state and merged flag."""

def _calculate_cycle_time_hours(pr_created_at, merged_at) -> Decimal | None:
    """Calculate cycle time in hours."""

def _calculate_time_diff_hours(start_time, end_time) -> Decimal | None:
    """Calculate time difference in hours."""

def _get_team_member_by_github_id(team, github_user_id: str) -> TeamMember | None:
    """Look up TeamMember by GitHub user ID."""

def handle_pull_request_event(team, payload: dict) -> PullRequest | None:
    """Process PR webhook payload - can be adapted for sync."""

def handle_pull_request_review_event(team, payload: dict) -> PRReview | None:
    """Process review webhook payload - can be adapted for sync."""
```

**Encryption Service (apps/integrations/services/encryption.py)**
```python
from apps.integrations.services.encryption import decrypt
access_token = decrypt(credential.access_token)
```

### Existing Views

**github_repo_toggle (apps/integrations/views.py)**
- Creates/deletes TrackedRepository
- Already registers/deletes webhooks
- Will add sync trigger here

---

## GitHub API Reference

### List Repository Pull Requests

```http
GET /repos/{owner}/{repo}/pulls
Authorization: token {access_token}
Accept: application/vnd.github.v3+json

Query Parameters:
- state: "all" | "open" | "closed" (default: "open")
- sort: "created" | "updated" | "popularity" | "long-running" (default: "created")
- direction: "asc" | "desc" (default: "desc")
- per_page: 1-100 (default: 30)
- page: page number

Response Headers:
- Link: <url>; rel="next", <url>; rel="last"
- X-RateLimit-Remaining: number
- X-RateLimit-Reset: timestamp
```

**Response:**
```json
[
  {
    "id": 123456789,
    "number": 42,
    "state": "closed",
    "title": "Add new feature",
    "user": {
      "login": "developer",
      "id": 12345
    },
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-02T16:00:00Z",
    "closed_at": "2025-01-02T15:00:00Z",
    "merged_at": "2025-01-02T15:00:00Z",
    "additions": 150,
    "deletions": 50,
    "base": {
      "repo": {
        "id": 98765432,
        "full_name": "acme-corp/api-server"
      }
    }
  }
]
```

### Get Pull Request Reviews

```http
GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews
Authorization: token {access_token}
Accept: application/vnd.github.v3+json
```

**Response:**
```json
[
  {
    "id": 456789,
    "user": {
      "login": "reviewer",
      "id": 54321
    },
    "state": "APPROVED",
    "submitted_at": "2025-01-01T12:00:00Z",
    "body": "LGTM!"
  }
]
```

**Review States:**
- `APPROVED`
- `CHANGES_REQUESTED`
- `COMMENTED`
- `PENDING` (draft review, not submitted)
- `DISMISSED`

### Get Pull Request Commits

```http
GET /repos/{owner}/{repo}/pulls/{pull_number}/commits
Authorization: token {access_token}
Accept: application/vnd.github.v3+json
```

**Response:**
```json
[
  {
    "sha": "abc123def456...",
    "commit": {
      "message": "Add feature X",
      "author": {
        "name": "Developer",
        "email": "dev@example.com",
        "date": "2025-01-01T09:00:00Z"
      }
    },
    "author": {
      "login": "developer",
      "id": 12345
    }
  }
]
```

---

## Test Factories

**From apps/integrations/factories.py:**
```python
from apps.integrations.factories import (
    IntegrationCredentialFactory,
    GitHubIntegrationFactory,
    TrackedRepositoryFactory,
)

# Create tracked repo for testing
tracked_repo = TrackedRepositoryFactory(
    team=team,
    integration=integration,
    github_repo_id=123456,
    full_name="acme-corp/api-server",
)
```

**From apps/metrics/factories.py:**
```python
from apps.metrics.factories import (
    TeamMemberFactory,
    PullRequestFactory,
    PRReviewFactory,
    CommitFactory,
)

# Create test PR
pr = PullRequestFactory(
    team=team,
    github_pr_id=42,
    github_repo="acme-corp/api-server",
    author=member,
    state="merged",
)
```

---

## Celery Task Pattern

**Reference from apps/subscriptions/tasks.py:**
```python
from celery import shared_task

@shared_task
def sync_repository_history_task(tracked_repo_id: int):
    """Sync historical data for a tracked repository."""
    from apps.integrations.models import TrackedRepository
    from apps.integrations.services.github_sync import sync_repository_history

    try:
        tracked_repo = TrackedRepository.objects.get(id=tracked_repo_id)
        result = sync_repository_history(tracked_repo)
        return result
    except TrackedRepository.DoesNotExist:
        return {"error": "Repository not found"}
    except Exception as e:
        # Log error, update status
        return {"error": str(e)}
```

---

## URL Patterns

### New URL (in team_urlpatterns)
```python
# apps/integrations/urls.py
path(
    "github/repos/<int:repo_id>/sync/",
    views.github_repo_sync,
    name="github_repo_sync",
),
```

**Full URL:** `/a/{team_slug}/integrations/github/repos/{repo_id}/sync/`

---

## UI Updates

### Repo Card Enhancement (repo_card.html)

```html
<!-- Add sync button next to webhook status -->
{% if repo.is_tracked %}
  <div class="flex items-center gap-2">
    {% if repo.webhook_id %}
      <span class="badge badge-success badge-sm">Webhook active</span>
    {% else %}
      <span class="badge badge-warning badge-sm">Webhook pending</span>
    {% endif %}

    <!-- Sync status -->
    {% if repo.last_sync_at %}
      <span class="badge badge-info badge-sm" title="Last synced: {{ repo.last_sync_at }}">
        Synced
      </span>
    {% else %}
      <span class="badge badge-ghost badge-sm">Not synced</span>
    {% endif %}

    <!-- Manual sync button -->
    <button
      hx-post="{% url 'integrations:github_repo_sync' team.slug repo.github_repo_id %}"
      hx-swap="none"
      class="btn btn-xs btn-ghost"
      title="Sync historical data"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
      </svg>
    </button>
  </div>
{% endif %}
```

---

## Verification Commands

```bash
# Run all tests
make test ARGS='--keepdb'

# Run integrations tests only
make test ARGS='apps.integrations --keepdb'

# Run metrics tests only
make test ARGS='apps.metrics --keepdb'

# Check for missing migrations
make migrations

# Start Celery worker (for async tasks)
celery -A tformance worker -l info

# Start dev server
make dev
```

---

## Session Handoff Notes

**Starting state:** Webhooks working, repos can be tracked

**To start Phase 2.5 (Historical Sync):**
1. Create `github_sync.py` with API functions for fetching PRs/reviews
2. Create sync service function that processes data
3. Wire up to `github_repo_toggle` (trigger on track)
4. Add manual sync button to repo card
5. (Optional) Add Celery task for background processing

**Key decisions made:**
1. Sync should be synchronous for MVP (simpler), can add Celery later
2. Sync 90 days of history by default
3. Skip commit sync for MVP (can add in incremental sync phase)
4. Use existing processor helpers where possible

**API mapping notes:**
- PR list endpoint returns `id` (GitHub internal ID) which we use as `github_pr_id`
- PR list endpoint also returns `number` which is the human-readable PR number
- Review `state` from API is UPPERCASE, model stores lowercase
- Author lookup uses `user.id` from API response
