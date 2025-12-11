# PyGithub Refactor - Context Reference

> Last Updated: 2025-12-11

## Implementation Status

**Status:** ✅ COMPLETE

All 552 tests pass. Lint passes.

---

## Key Files

### Files to Modify

| File | Line Count | Test File | Test Count |
|------|------------|-----------|------------|
| `apps/integrations/services/github_oauth.py` | 328 | `test_github_oauth.py` | 77 |
| `apps/integrations/services/github_webhooks.py` | 128 | `test_github_webhooks.py` | 18 |
| `apps/integrations/services/github_sync.py` | 247 | `test_github_sync.py` | 24 |

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/github_client.py` | PyGithub client factory |
| `apps/integrations/tests/test_github_client.py` | Tests for client factory |

---

## Current Function Signatures (Must Preserve)

### github_oauth.py

```python
def create_oauth_state(team_id: int) -> str:
    """Keep as-is - cryptographic signing."""

def verify_oauth_state(state: str) -> dict[str, Any]:
    """Keep as-is - cryptographic verification."""

def get_authorization_url(team_id: int, redirect_uri: str) -> str:
    """Keep as-is - URL building."""

def exchange_code_for_token(code: str, redirect_uri: str) -> dict[str, Any]:
    """Keep as direct requests call - no token yet."""

def get_authenticated_user(access_token: str) -> dict[str, Any]:
    """REFACTOR: Return dict with login, id, email, name, avatar_url."""

def get_user_organizations(access_token: str) -> list[dict[str, Any]]:
    """REFACTOR: Return list of org dicts with login, id, description, avatar_url."""

def get_organization_members(access_token: str, org_slug: str) -> list[dict[str, Any]]:
    """REFACTOR: Return list of member dicts with id, login, avatar_url, type."""

def get_user_details(access_token: str, username: str) -> dict[str, Any]:
    """REFACTOR: Return dict with login, id, name, email, avatar_url, bio, company."""

def get_organization_repositories(access_token: str, org_slug: str, exclude_archived: bool = False) -> list[dict[str, Any]]:
    """REFACTOR: Return list of repo dicts with id, full_name, name, description, language, private, updated_at, archived."""
```

### github_webhooks.py

```python
def create_repository_webhook(access_token: str, repo_full_name: str, webhook_url: str, secret: str) -> int:
    """REFACTOR: Return webhook ID (int)."""

def delete_repository_webhook(access_token: str, repo_full_name: str, webhook_id: int) -> bool:
    """REFACTOR: Return True on success/404, raise on other errors."""

def validate_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """Keep as-is - HMAC validation, not API call."""
```

### github_sync.py

```python
def get_repository_pull_requests(access_token: str, repo_full_name: str, state: str = "all", per_page: int = 100) -> list[dict]:
    """REFACTOR: Return list of PR dicts from GitHub API."""

def get_pull_request_reviews(access_token: str, repo_full_name: str, pr_number: int) -> list[dict]:
    """REFACTOR: Return list of review dicts from GitHub API."""

def sync_repository_history(tracked_repo, days_back: int = 90) -> dict:
    """UPDATE: Use refactored functions above."""

def _sync_pr_reviews(pr, pr_number, access_token, repo_full_name, team, errors) -> int:
    """UPDATE: Use refactored get_pull_request_reviews."""
```

---

## PyGithub Mapping Reference

### User Objects

```python
# PyGithub AuthenticatedUser / NamedUser attributes
user.login        # str
user.id           # int
user.email        # str | None
user.name         # str | None
user.avatar_url   # str
user.bio          # str | None
user.company      # str | None
user.location     # str | None
user.type         # str ("User", "Bot", etc.)
```

### Organization Objects

```python
# PyGithub Organization attributes
org.login         # str (slug)
org.id            # int
org.description   # str | None
org.avatar_url    # str
```

### Repository Objects

```python
# PyGithub Repository attributes
repo.id           # int
repo.full_name    # str ("owner/repo")
repo.name         # str
repo.description  # str | None
repo.language     # str | None
repo.private      # bool
repo.archived     # bool
repo.updated_at   # datetime
repo.default_branch # str
```

### PullRequest Objects

```python
# PyGithub PullRequest attributes
pr.id             # int (github_pr_id)
pr.number         # int (pr_number)
pr.title          # str
pr.state          # str ("open", "closed")
pr.merged         # bool
pr.merged_at      # datetime | None
pr.created_at     # datetime
pr.updated_at     # datetime
pr.additions      # int
pr.deletions      # int
pr.commits        # int (commits_count)
pr.changed_files  # int
pr.user           # NamedUser (author)
pr.base.ref       # str (target branch)
pr.head.ref       # str (source branch)
pr.head.sha       # str (head_sha)
pr.html_url       # str
```

### PullRequestReview Objects

```python
# PyGithub PullRequestReview attributes
review.id           # int (github_review_id)
review.user         # NamedUser (reviewer)
review.state        # str ("APPROVED", "CHANGES_REQUESTED", etc.)
review.submitted_at # datetime
review.body         # str | None
```

### Hook Objects

```python
# PyGithub Hook attributes
hook.id           # int
hook.name         # str
hook.active       # bool
hook.events       # list[str]
hook.config       # dict
```

---

## Exception Mapping

```python
from github import (
    GithubException,           # Base exception
    BadCredentialsException,   # 401 - Invalid token
    UnknownObjectException,    # 404 - Not found
    RateLimitExceededException, # 403 - Rate limited
)

