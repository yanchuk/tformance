# Fix: GitHub App Sync for Personal Accounts

**Last Updated:** 2026-01-18

## Executive Summary

The GitHub App onboarding sync fails for personal accounts because the code assumes all installations are organizations and calls the organization members API (`/orgs/{slug}`), which returns 404 for personal accounts.

**Impact:** Users who install the GitHub App on their personal account (not an organization) cannot complete onboarding - sync gets stuck at step 1 "Members" at 0%.

**Solution:** Check `account_type` field before syncing members. For personal accounts (`account_type="User"`), create a single TeamMember for the account owner instead of calling the org members API.

---

## Current State Analysis

### The Problem Flow

```
1. User installs GitHub App on personal account "yanchuk"
2. Webhook creates GitHubAppInstallation with account_type="User"
3. Onboarding pipeline triggers sync_github_app_members_task
4. Task extracts: org_slug = installation.account_login ("yanchuk")
5. Calls: get_organization_members(token, "yanchuk")
6. GitHub API: GET /orgs/yanchuk → 404 Not Found
7. Task fails and retries → eventually fails permanently
8. Sync stuck at step 1 "Members" at 0%
```

### Error from Production Logs

```
GitHub App member sync failed for yanchuk: Organization not found: 404 -
{'message': 'Not Found', 'documentation_url': 'https://docs.github.com/rest/orgs/orgs#get-an-organization'}
```

### Current Code (Broken)

**`apps/integrations/_task_modules/github_sync.py:785-801`**
```python
org_slug = installation.account_login  # "yanchuk" - assumes this is an org
# ...
result = sync_github_members(team, access_token, org_slug)  # Fails for personal accounts
```

---

## Proposed Future State

### Solution Architecture

```
sync_github_app_members_task
    │
    ├─ IF account_type == "User"
    │   └─ sync_single_user_as_member()
    │       └─ get_user_details() via /users/{username}
    │       └─ Create single TeamMember
    │
    └─ ELSE (account_type == "Organization")
        └─ sync_github_members() (existing)
            └─ get_organization_members() via /orgs/{slug}/members
            └─ Create TeamMember for each org member
```

### Key Design Decisions

1. **Separate function for personal accounts** - Cleaner than modifying existing `sync_github_members()`
2. **Reuse existing `get_user_details()`** - Already exists in codebase
3. **Match existing SyncResult format** - Returns `{"created": int, "updated": int, "unchanged": int, "failed": int}`
4. **Add error handling** - Gracefully handle API failures

---

## Implementation Phases

### Phase 1: Add `sync_single_user_as_member()` Function (TDD)

**File:** `apps/integrations/services/member_sync.py`

1. Write failing tests for the new function
2. Implement minimal code to pass tests
3. Refactor for clarity

**Tests to write:**
- Creates TeamMember for new user
- Updates existing member if username changed
- Returns unchanged when no changes
- Handles API error gracefully (returns failed=1)
- Handles private email (None → empty string)

### Phase 2: Update Task to Route Based on Account Type (TDD)

**File:** `apps/integrations/_task_modules/github_sync.py`

1. Write failing test for task routing
2. Add account_type check to task
3. Verify existing org sync still works

**Tests to write:**
- Task uses `sync_single_user_as_member` when `account_type="User"`
- Task uses `sync_github_members` when `account_type="Organization"`

### Phase 3: Deploy and Verify

1. Deploy to Heroku
2. Test with new personal account installation
3. Manually re-sync any stuck installations

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Break existing org sync | Low | High | Existing tests + new routing test |
| API rate limiting | Low | Medium | Error handling returns failed=1 |
| Stuck installations don't auto-recover | Medium | Low | Manual re-trigger documented |

### Known Limitations

**Personal accounts with collaborators:** PRs from collaborators on personal repos won't be attributed to any team member since we only create the account owner as a member. This is acceptable for MVP - users who need full attribution should use an organization.

---

## Success Metrics

1. **Functional:** Personal account sync completes all 5 steps
2. **Data:** TeamMember created for personal account owner
3. **Logs:** No "Organization not found" errors for personal accounts
4. **Tests:** All new tests pass, no regression in existing tests
