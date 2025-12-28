# Unified GitHub OAuth Callback

**Last Updated:** 2025-12-28

## Executive Summary

Unify the duplicate GitHub OAuth callback URLs into a single endpoint. Currently, the onboarding flow and integrations flow use separate callback URLs, which requires configuring multiple URLs in the GitHub OAuth App. Since GitHub OAuth Apps only support **one callback URL**, this causes OAuth failures.

**Scope:** GitHub OAuth only. Jira and Slack already use single callback URLs.

## Problem Statement

| Flow | Current Callback URL | Purpose |
|------|---------------------|---------|
| Onboarding | `/onboarding/github/callback/` | Create new team from GitHub org |
| Integrations | `/app/<team>/integrations/github/callback/` | Add GitHub to existing team |

GitHub OAuth Apps support only ONE callback URL, but the redirect_uri can be a **subdirectory** of that URL. This means we need a single callback that handles both flows.

## Proposed Solution

Create a single unified callback at `/auth/github/callback/` that:
1. Parses the `state` parameter to determine which flow initiated the OAuth
2. Routes to appropriate handler logic based on state type
3. Redirects to the correct next step

### State Parameter Design

```json
// Onboarding flow
{"type": "onboarding", "iat": 1703750400}

// Integration flow (existing team)
{"type": "integration", "team_id": 123, "iat": 1703750400}
```

## Current State Analysis

### Onboarding Flow (`apps/onboarding/views.py`)
- **Decorator:** `@login_required`
- **State:** `{"type": "onboarding"}` (no team_id)
- **Token storage:** Encrypted in session
- **After callback:** Creates Team + GitHubIntegration + syncs members
- **Next step:** Redirect to org selection or repo selection

### Integration Flow (`apps/integrations/views/github.py`)
- **Decorator:** `@login_and_team_required`
- **State:** `{"team_id": <id>, "iat": <timestamp>}`
- **Token storage:** `IntegrationCredential` model (encrypted)
- **After callback:** Creates GitHubIntegration for existing team
- **Next step:** Redirect to integrations home or org selection

## Proposed Future State

### New Module: `apps/auth/`

```
apps/auth/
├── __init__.py
├── urls.py          # Single /auth/github/callback/ route
├── views.py         # Unified callback dispatcher
└── services/
    └── oauth_state.py  # State creation/verification
```

### Unified Callback Flow

```
GitHub OAuth Complete
        ↓
/auth/github/callback/
        ↓
Parse state parameter
        ↓
    ┌───────────────┐
    │ type = ?      │
    └───────────────┘
         ↓                    ↓
   "onboarding"         "integration"
         ↓                    ↓
 Create Team            Get existing Team
 from GitHub org        from state.team_id
         ↓                    ↓
 Store token            Store credential
 in session             in database
         ↓                    ↓
 Redirect to            Redirect to
 /onboarding/org/       integrations home
```

## Implementation Phases

### Phase 1: Create Unified OAuth State Service (Effort: S)
Consolidate state creation/verification logic into a single service.

### Phase 2: Create Unified Callback Endpoint (Effort: M)
Create new `/auth/github/callback/` endpoint with routing logic.

### Phase 3: Update Connect Views (Effort: S)
Update `github_connect` views in both apps to use new callback URL.

### Phase 4: Migrate and Clean Up (Effort: S)
Remove old callback views and update tests.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing OAuth sessions | Low | Medium | Deploy during low-traffic period |
| State validation failures | Low | Medium | Comprehensive test coverage |
| Incorrect routing | Low | High | Unit tests for each flow |

## Success Metrics

1. Single callback URL configured in GitHub OAuth App
2. Both onboarding and integration flows work correctly
3. All existing tests pass
4. No increase in OAuth-related errors

## Dependencies

- No external dependencies
- Requires updating GitHub OAuth App callback URL after deployment

## Files to Modify

### New Files
- `apps/auth/__init__.py`
- `apps/auth/urls.py`
- `apps/auth/views.py`
- `apps/auth/tests/test_github_callback.py`

### Modified Files
- `apps/onboarding/views.py` - Update `github_connect` to use new callback URL
- `apps/integrations/views/github.py` - Update `github_connect` to use new callback URL
- `apps/integrations/services/github_oauth.py` - Consolidate state handling
- `tformance/urls.py` - Add `/auth/` URL include

### Deleted (after migration)
- `apps/onboarding/views.py` - `github_callback` function
- `apps/integrations/views/github.py` - `github_callback` function