# Map to our error:
from apps.integrations.services.github_oauth import GitHubOAuthError

try:
    result = github_api_call()
except BadCredentialsException:
    raise GitHubOAuthError("GitHub API error: 401")
except UnknownObjectException:
    raise GitHubOAuthError("GitHub API error: 404")
except RateLimitExceededException:
    raise GitHubOAuthError("GitHub API error: 403")
except GithubException as e:
    raise GitHubOAuthError(f"GitHub API error: {e.status}")
```

---

## Test Mock Patterns

### Before: Mocking requests

```python
from unittest.mock import MagicMock, patch

@patch("apps.integrations.services.github_oauth.requests.get")
def test_get_authenticated_user_returns_user_data(self, mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "login": "testuser",
        "id": 12345,
        "email": "testuser@example.com",
        "name": "Test User",
        "avatar_url": "https://avatars.githubusercontent.com/u/12345",
    }
    mock_get.return_value = mock_response

    result = get_authenticated_user("gho_test_token")

    self.assertEqual(result["login"], "testuser")
    self.assertEqual(result["id"], 12345)
```

### After: Mocking PyGithub

```python
from unittest.mock import MagicMock, patch

@patch("apps.integrations.services.github_oauth.Github")
def test_get_authenticated_user_returns_user_data(self, MockGithub):
    # Set up mock Github instance
    mock_github = MagicMock()
    MockGithub.return_value = mock_github

    # Set up mock user
    mock_user = MagicMock()
    mock_user.login = "testuser"
    mock_user.id = 12345
    mock_user.email = "testuser@example.com"
    mock_user.name = "Test User"
    mock_user.avatar_url = "https://avatars.githubusercontent.com/u/12345"
    mock_github.get_user.return_value = mock_user

    result = get_authenticated_user("gho_test_token")

    self.assertEqual(result["login"], "testuser")
    self.assertEqual(result["id"], 12345)
    MockGithub.assert_called_once_with("gho_test_token")
```

### Mocking Paginated Lists

```python
@patch("apps.integrations.services.github_oauth.Github")
def test_get_user_organizations_returns_list(self, MockGithub):
    mock_github = MagicMock()
    MockGithub.return_value = mock_github

    # Create mock orgs
    mock_org1 = MagicMock()
    mock_org1.login = "acme-corp"
    mock_org1.id = 1001
    mock_org1.description = "Acme Corporation"
    mock_org1.avatar_url = "https://..."

    mock_org2 = MagicMock()
    mock_org2.login = "test-org"
    mock_org2.id = 1002
    mock_org2.description = "Test Organization"
    mock_org2.avatar_url = "https://..."

    # PaginatedList is iterable - mock as list
    mock_user = MagicMock()
    mock_user.get_orgs.return_value = [mock_org1, mock_org2]
    mock_github.get_user.return_value = mock_user

    result = get_user_organizations("gho_test_token")

    self.assertEqual(len(result), 2)
    self.assertEqual(result[0]["login"], "acme-corp")
```

### Mocking Exceptions

```python
from github import BadCredentialsException

@patch("apps.integrations.services.github_oauth.Github")
def test_get_authenticated_user_handles_bad_credentials(self, MockGithub):
    mock_github = MagicMock()
    MockGithub.return_value = mock_github
    mock_github.get_user.side_effect = BadCredentialsException(401, {"message": "Bad credentials"})

    with self.assertRaises(GitHubOAuthError) as context:
        get_authenticated_user("invalid_token")

    self.assertIn("401", str(context.exception))
```

---

## Files That Call These Functions

These files import and use the functions being refactored:

| Caller File | Functions Used |
|-------------|----------------|
| `apps/integrations/views.py` | `get_authorization_url`, `exchange_code_for_token`, `verify_oauth_state`, `get_authenticated_user`, `get_user_organizations`, `get_organization_members`, `get_user_details`, `get_organization_repositories`, `create_repository_webhook`, `delete_repository_webhook` |
| `apps/metrics/processors.py` | None (uses github_sync indirectly) |
| `apps/integrations/services/github_sync.py` | Imports from `github_oauth` |

**Important:** Function signatures must NOT change to avoid breaking callers.

---

## Verification Commands

```bash
# Install PyGithub
uv add PyGithub

# Run specific test file
make test ARGS='apps.integrations.tests.test_github_oauth --keepdb'
make test ARGS='apps.integrations.tests.test_github_webhooks --keepdb'
make test ARGS='apps.integrations.tests.test_github_sync --keepdb'

# Run all integrations tests
make test ARGS='apps.integrations --keepdb'

# Run all tests
make test ARGS='--keepdb'

# Check for lint errors
make ruff

# Start dev server for manual testing
make dev
```

---

## Notes

- PyGithub handles pagination automatically - no manual Link header parsing needed
- PyGithub objects are not JSON serializable - must convert to dicts
- Rate limit info: `github.get_rate_limit()` returns `RateLimit` object
- For incremental sync (Phase 2.6), use Issues API: `repo.get_issues(since=datetime)`
