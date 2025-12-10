# Phase 2.5: Webhook Setup - Context Reference

> Last Updated: 2025-12-10

## Current Implementation Status

**Status:** NOT STARTED

**Depends on:**
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete
- Phase 2.3 Organization Discovery ✅ Complete
- Phase 2.4 Repository Selection ✅ Complete

---

## Key Files Reference

### Existing Models

**TrackedRepository (apps/integrations/models.py:140-196)**
```python
class TrackedRepository(BaseTeamModel):
    """Repositories being tracked for metrics collection."""
    integration = models.ForeignKey(GitHubIntegration, on_delete=models.CASCADE)
    github_repo_id = models.BigIntegerField()
    full_name = models.CharField(max_length=255)  # owner/repo
    is_active = models.BooleanField(default=True)
    webhook_id = models.BigIntegerField(null=True)  # ← For storing GitHub webhook ID
    last_sync_at = models.DateTimeField(null=True)
```

**GitHubIntegration (apps/integrations/models.py:72-138)**
```python
class GitHubIntegration(BaseTeamModel):
    credential = models.OneToOneField(IntegrationCredential, on_delete=models.CASCADE)
    organization_slug = models.CharField(max_length=100)
    organization_id = models.BigIntegerField()
    webhook_secret = models.CharField(max_length=100)  # ← For webhook signature validation
    last_sync_at = models.DateTimeField(null=True)
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES)
```

**PullRequest (apps/metrics/models.py:97-231)**
```python
class PullRequest(BaseTeamModel):
    github_pr_id = models.BigIntegerField()
    github_repo = models.CharField(max_length=255)
    title = models.TextField(blank=True)
    author = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES)
    pr_created_at = models.DateTimeField(null=True)
    merged_at = models.DateTimeField(null=True)
    first_review_at = models.DateTimeField(null=True)
    cycle_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    review_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    additions = models.IntegerField(default=0)
    deletions = models.IntegerField(default=0)
    is_revert = models.BooleanField(default=False)
    is_hotfix = models.BooleanField(default=False)
```

**PRReview (apps/metrics/models.py:233-288)**
```python
class PRReview(BaseTeamModel):
    pull_request = models.ForeignKey(PullRequest, on_delete=models.CASCADE)
    reviewer = models.ForeignKey(TeamMember, on_delete=models.SET_NULL, null=True)
    state = models.CharField(max_length=20, choices=STATE_CHOICES)  # approved, changes_requested, commented
    submitted_at = models.DateTimeField(null=True)
```

**TeamMember (apps/metrics/models.py:6-95)**
```python
class TeamMember(BaseTeamModel):
    email = models.EmailField(blank=True)
    display_name = models.CharField(max_length=255)
    github_username = models.CharField(max_length=100, blank=True)
    github_id = models.CharField(max_length=50, blank=True)  # ← For matching webhook user data
    is_active = models.BooleanField(default=True)
```

### Existing Services

**GitHub OAuth Service (apps/integrations/services/github_oauth.py)**
```python
# Constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github.v3+json"

# Reusable request helper
def _make_github_api_request(endpoint: str, access_token: str, method: str = "GET", data: dict = None) -> dict:
    """Make GitHub API request."""

# Encryption
from apps.integrations.services.encryption import decrypt
access_token = decrypt(credential.access_token)
```

### Existing Views

**github_repo_toggle (apps/integrations/views.py)**
- Currently creates/deletes TrackedRepository
- Will be updated to call webhook registration/deletion

---

## GitHub Webhook API Reference

### Create Repository Webhook
```http
POST /repos/{owner}/{repo}/hooks
Authorization: token {access_token}
Accept: application/vnd.github.v3+json
Content-Type: application/json

{
  "name": "web",
  "active": true,
  "events": ["pull_request", "pull_request_review"],
  "config": {
    "url": "https://app.tformance.com/webhooks/github/",
    "content_type": "json",
    "secret": "{webhook_secret}",
    "insecure_ssl": "0"
  }
}

# Response (201 Created)
{
  "id": 12345678,
  "name": "web",
  "active": true,
  "events": ["pull_request", "pull_request_review"],
  "config": {
    "url": "https://app.tformance.com/webhooks/github/",
    "content_type": "json"
  }
}
```

### Delete Repository Webhook
```http
DELETE /repos/{owner}/{repo}/hooks/{hook_id}
Authorization: token {access_token}
Accept: application/vnd.github.v3+json

# Response: 204 No Content
```

### Webhook Delivery Headers
```http
POST /webhooks/github/
X-GitHub-Event: pull_request
X-GitHub-Delivery: 72d3162e-cc78-11e3-81ab-4c9367dc0958
X-Hub-Signature-256: sha256=abc123...
Content-Type: application/json
```

---

## Webhook Event Payloads

