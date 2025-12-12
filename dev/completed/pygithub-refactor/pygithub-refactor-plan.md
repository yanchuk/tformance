# PyGithub Refactor - Implementation Plan

> Last Updated: 2025-12-11

## Executive Summary

Refactor all GitHub API direct `requests` calls to use the **PyGithub** official library. This provides better pagination handling, rate limiting awareness, typed responses, and maintainable code - setting up a solid foundation before adding incremental sync (Phase 2.6).

**Scope:** 3 service files, ~150 tests to update, 0 model changes

---

## Current State Analysis

### Files Using Direct API Calls

| File | Functions | Lines | Tests |
|------|-----------|-------|-------|
| `github_oauth.py` | 10 functions | 328 | 77 tests |
| `github_webhooks.py` | 3 functions | 128 | 18 tests |
| `github_sync.py` | 4 functions | 247 | 24 tests |

### Functions Inventory

#### github_oauth.py (10 functions)
| Function | PyGithub Equivalent | Notes |
|----------|---------------------|-------|
| `create_oauth_state()` | N/A | Keep as-is (cryptographic) |
| `verify_oauth_state()` | N/A | Keep as-is (cryptographic) |
| `get_authorization_url()` | N/A | Keep as-is (URL building) |
| `exchange_code_for_token()` | N/A | **Keep as direct call** - happens before token exists |
| `_make_github_api_request()` | Remove | Helper - replaced by PyGithub |
| `_make_paginated_github_api_request()` | Remove | Helper - replaced by PyGithub |
| `_parse_next_link()` | Remove | Helper - replaced by PyGithub |
| `get_authenticated_user()` | `Github.get_user()` | Refactor |
| `get_user_organizations()` | `Github.get_user().get_orgs()` | Refactor |
| `get_organization_members()` | `org.get_members()` | Refactor |
| `get_user_details()` | `Github.get_user(username)` | Refactor |
| `get_organization_repositories()` | `org.get_repos()` | Refactor |

#### github_webhooks.py (3 functions)
| Function | PyGithub Equivalent | Notes |
|----------|---------------------|-------|
| `create_repository_webhook()` | `repo.create_hook()` | Refactor |
| `delete_repository_webhook()` | `hook.delete()` | Refactor |
| `validate_webhook_signature()` | N/A | Keep as-is (HMAC validation) |

#### github_sync.py (4 functions)
| Function | PyGithub Equivalent | Notes |
|----------|---------------------|-------|
| `_make_paginated_github_request()` | Remove | Duplicate of oauth helper |
| `get_repository_pull_requests()` | `repo.get_pulls()` | Refactor |
| `get_pull_request_reviews()` | `pr.get_reviews()` | Refactor |
| `sync_repository_history()` | Uses above | Update to use new functions |
| `_sync_pr_reviews()` | Uses above | Update to use new functions |

### What Must Stay as Direct Calls

1. **`exchange_code_for_token()`** - OAuth token exchange happens before we have a token
2. **`validate_webhook_signature()`** - HMAC calculation, not an API call
3. **OAuth state functions** - Cryptographic signing, not API calls

---

## Proposed Future State

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Service Layer                         │
├─────────────────────────────────────────────────────────┤
│  github_client.py (NEW)                                 │
│  ├── get_github_client(access_token) -> Github          │
│  └── GitHubClientError                                  │
├─────────────────────────────────────────────────────────┤
│  github_oauth.py (REFACTORED)                           │
│  ├── create_oauth_state()      (unchanged)              │
│  ├── verify_oauth_state()      (unchanged)              │
│  ├── get_authorization_url()   (unchanged)              │
│  ├── exchange_code_for_token() (unchanged - direct)     │
│  ├── get_authenticated_user()  → uses PyGithub          │
│  ├── get_user_organizations()  → uses PyGithub          │
│  ├── get_organization_members()→ uses PyGithub          │
│  ├── get_user_details()        → uses PyGithub          │
│  └── get_organization_repos()  → uses PyGithub          │
├─────────────────────────────────────────────────────────┤
│  github_webhooks.py (REFACTORED)                        │
│  ├── create_repository_webhook() → uses PyGithub        │
│  ├── delete_repository_webhook() → uses PyGithub        │
│  └── validate_webhook_signature() (unchanged - HMAC)    │
├─────────────────────────────────────────────────────────┤
│  github_sync.py (REFACTORED)                            │
│  ├── get_repository_pull_requests() → uses PyGithub     │
│  ├── get_pull_request_reviews()     → uses PyGithub     │
│  ├── sync_repository_history()      → uses above        │
│  └── _sync_pr_reviews()             → uses above        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌───────────────────────┐
              │      PyGithub         │
              │  (handles pagination, │
              │   rate limits, etc.)  │
              └───────────────────────┘
