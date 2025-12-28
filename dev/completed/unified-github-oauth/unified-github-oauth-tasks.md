# Unified GitHub OAuth - Tasks

**Last Updated:** 2025-12-28

## Phase 1: Create Unified OAuth State Service

### 1.1 Create unified state module
- [ ] Create `apps/integrations/services/oauth_state.py`
- [ ] Implement `create_oauth_state(flow_type: str, team_id: int | None = None) -> str`
- [ ] Implement `verify_oauth_state(state: str) -> dict` returning `{"type": ..., "team_id": ..., "iat": ...}`
- [ ] Add state expiration check (10 min max age)
- [ ] Add unit tests for state creation and verification

**Acceptance Criteria:**
- State includes `type` field ("onboarding" or "integration")
- State includes `iat` timestamp
- State includes `team_id` only for integration flow
- Verification rejects expired or invalid states

---

## Phase 2: Create Unified Callback Endpoint

### 2.1 Create auth app structure
- [ ] Create `apps/auth/__init__.py`
- [ ] Create `apps/auth/apps.py` with AuthConfig
- [ ] Add `apps.auth` to INSTALLED_APPS in settings

### 2.2 Implement unified callback view
- [ ] Create `apps/auth/views.py`
- [ ] Implement `github_callback(request)` that:
  - Validates state parameter
  - Extracts flow type from state
  - Routes to `_handle_onboarding_callback` or `_handle_integration_callback`
- [ ] Implement `_handle_onboarding_callback(request, code)` - extracted from onboarding views
- [ ] Implement `_handle_integration_callback(request, code, team_id)` - extracted from integration views
- [ ] Add rate limiting decorator

### 2.3 Create URL routing
- [ ] Create `apps/auth/urls.py` with `/github/callback/` route
- [ ] Update `tformance/urls.py` to include `path("auth/", include("apps.auth.urls"))`

### 2.4 Write tests
- [ ] Test onboarding flow through unified callback
- [ ] Test integration flow through unified callback
- [ ] Test invalid state handling
- [ ] Test expired state handling
- [ ] Test missing code parameter
- [ ] Test rate limiting

**Acceptance Criteria:**
- Single `/auth/github/callback/` endpoint handles both flows
- Correct routing based on state type
- Proper error handling and user feedback
- Rate limiting in place

---

## Phase 3: Update Connect Views

### 3.1 Update onboarding connect view
- [ ] Modify `apps/onboarding/views.py:github_connect`
- [ ] Change callback URL from `onboarding:github_callback` to `auth:github_callback`
- [ ] Update state creation to use unified `create_oauth_state("onboarding")`

### 3.2 Update integration connect view
- [ ] Modify `apps/integrations/views/github.py:github_connect`
- [ ] Change callback URL from `integrations:github_callback` to `auth:github_callback`
- [ ] Update state creation to use unified `create_oauth_state("integration", team.id)`

### 3.3 Update existing tests
- [ ] Update onboarding tests to expect new callback URL
- [ ] Update integration tests to expect new callback URL

**Acceptance Criteria:**
- Both connect views use `/auth/github/callback/` as redirect_uri
- Existing functionality preserved
- All tests pass

---

## Phase 4: Clean Up and Deploy

### 4.1 Remove old callback endpoints
- [ ] Remove `github_callback` from `apps/onboarding/views.py`
- [ ] Remove `github_callback` from `apps/integrations/views/github.py`
- [ ] Remove old URL patterns from `apps/onboarding/urls.py`
- [ ] Remove old URL patterns from `apps/integrations/urls.py`
- [ ] Remove old state functions from onboarding views

### 4.2 Clean up imports
- [ ] Remove unused imports from onboarding views
- [ ] Remove unused imports from integration views
- [ ] Remove `_verify_onboarding_state`, `_create_onboarding_state` from onboarding

### 4.3 Update documentation
- [ ] Update CLAUDE.md if needed
- [ ] Add comments explaining unified callback pattern

### 4.4 GitHub OAuth App configuration
- [ ] **MANUAL:** Update GitHub OAuth App callback URL to `https://your-domain.com/auth/github/callback/`
- [ ] **MANUAL:** For dev environment, add `https://dev.ianchuk.com/auth/github/callback/`

**Acceptance Criteria:**
- No duplicate callback code
- Single callback URL in GitHub OAuth App
- Clean imports
- All tests pass

---

## Summary

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 | 5 | S |
| Phase 2 | 10 | M |
| Phase 3 | 5 | S |
| Phase 4 | 8 | S |
| **Total** | **28** | **M** |

## Quick Start

To begin implementation:

```bash
# 1. Create the auth app
mkdir -p apps/auth
touch apps/auth/__init__.py

# 2. Run tests to establish baseline
make test ARGS='apps.onboarding apps.integrations.tests.test_github'

# 3. Start with Phase 1 - oauth_state.py
```
