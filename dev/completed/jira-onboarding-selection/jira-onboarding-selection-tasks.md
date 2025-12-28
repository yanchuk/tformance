# Tasks: Jira Project Selection in Onboarding

**Last Updated: 2025-12-28**
**Status: COMPLETED**

## Phase 1: OAuth State Infrastructure (Effort: S) ✅

- [x] **1.1** Add `FLOW_TYPE_JIRA_ONBOARDING` and `FLOW_TYPE_JIRA_INTEGRATION` constants to `apps/auth/oauth_state.py`
- [x] **1.2** Add `jira_callback` view to `apps/auth/views.py`
  - Exchange code for token
  - Create/update `IntegrationCredential`
  - Get accessible Jira sites
  - Create `JiraIntegration`
  - Route based on flow type (onboarding vs integration)
- [x] **1.3** Add URL route in `apps/auth/urls.py`: `path("jira/callback/", ...)`
- [x] **1.4** Write tests for unified Jira callback (`apps/auth/tests/test_jira_callback.py`)

## Phase 2: Enable Jira Connection in Onboarding (Effort: S) ✅

- [x] **2.1** Update `apps/onboarding/views.py:connect_jira`:
  - Build Jira OAuth URL with `FLOW_TYPE_JIRA_ONBOARDING` state
  - Redirect to Atlassian OAuth when `?action=connect`
- [x] **2.2** Update `templates/onboarding/connect_jira.html`:
  - Enable "Connect Jira" button with `?action=connect` parameter
  - Wire form action to POST for skip
- [x] **2.3** Test that clicking "Connect Jira" redirects to Atlassian

## Phase 3: Implement Project Selection View (Effort: M) ✅

- [x] **3.1** Add `select_jira_projects` view to `apps/onboarding/views.py`:
  - GET: Fetch projects via `jira_client.get_accessible_projects()`
  - GET: Mark which are already tracked
  - POST: Create `TrackedJiraProject` for selected projects
  - POST: Redirect to `onboarding:connect_slack`
- [x] **3.2** Add URL route in `apps/onboarding/urls.py`:
  - `path("jira/projects/", views.select_jira_projects, name="select_jira_projects")`
- [x] **3.3** Handle edge cases:
  - No projects returned (show message, allow skip)
  - User already has Jira connected (redirect to project selection)

## Phase 4: Create Project Selection Template (Effort: M) ✅

- [x] **4.1** Create `templates/onboarding/select_jira_projects.html`:
  - Extend `onboarding/base.html`
  - Card layout matching other onboarding steps
  - List of projects with checkboxes
  - Project key, name, type displayed
- [x] **4.2** Implement "Select All" / "Deselect All" with Alpine.js:
  - Button at top toggles all project checkboxes
  - Shows count of selected projects
- [x] **4.3** Add styling:
  - Hover states on project rows
  - Visual distinction for selection
  - Proper spacing and alignment
- [x] **4.4** Add navigation:
  - "← Back" button to connect_jira step
  - "Continue →" button submits form

## Phase 5: Testing (Effort: M) ✅

- [x] **5.1** Add OAuth state tests (`apps/auth/tests/test_oauth_state.py`):
  - 5 new tests for Jira flow types
- [x] **5.2** Create `apps/auth/tests/test_jira_callback.py` (11 tests):
  - Test callback with onboarding flow redirects correctly
  - Test callback with integration flow redirects correctly
  - Test error handling (invalid state, API errors, missing code)
  - Test token exchange errors
  - Test no Jira sites found
- [x] **5.3** Add tests to `apps/onboarding/tests/test_views.py` (13 tests):
  - `ConnectJiraViewTests` (6 tests): auth redirect, skip, OAuth initiation
  - `SelectJiraProjectsViewTests` (7 tests): auth, project display, POST creates records
- [x] **5.4** Add E2E tests (`tests/e2e/onboarding.spec.ts`) (6 tests):
  - Test Jira connect page UI elements
  - Test Connect button links to OAuth
  - Test Jira projects page UI elements
  - Test authentication requirements
- [x] **5.5** Run full test suite: All 73 auth/onboarding tests pass

## Phase 6: Polish (Effort: S) ✅

- [x] **6.1** Fix variable shadowing bug (`_` → `_created`)
- [x] **6.2** Fix `JIRA_AUTH_URL` constant reference
- [x] **6.3** Remove invalid `project_type` field from view
- [x] **6.4** Code passes ruff lint checks

## Verification Checklist ✅

- [x] User can click "Connect Jira" and reach Atlassian OAuth
- [x] After OAuth, user sees project selection screen
- [x] "Select All" toggles all checkboxes
- [x] Submitting creates `TrackedJiraProject` records in DB
- [x] User can skip without selecting any projects
- [x] Flow continues to Slack step
- [x] All tests pass (`make test` - 73 tests)
- [x] No ruff errors (`make ruff`)
- [x] E2E tests pass (6 Jira-specific tests)

## Commits

1. `0599d5a` - Add Jira onboarding with project selection and unified OAuth
2. `dee410a` - Add tests and bug fixes (variable shadowing, field errors)
3. `5e2bf00` - Add comprehensive E2E tests for Jira onboarding pages
