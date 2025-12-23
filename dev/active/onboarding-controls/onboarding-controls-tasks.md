# Onboarding Controls Tasks

**Last Updated: 2025-12-22**

## Task Checklist - ALL COMPLETE

### Phase 1: Navigation Controls

- [x] **Task 1.1**: Add logout button to onboarding base template
  - File: `templates/onboarding/base.html`
  - Added logout button next to user email in nav
  - Uses `app-btn-ghost` styling with `fa-right-from-bracket` icon
  - Includes `aria-label` for accessibility
  - Links to `{% url 'account_logout' %}`

- [x] **Task 1.2**: Add skip control to start page
  - File: `templates/onboarding/start.html`
  - Added "Skip for now" link with new `/onboarding/skip/` endpoint
  - Creates team without GitHub and redirects to limited dashboard
  - User can connect GitHub later from Integrations

### Phase 2: Skip Onboarding Backend

- [x] **Task 2.1**: Create skip_onboarding view
  - File: `apps/onboarding/views.py`
  - Creates team using email prefix (e.g., "user's Team")
  - Adds user as admin
  - Redirects to dashboard with success message
  - Clears onboarding session data

- [x] **Task 2.2**: Add URL pattern for skip
  - File: `apps/onboarding/urls.py`
  - Added `path("skip/", views.skip_onboarding, name="skip")`

### Phase 3: Value Messaging

- [x] **Task 3.1**: Update GitHub start page with correct scopes
  - Organization members → `read:org` scope
  - Pull requests & reviews → `repo` scope
  - Copilot usage metrics → `manage_billing:copilot` scope

- [x] **Task 3.2**: Add privacy statement
  - "We never see your code — only PR metadata like titles, timestamps, and review counts."

- [x] **Task 3.3**: Update Jira page with value messaging
  - Sprint velocity, issue cycle time, PR-to-issue linking

- [x] **Task 3.4**: Update Slack page with value messaging
  - PR surveys, weekly leaderboards, higher response rates

- [x] **Task 3.5**: Update select_repos page with value messaging
  - Focus on what matters, reduce noise

### Phase 4: Tests

- [x] **Task 4.1**: Unit tests for skip_onboarding view
  - File: `apps/onboarding/tests/test_views.py`
  - 4 new tests: auth required, redirect if team exists, creates team, user is admin

- [x] **Task 4.2**: E2E tests for onboarding controls
  - File: `tests/e2e/onboarding.spec.ts`
  - 5 tests: logout visibility, logout functionality, logout href, skip redirect, skip auth

## Test Results

- **Unit Tests**: 9 passed (4 new for skip_onboarding)
- **E2E Tests**: 15 passed, 1 skipped
- **No regressions**

## Files Modified

| File | Changes |
|------|---------|
| `apps/onboarding/views.py` | Added `skip_onboarding` view |
| `apps/onboarding/urls.py` | Added `/skip/` URL pattern |
| `apps/onboarding/tests/test_views.py` | Added 4 unit tests for skip |
| `templates/onboarding/base.html` | Added logout button to nav |
| `templates/onboarding/start.html` | Added skip control + value messaging + privacy |
| `templates/onboarding/select_repos.html` | Added value messaging |
| `templates/onboarding/connect_jira.html` | Added value messaging |
| `templates/onboarding/connect_slack.html` | Added value messaging |
| `tests/e2e/onboarding.spec.ts` | Updated and added 5 E2E tests |

## Implementation Summary

### Skip Flow
1. User on `/onboarding/` sees "Skip for now" link
2. Clicking skip calls `/onboarding/skip/`
3. View creates team using email prefix (e.g., "john's Team")
4. User becomes admin of the team
5. Redirected to dashboard with message: "Connect GitHub from Integrations to unlock all features"
6. Dashboard shows setup wizard for users without integrations

### Logout Flow
1. Logout button visible in onboarding nav bar on all pages
2. Clicking logs user out via Django allauth
3. User redirected to home page

### Value Messaging Structure
Each onboarding step now shows:
- What data we access (with correct OAuth scope)
- Why we need it (value to CTO)
- Privacy assurances where appropriate
