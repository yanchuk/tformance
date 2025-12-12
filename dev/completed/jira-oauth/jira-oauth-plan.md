# Phase 3.1: Jira OAuth Integration Plan

**Last Updated:** 2025-12-11

---

## Executive Summary

Implement Atlassian OAuth 2.0 (3LO) flow to connect teams with their Jira Cloud instances. This phase establishes the authentication foundation for all subsequent Jira integration features (project selection, user matching, data sync).

### Goals
- Enable teams to connect Jira Cloud via OAuth 2.0
- Store encrypted tokens with refresh capability
- Allow site selection for multi-site Atlassian accounts
- Follow established GitHub OAuth patterns for consistency

### Success Criteria
- Users can connect/disconnect Jira from integrations page
- OAuth tokens are encrypted at rest
- Token refresh works automatically when needed
- Multi-site accounts can select which site to use

---

## Current State Analysis

### Existing Infrastructure

**IntegrationCredential Model** (already exists):
- `provider` field supports `PROVIDER_JIRA = "jira"`
- `access_token`, `refresh_token`, `token_expires_at` fields ready
- `scopes` JSONField for storing granted scopes
- `connected_by` ForeignKey to track who connected

**GitHub OAuth Pattern** (to follow):
- `github_oauth.py` service with state management
- `views.py` with connect/callback/disconnect views
- Encryption via `services/encryption.py`
- Templates for org/repo selection

### What's Missing

1. **JiraIntegration Model** - Similar to GitHubIntegration
2. **jira_oauth.py** - OAuth flow service
3. **Views** - Connect, callback, disconnect, site selection
4. **Templates** - Site selection UI
5. **URL routes** - `/a/<team>/integrations/jira/*`

---

## Technical Architecture

### Atlassian OAuth 2.0 (3LO) Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. User clicks "Connect Jira"                                  │
│     → Redirect to auth.atlassian.com/authorize                  │
│     → Parameters: client_id, redirect_uri, scope, state         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  2. User authorizes on Atlassian consent screen                 │
│     → Grants read:jira-work, read:jira-user, offline_access     │
│     → Atlassian redirects to our callback with ?code=           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  3. Exchange code for tokens                                     │
│     → POST auth.atlassian.com/oauth/token                       │
│     → Returns: access_token, refresh_token, expires_in          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  4. Get accessible resources (sites)                            │
│     → GET api.atlassian.com/oauth/token/accessible-resources    │
│     → Returns: [{id: cloud_id, name, url, scopes}]              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  5. Site selection (if multiple) or auto-connect                │
│     → Store encrypted tokens in IntegrationCredential           │
│     → Create JiraIntegration with cloud_id                      │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `https://auth.atlassian.com/authorize` | Authorization URL |
| `https://auth.atlassian.com/oauth/token` | Token exchange & refresh |
| `https://api.atlassian.com/oauth/token/accessible-resources` | List accessible sites |
| `https://api.atlassian.com/ex/jira/{cloud_id}/rest/api/3/*` | Jira API requests |

### Required Scopes

| Scope | Purpose |
|-------|---------|
| `read:jira-work` | Read issues, projects, worklogs |
| `read:jira-user` | Read user info for matching |
| `offline_access` | Get refresh token |

---

## Data Model

### New Model: JiraIntegration

```python
class JiraIntegration(BaseTeamModel):
    """Jira integration configuration for a team."""

    credential = models.OneToOneField(
        IntegrationCredential,
        on_delete=models.CASCADE,
        related_name="jira_integration",
    )
    cloud_id = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Atlassian Cloud ID for API requests",
    )
    site_name = models.CharField(
        max_length=255,
        help_text="Display name of the Jira site",
    )
    site_url = models.URLField(
        help_text="URL of the Jira site (e.g., https://acme.atlassian.net)",
    )
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default=SYNC_STATUS_PENDING,
    )
```

### Existing Model Updates

**IntegrationCredential** - No changes needed, already supports:
- `refresh_token` field
- `token_expires_at` field
- `scopes` JSONField

---

## Implementation Phases

### Section 1: OAuth Service Layer

**Tasks:**
1. Create `apps/integrations/services/jira_oauth.py`
2. Implement state creation/verification (reuse pattern from GitHub)
3. Implement `get_authorization_url()`
4. Implement `exchange_code_for_token()`
5. Implement `refresh_access_token()`
6. Implement `get_accessible_resources()`

### Section 2: Data Model

**Tasks:**
1. Create `JiraIntegration` model
2. Create migration
3. Add admin registration
4. Create factory for testing

### Section 3: Views & URLs

**Tasks:**
1. Add `jira_connect` view
2. Add `jira_callback` view
3. Add `jira_disconnect` view
4. Add `jira_select_site` view (for multi-site accounts)
5. Add URL patterns in `urls.py`

### Section 4: Templates & UI

**Tasks:**
1. Update `integrations/home.html` with Jira connection card
2. Create `integrations/jira_select_site.html` template
3. Add disconnect confirmation modal

### Section 5: Token Refresh Mechanism

**Tasks:**
1. Create `ensure_valid_token()` helper
2. Integrate with future API calls
3. Handle refresh failures gracefully

---

## Security Considerations

1. **State Parameter** - CSRF protection using signed team_id (same as GitHub)
2. **Token Encryption** - Use existing `encrypt()`/`decrypt()` from encryption.py
3. **Refresh Token Rotation** - Atlassian uses rotating refresh tokens
4. **Scope Limitation** - Request minimum scopes needed

---

## Settings Required

Add to `tformance/settings.py`:

```python
# Jira OAuth Settings
JIRA_CLIENT_ID = env("JIRA_CLIENT_ID", default="")
JIRA_CLIENT_SECRET = env("JIRA_CLIENT_SECRET", default="")
```

Add to `.env.example`:

```
JIRA_CLIENT_ID=your-client-id
JIRA_CLIENT_SECRET=your-client-secret
```

---

## Testing Strategy

### Unit Tests
- State creation/verification
- Token exchange (mocked)
- Token refresh (mocked)
- Accessible resources parsing

### Integration Tests
- Full OAuth flow (with mocked external calls)
- Site selection with multiple sites
- Disconnect flow

### Test Coverage Target
- 100% coverage for jira_oauth.py service
- 100% coverage for new views

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| IntegrationCredential model | ✅ Exists | Has all required fields |
| Encryption service | ✅ Exists | `services/encryption.py` |
| GitHub OAuth patterns | ✅ Reference | Follow same structure |
| Atlassian Developer App | ❌ Required | User must create app |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token refresh failures | Medium | High | Graceful degradation, user notification |
| Multi-site complexity | Low | Medium | Clear UI for site selection |
| Atlassian API changes | Low | Medium | Version-specific API paths |
| Rate limiting | Low | Low | Daily sync pattern (same as GitHub) |

---

## Related Documentation

- [Atlassian OAuth 2.0 (3LO) Apps](https://developer.atlassian.com/cloud/jira/platform/oauth-2-3lo-apps/)
- [Jira Scopes](https://developer.atlassian.com/cloud/jira/platform/scopes-for-oauth-2-3LO-and-forge-apps/)
- [Implementing OAuth 2.0 (3LO)](https://developer.atlassian.com/cloud/oauth/getting-started/implementing-oauth-3lo/)
