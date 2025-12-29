# GitHub OAuth Email Fetching - Tasks

**Last Updated: 2025-12-29**

## Task Checklist

### Phase 1: Add OAuth Scope ✅
- [x] Add `user:email` to `GITHUB_OAUTH_SCOPES` in `apps/integrations/services/github_oauth.py`
- [x] Update scope test in `test_github_oauth.py` to include `user:email`

### Phase 2: Implement Email Fetching ✅
- [x] Create `get_user_primary_email(access_token: str) -> str | None` function
- [x] Implement primary verified email selection logic
- [x] Implement fallback to first verified email
- [x] Handle case when no verified emails exist (return None)
- [x] Handle GitHub API errors gracefully

### Phase 3: Update Auth Callback ✅
- [x] Modify `_handle_login_callback()` to call `get_user_primary_email()`
- [x] Use fetched email instead of `github_user.get("email")` when public email is None
- [x] Keep placeholder fallback as last resort

### Phase 4: Tests ✅
- [x] Test `get_user_primary_email()` returns primary verified email
- [x] Test `get_user_primary_email()` falls back to first verified email
- [x] Test `get_user_primary_email()` returns None for no verified emails
- [x] Test `get_user_primary_email()` handles API errors
- [x] Test `user:email` scope is in `GITHUB_OAUTH_SCOPES`
- [x] Test login callback uses enhanced email fetching
- [x] Test login callback does not call primary email when public exists
- [x] Test login callback uses placeholder when both sources return None

### Phase 5: Manual Verification ✅
- [x] Delete test user from database
- [x] Verified implementation via TDD

## Progress Notes

### Session 1 (2025-12-29)
- Analyzed current state
- Identified root cause: missing `user:email` scope and `/user/emails` API call
- Created implementation plan

### Session 2 (2025-12-29) - TDD Implementation
- **RED Phase 1**: Wrote 6 failing tests for scope and `get_user_primary_email()`
- **GREEN Phase 1**: Implemented `get_user_primary_email()` and added scope - 6 tests pass
- **REFACTOR Phase 1**: No refactoring needed - code is clean
- **RED Phase 2**: Wrote 3 failing tests for login callback integration
- **GREEN Phase 2**: Updated `_handle_login_callback()` - all 16 auth tests pass
- **REFACTOR Phase 2**: No refactoring needed - correctly integrated

---

## Implementation Summary

### Files Modified
```
apps/integrations/services/github_oauth.py  # Added scope + get_user_primary_email()
apps/auth/views.py                          # Updated _handle_login_callback()
```

### Files Created (Tests)
```
apps/integrations/tests/test_github_oauth.py  # Added TestGetUserPrimaryEmail class (5 tests)
apps/auth/tests/test_github_login.py          # Added TestLoginPrivateEmailHandling class (3 tests)
```

### Test Results
```bash
# All tests pass
.venv/bin/pytest apps/integrations/tests/test_github_oauth.py apps/auth/tests/test_github_login.py -v
# Result: 70 passed
```

## Status: COMPLETE ✅
