# Unified Login OAuth - Tasks

**Last Updated:** 2025-12-29

## Task Checklist

### Phase 1: TDD RED - Write Failing Tests
- [ ] **Task 1.1** - Create test file `apps/auth/tests/test_github_login.py`
- [ ] **Task 1.2** - Test: `github_login` view exists and redirects to GitHub
- [ ] **Task 1.3** - Test: OAuth state has `FLOW_TYPE_LOGIN` type
- [ ] **Task 1.4** - Test: `github_callback` handles login flow type
- [ ] **Task 1.5** - Test: New user created from GitHub profile
- [ ] **Task 1.6** - Test: Existing user matched by GitHub ID
- [ ] **Task 1.7** - Test: User redirected to onboarding if no team
- [ ] **Task 1.8** - Test: User redirected to dashboard if has team
- [ ] **Task 1.9** - Verify tests fail

### Phase 2: TDD GREEN - Implement Minimal Code
- [ ] **Task 2.1** - Add `FLOW_TYPE_LOGIN` to `oauth_state.py`
- [ ] **Task 2.2** - Add `github_login` view to `views.py`
- [ ] **Task 2.3** - Add URL pattern for `/github/login/`
- [ ] **Task 2.4** - Add `_handle_login_callback` function
- [ ] **Task 2.5** - Implement user creation/matching logic
- [ ] **Task 2.6** - Verify tests pass

### Phase 3: TDD REFACTOR - Code Quality
- [ ] **Task 3.1** - Review code for clarity
- [ ] **Task 3.2** - Run full test suite
- [ ] **Task 3.3** - Run linter

### Phase 4: Template & Integration
- [ ] **Task 4.1** - Update `social_buttons.html` to use new URL
- [ ] **Task 4.2** - Test login flow end-to-end on dev2.ianchuk.com
- [ ] **Task 4.3** - Verify integration flow still works

### Phase 5: Finalize
- [ ] **Task 5.1** - Move docs to completed
- [ ] **Task 5.2** - Commit changes

## Progress Summary

| Phase | Status | Tasks Completed |
|-------|--------|-----------------|
| Phase 1: RED | Not Started | 0/9 |
| Phase 2: GREEN | Not Started | 0/6 |
| Phase 3: REFACTOR | Not Started | 0/3 |
| Phase 4: Integration | Not Started | 0/3 |
| Phase 5: Finalize | Not Started | 0/2 |

**Total Progress: 0/23 tasks completed**

## Dependencies

```
Phase 2 depends on: Phase 1 complete
Phase 3 depends on: Phase 2 complete
Phase 4 depends on: Phase 3 complete
Phase 5 depends on: Phase 4 complete
```

## Technical Notes

### OAuth Scopes
- **Login:** `user:email` (minimal - just authentication)
- **Integration:** `read:org repo read:user manage_billing:copilot` (full access)

### User Matching Priority
1. Match by GitHub ID (SocialAccount)
2. Match by email
3. Create new user

### Redirect Logic
```python
if user.teams.exists():
    return redirect("web:home")  # Dashboard
else:
    return redirect("onboarding:start")  # Onboarding
```

## Blockers

None identified yet.

## Related Tasks

- Completed: `github-ux-improvement` - Shows different messaging for GitHub-authenticated users
- Reference: `unified-github-oauth` - Previous work unifying integration callbacks
- Reference: `github-only-auth` - Auth mode configuration