```

### Benefits

1. **Automatic pagination** - No more manual Link header parsing
2. **Rate limit handling** - PyGithub respects rate limits
3. **Typed responses** - IDE completion, fewer bugs
4. **Less code** - Remove ~100 lines of HTTP handling
5. **Better errors** - Typed exceptions (BadCredentialsException, etc.)
6. **Future-proof** - Easy to add new GitHub features

---

## Implementation Phases

### Section 1: Foundation - PyGithub Setup

| # | Task | Acceptance Criteria | Effort |
|---|------|---------------------|--------|
| 1.1 | Add PyGithub dependency | `PyGithub>=2.1.0` in pyproject.toml, `uv sync` passes | S |
| 1.2 | Create `github_client.py` | Helper module with `get_github_client(token)` function | S |
| 1.3 | Write tests for github_client | Test client creation, test invalid token handling | S |
| 1.4 | Define exception mapping | Map PyGithub exceptions to our `GitHubOAuthError` | S |

### Section 2: Refactor github_oauth.py

Refactor read-only API calls first (lower risk).

| # | Task | Acceptance Criteria | Effort |
|---|------|---------------------|--------|
| 2.1 | Refactor `get_authenticated_user()` | Uses `github.get_user()`, tests pass | M |
| 2.2 | Refactor `get_user_organizations()` | Uses `user.get_orgs()`, tests pass | M |
| 2.3 | Refactor `get_user_details()` | Uses `github.get_user(username)`, tests pass | M |
| 2.4 | Refactor `get_organization_members()` | Uses `org.get_members()`, tests pass | M |
| 2.5 | Refactor `get_organization_repositories()` | Uses `org.get_repos()`, tests pass | M |
| 2.6 | Remove dead code | Delete `_make_github_api_request`, `_make_paginated_*`, `_parse_next_link` | S |
| 2.7 | Update test mocks | Update all tests to mock PyGithub instead of requests | L |

### Section 3: Refactor github_webhooks.py

Refactor write operations (webhook create/delete).

| # | Task | Acceptance Criteria | Effort |
|---|------|---------------------|--------|
| 3.1 | Refactor `create_repository_webhook()` | Uses `repo.create_hook()`, tests pass | M |
| 3.2 | Refactor `delete_repository_webhook()` | Uses `hook.delete()`, tests pass | M |
| 3.3 | Update test mocks | Update tests to mock PyGithub instead of requests | M |

### Section 4: Refactor github_sync.py

Refactor sync service (most critical for Phase 2.6).

| # | Task | Acceptance Criteria | Effort |
|---|------|---------------------|--------|
| 4.1 | Refactor `get_repository_pull_requests()` | Uses `repo.get_pulls()`, tests pass | M |
| 4.2 | Refactor `get_pull_request_reviews()` | Uses `pr.get_reviews()`, tests pass | M |
| 4.3 | Update `sync_repository_history()` | Uses refactored functions, tests pass | M |
| 4.4 | Update `_sync_pr_reviews()` | Uses refactored functions, tests pass | S |
| 4.5 | Remove duplicate pagination helper | Delete `_make_paginated_github_request` | S |
| 4.6 | Update test mocks | Update all tests to mock PyGithub | L |

### Section 5: Cleanup & Verification

| # | Task | Acceptance Criteria | Effort |
|---|------|---------------------|--------|
| 5.1 | Remove `requests` import from services | No more `import requests` in github_*.py | S |
| 5.2 | Run full test suite | All 560+ tests pass | S |
| 5.3 | Run lint | `make ruff` passes | S |
| 5.4 | Manual smoke test | OAuth flow, repo tracking work in browser | M |
| 5.5 | Update documentation | Update context file, CLAUDE.md if needed | S |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| PyGithub returns different data structure | Medium | High | Keep function signatures identical, transform PyGithub objects to dicts |
| Test mocks break extensively | High | Medium | Update tests incrementally per function |
| Rate limiting behavior differs | Low | Medium | Test with real GitHub account in dev |
| Missing PyGithub feature | Low | Low | Check docs before each refactor; fallback to requests if needed |

---

## Success Metrics

1. **Zero behavior changes** - All existing functionality works identically
2. **All tests pass** - 560+ tests green
3. **Code reduction** - ~100 lines of HTTP handling removed
4. **No `requests` usage** - Only PyGithub for GitHub API (except token exchange)

---

## Required Resources

### Dependencies

```toml
# pyproject.toml
dependencies = [
    "PyGithub>=2.1.0",
]
```

### PyGithub Quick Reference

```python
from github import Github, GithubException, BadCredentialsException, UnknownObjectException

