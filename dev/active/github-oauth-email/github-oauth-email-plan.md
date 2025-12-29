# GitHub OAuth Email Fetching Implementation Plan

**Last Updated: 2025-12-29**

## Executive Summary

Implement proper GitHub OAuth email fetching to ensure user accounts have real email addresses instead of placeholder emails (`username@github.placeholder`). This is critical for:
- Email notifications
- Account recovery
- User communication
- Future email-based features

## Current State Analysis

### Problem
When users authenticate via GitHub OAuth, if their email is private, the `/user` endpoint returns `null` for the email field. The current code creates a placeholder email:
```python
email=github_email or f"{github_login_name}@github.placeholder"
```

### Root Cause
1. **Missing OAuth scope**: The login flow uses `user:email` scope correctly, but the integration flow (`GITHUB_OAUTH_SCOPES`) only has `read:user` which doesn't include access to private emails
2. **Incomplete email fetching**: The code only checks `github_user.get("email")` from the `/user` endpoint, but doesn't call `/user/emails` to fetch private emails

### Current OAuth Flows
| Flow | Scope | File | Issue |
|------|-------|------|-------|
| Login | `user:email` | `apps/auth/views.py:60` | Correct scope but no `/user/emails` call |
| Integration | `GITHUB_OAUTH_SCOPES` (missing `user:email`) | `github_oauth.py:28-35` | Missing scope |

## Proposed Future State

### Solution Overview
1. Add `user:email` scope to `GITHUB_OAUTH_SCOPES` in `github_oauth.py`
2. Create `get_user_primary_email()` function that calls GitHub's `/user/emails` endpoint
3. Update `get_authenticated_user()` to use `get_user_primary_email()` when email is None
4. Update login callback to utilize the enhanced email fetching

### GitHub API Reference
- **Endpoint**: `GET /user/emails`
- **Scope Required**: `user:email`
- **Response**: Array of email objects with `email`, `primary`, `verified` fields
- **Selection Logic**: Return the primary verified email, fallback to first verified email

## Implementation Phases

### Phase 1: Add OAuth Scope (Effort: S)
Add `user:email` to `GITHUB_OAUTH_SCOPES` constant.

**Files Modified:**
- `apps/integrations/services/github_oauth.py`

**Acceptance Criteria:**
- [x] `user:email` scope included in `GITHUB_OAUTH_SCOPES`
- [x] Existing tests updated to verify scope presence

### Phase 2: Implement Email Fetching (Effort: M)
Create function to fetch user's primary email from `/user/emails` endpoint.

**Files Modified:**
- `apps/integrations/services/github_oauth.py`

**Acceptance Criteria:**
- [ ] `get_user_primary_email()` function implemented
- [ ] Returns primary verified email when available
- [ ] Falls back to first verified email
- [ ] Returns None if no verified emails
- [ ] Handles API errors gracefully

### Phase 3: Update Auth Callback (Effort: S)
Integrate email fetching into login flow.

**Files Modified:**
- `apps/auth/views.py`

**Acceptance Criteria:**
- [ ] Login callback calls `get_user_primary_email()` when email is None
- [ ] Placeholder email only used as absolute last resort
- [ ] Existing users with placeholder emails can be updated on next login

### Phase 4: Tests (Effort: M)
Add comprehensive tests for email fetching.

**Files Modified:**
- `apps/integrations/tests/test_github_oauth.py`

**Acceptance Criteria:**
- [ ] Test `get_user_primary_email()` with various responses
- [ ] Test primary email selection logic
- [ ] Test fallback behavior
- [ ] Test error handling
- [ ] Test scope configuration

## Detailed Tasks

### Task 1: Update GITHUB_OAUTH_SCOPES
**Priority**: P0 | **Effort**: S | **Dependencies**: None

```python
GITHUB_OAUTH_SCOPES = " ".join([
    "read:org",
    "repo",
    "read:user",
    "user:email",  # NEW - Access user email addresses
    "manage_billing:copilot",
])
```

### Task 2: Implement get_user_primary_email()
**Priority**: P0 | **Effort**: M | **Dependencies**: Task 1

```python
def get_user_primary_email(access_token: str) -> str | None:
    """Get user's primary verified email from GitHub.

    Calls /user/emails endpoint to fetch all emails including private ones.
    Returns the primary verified email, or first verified email as fallback.

    Args:
        access_token: GitHub access token with user:email scope

    Returns:
        Primary verified email address or None if unavailable
    """
```

### Task 3: Update get_authenticated_user()
**Priority**: P1 | **Effort**: S | **Dependencies**: Task 2

Enhance to fetch email via `/user/emails` when public email is None.

### Task 4: Update _handle_login_callback()
**Priority**: P1 | **Effort**: S | **Dependencies**: Task 3

Use enhanced email fetching in login flow.

### Task 5: Add Tests
**Priority**: P1 | **Effort**: M | **Dependencies**: Task 2, 3, 4

Add tests for:
- `get_user_primary_email()` success cases
- `get_user_primary_email()` edge cases (no verified, no primary)
- `get_user_primary_email()` error handling
- Scope configuration verification
- Integration with auth callback

### Task 6: Manual Verification
**Priority**: P2 | **Effort**: S | **Dependencies**: Task 1-5

Delete test user and re-test GitHub OAuth flow.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Users need to re-authenticate for new scope | Medium | Low | New scope only affects new OAuth flows |
| GitHub API rate limiting | Low | Medium | Use PyGithub which handles rate limits |
| No verified emails available | Low | Low | Keep placeholder fallback as last resort |
| Breaking existing users | Low | Medium | Don't modify existing users without re-auth |

## Success Metrics

1. **Primary**: New GitHub OAuth users have real email addresses
2. **Secondary**: Zero placeholder emails for users who have verified GitHub emails
3. **Monitoring**: Log when placeholder fallback is used for debugging

## Required Resources

### Dependencies
- PyGithub library (already installed)
- `user:email` OAuth scope (no additional GitHub App configuration needed)

### Documentation
- [GitHub OAuth Scopes](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)
- [GitHub User Emails API](https://docs.github.com/en/rest/users/emails)
- [PyGithub AuthenticatedUser](https://pygithub.readthedocs.io/en/latest/github_objects/AuthenticatedUser.html)