### Pull Request Event
```json
{
  "action": "opened|closed|reopened|edited|synchronize",
  "number": 42,
  "pull_request": {
    "id": 123456789,
    "number": 42,
    "state": "open|closed",
    "merged": false,
    "title": "Add new feature",
    "user": {
      "login": "developer",
      "id": 12345
    },
    "created_at": "2025-01-01T10:00:00Z",
    "updated_at": "2025-01-02T14:00:00Z",
    "closed_at": null,
    "merged_at": null,
    "additions": 150,
    "deletions": 50,
    "base": {
      "repo": {
        "id": 98765432,
        "full_name": "acme-corp/api-server"
      }
    }
  },
  "repository": {
    "id": 98765432,
    "full_name": "acme-corp/api-server"
  }
}
```

### Pull Request Review Event
```json
{
  "action": "submitted|edited|dismissed",
  "review": {
    "id": 456789,
    "user": {
      "login": "reviewer",
      "id": 54321
    },
    "state": "approved|changes_requested|commented",
    "submitted_at": "2025-01-01T12:00:00Z"
  },
  "pull_request": {
    "id": 123456789,
    "number": 42
  },
  "repository": {
    "id": 98765432,
    "full_name": "acme-corp/api-server"
  }
}
```

---

## URL Patterns

### Webhook URL (apps/web/urls.py - NOT team-scoped)
```python
# This is NOT in team_urlpatterns because it's called by GitHub
urlpatterns = [
    # ... existing patterns
    path("webhooks/github/", views.github_webhook, name="github_webhook"),
]
```

**Important:** Webhook endpoint is NOT team-scoped. Team is determined from repository lookup.

---

## Signature Validation Pattern

```python
import hmac
import hashlib

def validate_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """Validate GitHub webhook signature.

    Args:
        payload: Raw request body as bytes
        signature_header: X-Hub-Signature-256 header value
        secret: Webhook secret from GitHubIntegration

    Returns:
        True if signature is valid
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected_signature = signature_header[7:]  # Remove "sha256=" prefix

    computed_signature = hmac.new(
        key=secret.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, computed_signature)
```

---

## TeamMember Lookup Pattern

```python
def get_team_member_by_github_id(team, github_id: int) -> TeamMember | None:
    """Find TeamMember by GitHub user ID.

    Returns None if no match found (author may not be in org).
    """
    try:
        return TeamMember.objects.get(team=team, github_id=str(github_id))
    except TeamMember.DoesNotExist:
        return None
```

---

## Test Factories

**PullRequestFactory (apps/metrics/factories.py)**
```python
from apps.metrics.factories import PullRequestFactory, PRReviewFactory

# Create test PR
pr = PullRequestFactory(
    team=team,
    github_pr_id=42,
    github_repo="acme-corp/api-server",
    author=member,
    state="open",
)

# Create test review
review = PRReviewFactory(
    team=team,
    pull_request=pr,
    reviewer=reviewer,
    state="approved",
)
```

---

## Environment Setup

### Local Testing with ngrok

```bash
# Install ngrok
brew install ngrok

# Start Django server
make dev

# In another terminal, start ngrok
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok.io)
# Use this as webhook URL during local development
```

### Production Webhook URL

```
https://app.tformance.com/webhooks/github/
```

---

## Error Handling Patterns

### Webhook Registration Failure
```python
try:
    webhook_id = create_repository_webhook(access_token, repo_full_name, webhook_url, secret)
    tracked_repo.webhook_id = webhook_id
    tracked_repo.save()
except GitHubOAuthError as e:
    # Log error but don't fail the toggle
    logger.error(f"Failed to register webhook for {repo_full_name}: {e}")
    # Repo is tracked but webhook not registered - can retry later
```

### Invalid Webhook Payload
```python
@csrf_exempt
def github_webhook(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    # Get signature header
    signature = request.headers.get("X-Hub-Signature-256")
    if not signature:
        return HttpResponse("Missing signature", status=401)

    # Validate signature against all possible secrets
    # (we don't know which team's repo yet)
    # ... validation logic ...

    return HttpResponse("OK", status=200)
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

# Start dev server
make dev
```

---

## Session Handoff Notes

**Starting state:** Phase 2.4 complete, repos can be tracked

**To start Phase 2.5:**
1. Create `github_webhooks.py` service with create/delete functions
2. Update `github_repo_toggle` to call webhook registration
3. Create `/webhooks/github/` endpoint
4. Implement signature validation
5. Create PR event handler
6. Create Review event handler

**Key decisions to make:**
1. Should webhook registration be sync or async? (recommend: sync for MVP, async later)
2. How to handle author not in TeamMember? (recommend: skip, log warning)
3. Should we process events inline or queue? (recommend: inline for MVP)

**Webhook URL for development:**
- Use ngrok for local testing
- Production URL: https://app.tformance.com/webhooks/github/
