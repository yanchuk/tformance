# Phase 3.1: Jira OAuth - Context Document

**Last Updated:** 2025-12-11

---

## Critical Discovery: Jira Development Info API Limitation

### The Problem

**Atlassian does NOT provide a public API to READ linked PRs/commits from Jira issues.**

| What We Want | API Status |
|--------------|------------|
| Read linked PRs from Jira issue | ❌ **Internal/Unsupported** |
| Read linked commits from issue | ❌ **Internal/Unsupported** |
| Write/push dev info TO Jira | ✅ Public API exists |

**Source**: [Atlassian Developer Community Discussion](https://community.developer.atlassian.com/t/permissions-to-get-issue-development-information-commits-pull-requests/5911)

> "This API is not public. It's not guaranteed by our REST API policy and could change at any time without notice."

**Feature request open since 2017** - still no public endpoint (JSWCLOUD-16901).

### How GitHub for Jira App Works

Even Atlassian's official app uses **text parsing** from PR titles, branch names, and commit messages:

```
Branch: DEV-2095-fix-login
Commit: DEV-2095 fix login bug
PR title: DEV-2095: Fix login validation
```

The app **pushes** parsed data TO Jira. There's no "read all linked PRs" API.

### Solution: Extract Jira Keys from GitHub Data

Since we already sync GitHub PRs (Phase 2), extract Jira keys using regex:

```python
import re

def extract_jira_key(text: str) -> str | None:
    """Extract first Jira issue key from text."""
    match = re.search(r'[A-Z][A-Z0-9]+-\d+', text or '')
    return match.group(0) if match else None

# Usage during PR sync
jira_key = extract_jira_key(pr.title) or extract_jira_key(pr.head.ref)
```

**Requires**: Add `jira_key` field to `PullRequest` model (see tasks).

---

## Key Files

### Existing Files to Reference

| File | Purpose | Relevance |
|------|---------|-----------|
| `apps/integrations/models.py` | IntegrationCredential, GitHubIntegration | Pattern for JiraIntegration |
| `apps/integrations/services/github_oauth.py` | GitHub OAuth implementation | Template for jira_oauth.py |
| `apps/integrations/services/encryption.py` | Token encryption | Reuse for Jira tokens |
| `apps/integrations/views.py` | GitHub connect/callback views | Pattern for Jira views |
| `apps/integrations/urls.py` | URL routing | Add Jira routes |
| `apps/integrations/factories.py` | Test factories | Add JiraIntegrationFactory |
| `apps/integrations/constants.py` | Sync status constants | Reuse for Jira |
| `tformance/settings.py` | Django settings | Add JIRA_CLIENT_ID/SECRET |

### Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/jira_oauth.py` | Jira OAuth service |
| `apps/integrations/services/jira_client.py` | Jira API client factory (Phase 3.2+) |
| `apps/integrations/tests/test_jira_oauth.py` | OAuth service tests |
| `apps/integrations/tests/test_jira_views.py` | View tests |
| `templates/integrations/jira_select_site.html` | Site selection template |
| Migration for JiraIntegration model | Database schema |

---

## Architectural Decisions

### Decision 1: Direct API Calls vs Library

**Decision:** Use direct `requests` calls for OAuth flow, defer library decision to Phase 3.2

**Reasoning:**
- OAuth flow is simple HTTP requests
- No need for pagination or complex operations
- Library (atlassian-python-api or jira-python) better suited for data sync
- Keeps OAuth layer independent

### Decision 2: State Parameter Format

**Decision:** Reuse GitHub's signed state pattern

**Implementation:**
```python
# Same pattern as github_oauth.py
payload = json.dumps({"team_id": team_id})
encoded = base64.b64encode(payload.encode()).decode()
signed_state = Signer().sign(encoded)
```

### Decision 3: Token Storage

**Decision:** Store in existing IntegrationCredential model

**Fields Used:**
- `access_token` - Encrypted access token
- `refresh_token` - Encrypted refresh token
- `token_expires_at` - Expiration timestamp
- `scopes` - List of granted scopes

### Decision 4: Site Selection UX

**Decision:** Same pattern as GitHub org selection

**Flow:**
- Single site → Auto-connect, redirect to integrations home
- Multiple sites → Show selection page, user picks one

---

## API Reference

### Authorization URL

```
GET https://auth.atlassian.com/authorize
?audience=api.atlassian.com
&client_id={JIRA_CLIENT_ID}
&scope=read:jira-work read:jira-user offline_access
&redirect_uri={callback_url}
&state={signed_state}
&response_type=code
&prompt=consent
```

### Token Exchange

```
POST https://auth.atlassian.com/oauth/token
Content-Type: application/json

{
    "grant_type": "authorization_code",
    "client_id": "{JIRA_CLIENT_ID}",
    "client_secret": "{JIRA_CLIENT_SECRET}",
    "code": "{authorization_code}",
    "redirect_uri": "{callback_url}"
}

Response:
{
    "access_token": "...",
    "refresh_token": "...",
    "expires_in": 3600,
    "scope": "read:jira-work read:jira-user offline_access"
}
```

### Token Refresh

```
POST https://auth.atlassian.com/oauth/token
Content-Type: application/json

{
    "grant_type": "refresh_token",
    "client_id": "{JIRA_CLIENT_ID}",
    "client_secret": "{JIRA_CLIENT_SECRET}",
    "refresh_token": "{refresh_token}"
}
```

### Accessible Resources

```
GET https://api.atlassian.com/oauth/token/accessible-resources
Authorization: Bearer {access_token}

Response:
[
    {
        "id": "11223344-a1b2-3b33-c444-def123456789",  // cloud_id
        "name": "Acme Corp",
        "url": "https://acme.atlassian.net",
        "scopes": ["read:jira-work", "read:jira-user"],
        "avatarUrl": "https://..."
    }
]
```

---

## Dependencies Between Tasks

```
┌─────────────────────────────────┐
│ 1. Settings (JIRA_CLIENT_*)    │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ 2. jira_oauth.py service        │
│    - state functions            │
│    - get_authorization_url      │
│    - exchange_code_for_token    │
│    - refresh_access_token       │
│    - get_accessible_resources   │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ 3. JiraIntegration model        │
│    - migration                  │
│    - admin                      │
│    - factory                    │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ 4. Views (in parallel)          │
│    - jira_connect               │
│    - jira_callback              │
│    - jira_disconnect            │
│    - jira_select_site           │
└─────────────┬───────────────────┘
              ↓
┌─────────────────────────────────┐
│ 5. Templates & URLs             │
│    - Update home.html           │
│    - jira_select_site.html      │
│    - URL patterns               │
└─────────────────────────────────┘
```

---

## Error Handling

### OAuth Errors

| Error | Cause | User Message |
|-------|-------|--------------|
| `access_denied` | User declined | "Jira authorization was cancelled." |
| Missing `code` | OAuth failure | "Missing authorization code from Jira." |
| Invalid `state` | CSRF/tampering | "Invalid state parameter." |
| Token exchange failure | API error | "Failed to exchange authorization code." |

### Token Refresh Errors

| Error | Handling |
|-------|----------|
| Invalid refresh token | Mark integration as disconnected, prompt re-auth |
| Network error | Retry with exponential backoff |
| Rate limited | Wait and retry |

---

## Testing Patterns

### Mocking OAuth Responses

```python
@patch("apps.integrations.services.jira_oauth.requests.post")
def test_exchange_code_for_token(self, mock_post):
    mock_post.return_value.status_code = 200
    mock_post.return_value.json.return_value = {
        "access_token": "test_access_token",
        "refresh_token": "test_refresh_token",
        "expires_in": 3600,
    }

    result = jira_oauth.exchange_code_for_token("test_code", "http://callback")

    self.assertEqual(result["access_token"], "test_access_token")
```

### Mocking Accessible Resources

```python
@patch("apps.integrations.services.jira_oauth.requests.get")
def test_get_accessible_resources(self, mock_get):
    mock_get.return_value.status_code = 200
    mock_get.return_value.json.return_value = [
        {
            "id": "cloud-123",
            "name": "Test Site",
            "url": "https://test.atlassian.net",
            "scopes": ["read:jira-work"],
        }
    ]

    result = jira_oauth.get_accessible_resources("access_token")

    self.assertEqual(len(result), 1)
    self.assertEqual(result[0]["id"], "cloud-123")
```

---

## Comparison: GitHub vs Jira OAuth

| Aspect | GitHub | Jira (Atlassian) |
|--------|--------|------------------|
| Auth URL | `github.com/login/oauth/authorize` | `auth.atlassian.com/authorize` |
| Token URL | `github.com/login/oauth/access_token` | `auth.atlassian.com/oauth/token` |
| API Base | `api.github.com` | `api.atlassian.com/ex/jira/{cloud_id}` |
| Site/Org discovery | Orgs endpoint | Accessible resources endpoint |
| Refresh tokens | No (tokens don't expire) | Yes (rotating, 1hr expiry) |
| Required param | - | `audience=api.atlassian.com` |
| Required param | - | `prompt=consent` |

---

## Environment Setup

### Developer Console Setup

1. Go to https://developer.atlassian.com/console/myapps/
2. Create new OAuth 2.0 (3LO) app
3. Configure:
   - App name: "tformance" (or similar)
   - Redirect URI: `http://localhost:8000/a/<team_slug>/integrations/jira/callback/`
   - Scopes: `read:jira-work`, `read:jira-user`, `offline_access`
4. Copy Client ID and Secret to `.env`

### Local Testing

```bash
# .env additions
JIRA_CLIENT_ID=your-client-id-here
JIRA_CLIENT_SECRET=your-client-secret-here
```

---

## References

- [Atlassian OAuth 2.0 (3LO) Apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Implementing OAuth 2.0](https://developer.atlassian.com/cloud/oauth/getting-started/implementing-oauth-3lo/)
- [Jira Scopes](https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/)
- [GitHub OAuth implementation](../../../apps/integrations/services/github_oauth.py) - Pattern reference
