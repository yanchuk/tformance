# Phase 2.4: Repository Selection - Context Reference

> Last Updated: 2025-12-10

## Current Implementation Status

**Status:** NOT STARTED

**Depends on:**
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete
- Phase 2.3 Organization Discovery ✅ Complete

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
    webhook_id = models.BigIntegerField(null=True)  # For Phase 2.5
    last_sync_at = models.DateTimeField(null=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=["team", "github_repo_id"], name="unique_team_github_repo"),
        ]
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
```

### Existing Services

**GitHub OAuth Service (apps/integrations/services/github_oauth.py)**
```python
# Constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github.v3+json"

# Reusable pagination helper
def _make_paginated_github_api_request(endpoint: str, access_token: str) -> list[dict]:
    """Make paginated GitHub API request, following Link headers."""

def _parse_next_link(link_header: str | None) -> str | None:
    """Parse GitHub Link header to extract next page URL."""

# Member functions (reuse patterns)
def get_organization_members(access_token: str, org_slug: str) -> list[dict]
def get_user_details(access_token: str, username: str) -> dict
```

**Encryption Service (apps/integrations/services/encryption.py)**
```python
from apps.integrations.services.encryption import encrypt, decrypt

# Decrypt token before use
access_token = decrypt(credential.access_token)
```

### Existing Views

**integrations_home (apps/integrations/views.py:85-120)**
- Shows integration status
- GitHub card with connection status
- Member count badge
- **Add Repositories link here**

---

## GitHub API Reference

### List Organization Repositories
```http
GET /orgs/{org}/repos
Authorization: token {access_token}
Accept: application/vnd.github.v3+json

# Query Parameters
?type=all       # all, public, private, forks, sources, member
?sort=updated   # created, updated, pushed, full_name
?per_page=100   # max 100
?page=1

# Response (array)
[
  {
    "id": 1296269,
    "name": "Hello-World",
    "full_name": "octocat/Hello-World",
    "private": false,
    "description": "This your first repo!",
    "language": "Python",
    "default_branch": "main",
    "updated_at": "2023-01-01T00:00:00Z",
    "pushed_at": "2023-01-01T00:00:00Z",
    "archived": false,
    "disabled": false
  }
]

# Pagination headers
Link: <https://api.github.com/orgs/org/repos?page=2>; rel="next"
```

### Rate Limits
- Authenticated: 5000 requests/hour
- Typical org with 50 repos: ~1 request (single page)
- Large org with 200 repos: ~2 requests

---

## Test Factories

**TrackedRepository Factory (apps/integrations/factories.py)**
```python
from apps.integrations.factories import TrackedRepositoryFactory

# Create test repo
repo = TrackedRepositoryFactory(
    team=team,
    integration=integration,
    github_repo_id=123456,
    full_name="acme-corp/api-server",
    is_active=True,
)
```

**Note:** Factory may need to be created if it doesn't exist.

---

## URL Patterns

### Existing Patterns (apps/integrations/urls.py)
```python
team_urlpatterns = (
    [
        path("", views.integrations_home, name="integrations_home"),
        path("github/connect/", views.github_connect, name="github_connect"),
        path("github/callback/", views.github_callback, name="github_callback"),
        path("github/disconnect/", views.github_disconnect, name="github_disconnect"),
        path("github/select-org/", views.github_select_org, name="github_select_org"),
        path("github/members/", views.github_members, name="github_members"),
        path("github/members/sync/", views.github_members_sync, name="github_members_sync"),
        path("github/members/<int:member_id>/toggle/", views.github_member_toggle, name="github_member_toggle"),
        # ADD THESE:
        # path("github/repos/", views.github_repos, name="github_repos"),
        # path("github/repos/<int:repo_id>/toggle/", views.github_repo_toggle, name="github_repo_toggle"),
        # path("github/repos/bulk/", views.github_repos_bulk, name="github_repos_bulk"),
    ],
    "integrations",
)
```

---

## Template Patterns

### Following Project Conventions
```html
{% extends "web/app/app_base.html" %}
{% load static %}
{% load i18n %}

{% block app %}
<section class="app-card">
  <!-- Use DaisyUI components -->
  <div class="card bg-base-100 shadow-md">
    <!-- Content -->
  </div>
</section>
{% endblock %}
```

### HTMX for Interactive Updates
```html
<!-- Toggle repo tracking -->
<form hx-post="{% url 'integrations:github_repo_toggle' team_slug=request.team.slug repo_id=repo.github_repo_id %}"
      hx-target="#repo-{{ repo.github_repo_id }}"
      hx-swap="outerHTML">
  {% csrf_token %}
  <button type="submit" class="btn btn-sm">
    {% if repo.is_tracked %}Untrack{% else %}Track{% endif %}
  </button>
</form>
```

---

## View Decorator Patterns

```python
from apps.teams.decorators import login_and_team_required, team_admin_required

# Read-only views
@login_and_team_required
def github_repos(request, team_slug):
    """List available repos - any team member can view."""
    pass

# Admin actions
@team_admin_required
def github_repo_toggle(request, team_slug, repo_id):
    """Toggle repo tracking - admin only."""
    pass
```

---

## Error Handling Patterns

### GitHub API Errors
```python
from apps.integrations.services.github_oauth import GitHubOAuthError

try:
    repos = get_organization_repositories(access_token, org_slug)
except GitHubOAuthError as e:
    messages.error(request, f"Failed to fetch repositories: {str(e)}")
    return redirect("integrations:integrations_home", team_slug=team.slug)
```

---

## Verification Commands

```bash
# Run all tests
make test ARGS='--keepdb'

# Run integrations tests only
make test ARGS='apps.integrations --keepdb'

# Check for missing migrations
make migrations

# Start dev server
make dev
# Visit http://localhost:8000/a/{team}/integrations/github/repos/
```

---

## Session Handoff Notes

**Starting state:** Phase 2.3 complete, members syncing

**To start Phase 2.4:**
1. Add `get_organization_repositories()` to github_oauth.py
2. Create `github_repos` view and template
3. Create `github_repo_toggle` view
4. Add URL patterns
5. Update integrations home with repos link

**Key decisions to make:**
1. Should repos auto-sync list periodically? (recommend: manual refresh for now)
2. Show archived repos? (recommend: filter out by default)
3. Bulk selection pattern? (recommend: checkboxes with form submission)
