# Unified Login OAuth - Context

**Last Updated:** 2025-12-29

## Current Implementation State

**Status:** NOT STARTED - Planning complete, ready for TDD implementation

### Clarification

The unified callback (`/auth/github/callback/`) was implemented previously but ONLY for:
- `FLOW_TYPE_ONBOARDING` - New user creating team from GitHub org
- `FLOW_TYPE_INTEGRATION` - Existing team adding GitHub integration

The **LOGIN flow has NOT been touched** - it still uses django-allauth which has its own callback URL (`/accounts/github/login/callback/`).

This is why we need to add `FLOW_TYPE_LOGIN` to the unified callback.

### Background

User deployed to `dev2.ianchuk.com` and set GitHub OAuth callback to:
```
https://dev2.ianchuk.com/auth/github/callback/
```

This works for the integration flow but breaks the login flow because:
- Integration uses `/auth/github/callback/` ✅
- Login (allauth) uses `/accounts/github/login/callback/` ❌

GitHub OAuth Apps only allow ONE callback URL.

## Key Files

### Files to Modify

| File | Current State | Required Change |
|------|--------------|-----------------|
| `apps/auth/oauth_state.py` | Has 6 flow types | Add `FLOW_TYPE_LOGIN` |
| `apps/auth/views.py` | Handles onboarding/integration | Add login handler |
| `apps/auth/urls.py` | Has `/github/callback/` | Add `/github/login/` |
| `templates/account/components/social/social_buttons.html` | Uses allauth URL | Use our URL |

### Reference Files

| File | Purpose |
|------|---------|
| `apps/auth/oauth_state.py` | OAuth state creation/verification |
| `apps/integrations/services/github_oauth.py` | GitHub API helpers |
| `tformance/settings.py:342-353` | GitHub OAuth config |

## Key Decisions Made

1. **Bypass allauth for GitHub login** - Create our own login flow instead of customizing allauth
2. **Minimal scopes for login** - Use `user:email` scope only (not repo access)
3. **User matching** - Match by GitHub ID first, then email
4. **Redirect logic** - Go to onboarding if no team, dashboard if has team

## Architecture Context

### Current OAuth Flow Types (oauth_state.py:20-40)
```python
FLOW_TYPE_ONBOARDING = "onboarding"      # New user, create team
FLOW_TYPE_INTEGRATION = "integration"    # Existing team, add GitHub
FLOW_TYPE_JIRA_ONBOARDING = "jira_onboarding"
FLOW_TYPE_JIRA_INTEGRATION = "jira_integration"
FLOW_TYPE_SLACK_ONBOARDING = "slack_onboarding"
FLOW_TYPE_SLACK_INTEGRATION = "slack_integration"
```

### Proposed Addition
```python
FLOW_TYPE_LOGIN = "login"  # User authentication only
```

### Callback Handler Pattern (views.py:54-155)
```python
def github_callback(request):
    # Verify state
    state_data = verify_oauth_state(state)

    # Route based on flow type
    if state_data["type"] == FLOW_TYPE_ONBOARDING:
        return _handle_onboarding_callback(...)
    elif state_data["type"] == FLOW_TYPE_INTEGRATION:
        return _handle_integration_callback(...)
    # Add: elif state_data["type"] == FLOW_TYPE_LOGIN:
    #         return _handle_login_callback(...)
```

## Session Work Summary

### Completed This Session
1. ✅ TDD implementation of GitHub UX improvement (has_github_social)
   - Tests: `apps/onboarding/tests/test_github_ux_messaging.py` (8 tests)
   - View: Added `has_github_social` context to `onboarding_start`
   - Template: Conditional messaging in `start.html`

2. ✅ Investigated OAuth callback issue
   - Identified that GitHub OAuth Apps only allow ONE callback URL
   - Found existing `unified-github-oauth` docs showing previous work
   - Determined solution: add login flow to unified callback

### Not Yet Started
- Implementing unified login OAuth (this task)

## Next Immediate Steps

1. **TDD RED:** Write failing tests for login flow
   - Test `github_login` view initiates OAuth correctly
   - Test `github_callback` handles `FLOW_TYPE_LOGIN`
   - Test user creation/matching logic
   - Test redirect logic (onboarding vs dashboard)

2. **TDD GREEN:** Implement minimal code
   - Add `FLOW_TYPE_LOGIN` to oauth_state.py
   - Add `github_login` view
   - Add login handler to callback
   - Update URL patterns

3. **TDD REFACTOR:** Clean up and verify

4. **Template Update:** Change social button URL

## Commands to Run on Restart

```bash
# Verify current tests pass
.venv/bin/pytest apps/auth/tests/ -v

# After implementation, run:
.venv/bin/pytest apps/auth/tests/test_github_login.py -v
.venv/bin/pytest apps/onboarding/tests/ -v

# Check for regressions
make test
```

## Uncommitted Changes

Check git status - there may be uncommitted changes from:
1. GitHub UX improvement (test file + view + template)
2. Dev docs for this task

```bash
git status
git diff --name-only
```
