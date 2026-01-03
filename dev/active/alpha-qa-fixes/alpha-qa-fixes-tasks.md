# Alpha QA Fixes - Task Checklist

## Phase 1: P0 Blocker Investigation

### A-006: GitHub Sync Stalls at 0% - COMPLETED

#### Fix Applied
- [x] **1.1** Added timeouts to 12 Celery tasks to prevent API hangs
- [x] **1.2** Tasks now have `soft_time_limit` and `time_limit` parameters
- [x] **1.3** Tests passing (40/40 integration tasks tests)

---

## Phase 2: P1 Critical Fixes

### A-001: Unrealistic Trend Percentages - COMPLETED

#### RED Phase
- [x] **2.1.1** Write test: `test_trend_percentage_capped_at_positive_500`
- [x] **2.1.2** Write test: `test_trend_percentage_capped_at_negative_500`
- [x] **2.1.3** Verify tests fail

#### GREEN Phase
- [x] **2.1.4** Add `MAX_TREND_PERCENTAGE = 500` constant
- [x] **2.1.5** Add cap in `_calculate_change_and_trend()` (~line 2270)
- [x] **2.1.6** Verify all tests pass

#### REFACTOR Phase
- [x] **2.1.7** Run full sparkline test suite (28 tests passed)

---

### A-002: Hide Jira/Slack When Flags Disabled - COMPLETED

#### GREEN Phase
- [x] **2.2.1** Add `_get_onboarding_flags_context()` helper function
- [x] **2.2.2** Add `jira_enabled`, `slack_enabled` to onboarding view contexts
- [x] **2.2.3** Update `templates/onboarding/base.html` stepper with conditionals
- [x] **2.2.4** Update step numbering to be dynamic (using `{% with done_step=... %}`)
- [x] **2.2.5** Update `templates/onboarding/complete.html` Setup Summary
- [x] **2.2.6** Update `templates/onboarding/complete.html` footer text

#### REFACTOR Phase
- [x] **2.2.7** DRY up flag passing with `**_get_onboarding_flags_context(request)`
- [x] **2.2.8** Run full onboarding test suite

---

### A-004: Copilot "Coming Soon" Label - COMPLETED

#### GREEN Phase
- [x] **2.3.1** Update `templates/onboarding/start.html` line 43-46
- [x] **2.3.2** Add "(coming soon)" span with muted styling

---

### A-007: Team Members Shows 0 - COMPLETED

#### Investigation
- [x] **2.4.1** Found bug: `sync_github_members(team)` called with 1 arg, needs 3
- [x] **2.4.2** Two different flows: OAuth vs GitHub App, each needs different handling

#### RED Phase
- [x] **2.4.3** Write test: `test_github_app_callback_queues_member_sync_task`
- [x] **2.4.4** Verify test fails (missing arguments error in logs)

#### GREEN Phase
- [x] **2.4.5** Create new task `sync_github_app_members_task` for GitHub App flow
- [x] **2.4.6** Update `_sync_github_members_after_connection` helper to handle both:
  - GitHubIntegration (OAuth) -> sync_github_members_task
  - GitHubAppInstallation (App) -> sync_github_app_members_task
- [x] **2.4.7** Update onboarding views to use the helper
- [x] **2.4.8** Verify test passes (17/17 GitHub App tests passed)

---

### A-015: Hide API Keys Section - COMPLETED

#### GREEN Phase
- [x] **2.5.1** Comment out api_keys include in `templates/account/profile.html`
- [x] **2.5.2** Added comment explaining why hidden for alpha

---

## Phase 3: P2 UX Improvements

### A-003: Privacy Message Callout - COMPLETED

- [x] **3.1.1** Update `templates/onboarding/start.html` lines 64-75
- [x] **3.1.2** Add callout box with shield icon
- [x] **3.1.3** Added "Privacy First" heading and styled box

---

### A-005: Loader Blank Space - COMPLETED

- [x] **3.2.1** Inspect `templates/onboarding/select_repos.html`
- [x] **3.2.2** Check loader container CSS
- [x] **3.2.3** Fixed by adding proper `.htmx-indicator` CSS in utilities.css
- [x] **3.2.4** Changed from opacity-based to display-based hiding

---

### A-008: Tracked Repos at Top - COMPLETED

#### RED Phase
- [x] **3.3.1** Write test: `test_tracked_repos_appear_first_in_list`
- [x] **3.3.2** Write test: `test_multiple_tracked_repos_sorted_by_updated_at`
- [x] **3.3.3** Verify tests fail

#### GREEN Phase
- [x] **3.3.4** Update repo sorting in `fetch_repos` view (apps/onboarding/views.py:477-491)
- [x] **3.3.5** Verify all 11 repo prioritization tests pass

---

### A-009, A-010: Sync Progress Consistency - COMPLETED

- [x] **3.4.1** Decision: Use bottom-right widget (less intrusive, consistent with onboarding)
- [x] **3.4.2** Updated `templates/web/components/sync_indicator.html` to floating widget pattern
- [x] **3.4.3** Component is already included in app_home.html (dashboard) and repos pages
- [x] **3.4.4** All 19 sync indicator tests pass

---

### A-011: Sync Banner Contrast - COMPLETED

