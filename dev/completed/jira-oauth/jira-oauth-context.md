# Phase 3.1: Jira OAuth - Context Document

**Last Updated:** 2025-12-11
**Status:** COMPLETE

---

## Implementation Summary

Phase 3.1 Jira OAuth is fully implemented with 119 new tests added (707 total tests passing).

### Files Created

| File | Purpose |
|------|---------|
| `apps/integrations/services/jira_oauth.py` | Full OAuth service (state, auth URL, token exchange, refresh, accessible resources) |
| `apps/integrations/tests/test_jira_oauth.py` | 36 tests for OAuth service |
| `apps/integrations/tests/test_jira_views.py` | 36 tests for views |
| `apps/integrations/migrations/0008_jiraintegration.py` | JiraIntegration model migration |
| `templates/integrations/jira_select_site.html` | Minimal site selection template |

### Files Modified

| File | Changes |
|------|---------|
| `tformance/settings.py` | Added JIRA_CLIENT_ID, JIRA_CLIENT_SECRET (lines 328-330) |
| `.env.example` | Added Jira env placeholders (lines 26-27) |
| `apps/integrations/models.py` | Added JiraIntegration model (lines 222-283) |
| `apps/integrations/views.py` | Added 4 views + refactored shared helpers (lines 71-136, 704-914) |
| `apps/integrations/urls.py` | Added 4 URL patterns for Jira |
| `apps/integrations/admin.py` | Added JiraIntegrationAdmin, JiraIntegrationInline |
| `apps/integrations/factories.py` | Added JiraIntegrationFactory (lines 100-116) |

---

## Critical Discovery: Jira Development Info API Limitation

### The Problem

**Atlassian does NOT provide a public API to READ linked PRs/commits from Jira issues.**

| What We Want | API Status |
|--------------|------------|
| Read linked PRs from Jira issue | **Internal/Unsupported** |
| Read linked commits from issue | **Internal/Unsupported** |
| Write/push dev info TO Jira | Public API exists |

**Source**: [Atlassian Developer Community Discussion](https://community.developer.atlassian.com/t/permissions-to-get-issue-development-information-commits-pull-requests/5911)

> "This API is not public. It's not guaranteed by our REST API policy and could change at any time without notice."

**Feature request open since 2017** - still no public endpoint (JSWCLOUD-16901).

### Solution Implemented: Extract Jira Keys from GitHub Data

```python
# apps/integrations/services/jira_utils.py
import re

def extract_jira_key(text: str) -> str | None:
    """Extract first Jira issue key from text."""
    if not text:
        return None
    match = re.search(r'[A-Z][A-Z0-9]+-\d+', text)
    return match.group(0) if match else None
```

---

## Key Architectural Decisions

### 1. OAuth Service Pattern
- Direct `requests` calls for OAuth (no library)
- Same signed state pattern as GitHub OAuth
- Extracted `_make_token_request()` helper for DRY

### 2. View Refactoring
- Extracted `_create_integration_credential()` - generic for all providers
- Extracted `_validate_oauth_callback()` - shared OAuth validation
- Reduced ~60 lines of duplication between GitHub and Jira views

### 3. Token Refresh
- `ensure_valid_jira_token(credential)` helper
- 5-minute buffer before expiration triggers refresh
- `TOKEN_REFRESH_BUFFER` constant for configurability

### 4. JiraIntegration Model
- OneToOne relationship with IntegrationCredential
- cloud_id indexed for fast lookups
- Compound index on (sync_status, last_sync_at)

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
```

### Accessible Resources
```
GET https://api.atlassian.com/oauth/token/accessible-resources
Authorization: Bearer {access_token}
```

---

## Verification Commands

```bash
# Run all tests
make test ARGS='--keepdb'
# Expected: 707 tests pass

# Run Jira-specific tests
make test ARGS='apps.integrations.tests.test_jira_oauth --keepdb'
make test ARGS='apps.integrations.tests.test_jira_views --keepdb'

# Lint check
make ruff

# Check migrations
make migrations  # Should say "No changes detected"
```

---

## Next Phase: 3.2 Jira Projects Sync

The next phase will:
1. Use `jira-python` library for API calls
2. Sync Jira projects to local model
3. Sync Jira issues with timestamps
4. Integrate with `ensure_valid_jira_token()` for auto-refresh

See IMPLEMENTATION-PLAN.md for detailed next steps.