# Create client
g = Github(access_token)

# Get authenticated user
user = g.get_user()  # AuthenticatedUser object
user.login, user.id, user.email, user.name, user.avatar_url

# Get user's orgs
orgs = user.get_orgs()  # PaginatedList[Organization]
for org in orgs:
    org.login, org.id, org.description

# Get specific user
user = g.get_user("username")  # NamedUser object

# Get org
org = g.get_organization("org-slug")

# Get org members
members = org.get_members()  # PaginatedList[NamedUser]

# Get org repos
repos = org.get_repos()  # PaginatedList[Repository]

# Get repo
repo = g.get_repo("owner/repo")

# Create webhook
hook = repo.create_hook(
    name="web",
    config={"url": url, "content_type": "json", "secret": secret},
    events=["pull_request", "pull_request_review"],
    active=True
)
hook.id  # webhook ID

# Delete webhook
hook = repo.get_hook(webhook_id)
hook.delete()

# Get PRs
prs = repo.get_pulls(state="all")  # PaginatedList[PullRequest]

# Get PR reviews
pr = repo.get_pull(number)
reviews = pr.get_reviews()  # PaginatedList[PullRequestReview]
```

---

## Test Strategy

### Mock Pattern Change

**Before (requests mock):**
```python
@patch("apps.integrations.services.github_oauth.requests.get")
def test_get_authenticated_user(self, mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"login": "user", "id": 123}
    mock_get.return_value = mock_response
```

**After (PyGithub mock):**
```python
@patch("apps.integrations.services.github_oauth.Github")
def test_get_authenticated_user(self, mock_github_class):
    mock_github = MagicMock()
    mock_user = MagicMock()
    mock_user.login = "user"
    mock_user.id = 123
    mock_user.email = "user@example.com"
    mock_user.name = "Test User"
    mock_user.avatar_url = "https://..."
    mock_github.get_user.return_value = mock_user
    mock_github_class.return_value = mock_github
```

### Return Value Transformation

Functions should continue returning dicts (not PyGithub objects) to maintain backward compatibility:

```python
def get_authenticated_user(access_token: str) -> dict[str, Any]:
    """Get authenticated user data from GitHub API."""
    g = Github(access_token)
    user = g.get_user()
    return {
        "login": user.login,
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "avatar_url": user.avatar_url,
    }
```

---

## Estimated Total Effort

| Section | Tasks | Effort |
|---------|-------|--------|
| 1. Foundation | 4 | Small |
| 2. github_oauth.py | 7 | Large |
| 3. github_webhooks.py | 3 | Medium |
| 4. github_sync.py | 6 | Large |
| 5. Cleanup | 5 | Small |
| **Total** | **25** | **Large** |

Estimated TDD cycles: 15-20