- [x] **3.5.1** Found sync banner template at `web/components/sync_indicator.html`
- [x] **3.5.2** Changed `text-base-content/70` to `opacity-80` for proper contrast
- [x] **3.5.3** Now inherits text color from alert-info component

---

### A-012: Delete Team Button - COMPLETED

- [x] **3.6.1** Updated `templates/teams/manage_team.html` line 85
- [x] **3.6.2** Changed `pg-button-danger` to `btn btn-error`
- [x] **3.6.3** Visual validation complete

---

### A-013: Profile Page Button Styling - COMPLETED

- [x] **3.7.1** Updated `templates/account/components/profile_form.html`
- [x] **3.7.2** Updated `templates/account/components/social/social_accounts.html`
- [x] **3.7.3** Replaced `pg-button-*` with `btn btn-*` classes
- [x] **3.7.4** Visual validation complete

---

### A-016: Delete User Account (New Feature) - COMPLETED

#### RED Phase
- [x] **3.8.1** Write tests in `apps/users/tests/test_delete_account.py`
- [x] **3.8.2** 8 tests: login, post, delete, logout, teams, UI (3)
- [x] **3.8.3** Verify tests fail

#### GREEN Phase
- [x] **3.8.4** Add `delete_account` view in `apps/users/views.py`
- [x] **3.8.5** Add URL pattern in `apps/users/urls.py`
- [x] **3.8.6** Create `templates/account/components/delete_account_modal.html`
- [x] **3.8.7** Add Danger Zone section to `templates/account/profile.html`
- [x] **3.8.8** All 8 tests pass

---

### A-018: Third Party Accounts Styling - COMPLETED

- [x] **3.9.1** Updated `templates/socialaccount/connections.html`
- [x] **3.9.2** Applied DaisyUI styling (btn, radio, form-control classes)
- [x] **3.9.3** Visual validation complete

---

## Phase 4: P3 Polish

### A-014: GitHub Logo Size - COMPLETED

- [x] **4.1.1** Updated `templates/account/components/social/social_accounts.html`
- [x] **4.1.2** Added `w-6 h-6` size constraints to all provider logos
- [x] **4.1.3** Visual validation complete

---

### A-017: GitHub Avatar Import - COMPLETED

#### GREEN Phase
- [x] **4.2.1** Modified `avatar_url` property to check GitHub social account
- [x] **4.2.2** Priority: local avatar > GitHub avatar > Gravatar
- [x] **4.2.3** Created 5 tests in `apps/users/tests/test_avatar.py`
- [x] **4.2.4** All 5 tests pass

---

## Final Verification

- [ ] **5.1** Run full unit test suite: `make test`
- [ ] **5.2** Run E2E smoke tests: `make e2e-smoke`
- [ ] **5.3** Manual QA: Complete onboarding flow
- [ ] **5.4** Manual QA: Check all pages for regressions
- [ ] **5.5** Update backlog.md with completed status
- [ ] **5.6** Commit and push

---

## Progress Summary

| Phase | Total | Completed | Remaining |
|-------|-------|-----------|-----------|
| Phase 1 (P0) | 3 | 3 | 0 |
| Phase 2 (P1) | 40 | 40 | 0 |
| Phase 3 (P2) | 24 | 24 | 0 |
| Phase 4 (P3) | 6 | 6 | 0 |
| Verification | 6 | 0 | 6 |
| **Total** | **79** | **73** | **6** |

---

## Completed Issues

### Session 2026-01-03 (Continued)

| Issue | Description | Solution |
|-------|-------------|----------|
| A-006 | Sync stalls at 0% | Added timeouts to 12 Celery tasks |
| A-005 | Loader blank space | Fixed htmx-indicator CSS to use display:none |
| A-011 | Sync banner contrast | Changed to opacity-80 for proper contrast |
| A-012 | Delete Team button | Updated to btn btn-error |
| A-013 | Profile buttons | Updated to DaisyUI btn classes |
| A-014 | GitHub logo size | Added w-6 h-6 constraints |
| A-018 | Third party accounts | Applied DaisyUI styling |
| A-008 | Tracked repos at top | Sorted by is_tracked then updated_at |
| A-009/A-010 | Sync progress consistency | Unified to bottom-right floating widget |
| A-016 | Delete user account | Added view, modal, Danger Zone section |
| A-017 | GitHub avatar import | Modified avatar_url property to check GitHub |

### Session 2026-01-03 (Initial)

| Issue | Description | Solution |
|-------|-------------|----------|
| A-001 | Trend percentages showing 12096% | Added MAX_TREND_PERCENTAGE=500 cap |
| A-002 | Jira/Slack steps shown when flags disabled | Added conditional rendering in templates |
| A-003 | Privacy message styling | Created callout box with shield icon |
| A-004 | Copilot missing "coming soon" | Added span with muted styling |
| A-007 | Team Members shows 0 | Fixed broken sync call, added new task for GitHub App flow |
| A-015 | API Keys section visible | Commented out include, added explanation |

---

## Remaining Issues

**All 18 issues (A-001 through A-018) are now COMPLETED!**

Only final verification steps remain.

---

*Last Updated: 2026-01-03*
