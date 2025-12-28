# Tasks: Jira Project Selection in Onboarding

**Last Updated: 2025-12-28**

## Phase 1: OAuth State Infrastructure (Effort: S)

- [ ] **1.1** Add `FLOW_TYPE_JIRA_ONBOARDING` constant to `apps/auth/oauth_state.py`
- [ ] **1.2** Add `jira_callback` view to `apps/auth/views.py`
  - Exchange code for token
  - Create/update `IntegrationCredential`
  - Get accessible Jira sites
  - Create `JiraIntegration`
  - Route based on flow type (onboarding vs integration)
- [ ] **1.3** Add URL route in `apps/auth/urls.py`: `path("jira/callback/", ...)`
- [ ] **1.4** Write tests for unified Jira callback (`apps/auth/tests/test_jira_callback.py`)

## Phase 2: Enable Jira Connection in Onboarding (Effort: S)

- [ ] **2.1** Update `apps/onboarding/views.py:connect_jira`:
  - Remove placeholder logic
  - Build Jira OAuth URL with `FLOW_TYPE_JIRA_ONBOARDING` state
  - Redirect to Atlassian OAuth
- [ ] **2.2** Update `templates/onboarding/connect_jira.html`:
  - Remove "Coming Soon" badge
  - Enable "Connect Jira" button
  - Wire form action to POST
- [ ] **2.3** Test that clicking "Connect Jira" redirects to Atlassian

## Phase 3: Implement Project Selection View (Effort: M)

- [ ] **3.1** Add `select_jira_projects` view to `apps/onboarding/views.py`:
  - GET: Fetch projects via `jira_client.get_accessible_projects()`
  - GET: Mark which are already tracked
  - POST: Create `TrackedJiraProject` for selected projects
  - POST: Redirect to `onboarding:connect_slack`
- [ ] **3.2** Add URL route in `apps/onboarding/urls.py`:
  - `path("jira/projects/", views.select_jira_projects, name="select_jira_projects")`
- [ ] **3.3** Handle edge cases:
  - No projects returned (show message, allow skip)
  - Token expired (use `ensure_valid_jira_token()`)
  - User navigates back (handle existing selections)

## Phase 4: Create Project Selection Template (Effort: M)

- [ ] **4.1** Create `templates/onboarding/select_jira_projects.html`:
  - Extend `onboarding/base.html`
  - Card layout matching other onboarding steps
  - List of projects with checkboxes
  - Project key, name, type displayed
- [ ] **4.2** Implement "Select All" / "Deselect All" with Alpine.js:
  - Checkbox at top toggles all project checkboxes
  - Individual unchecks update "Select All" state
- [ ] **4.3** Add styling:
  - Hover states on project rows
  - Visual distinction between selected/unselected
  - Proper spacing and alignment
- [ ] **4.4** Add navigation:
  - "← Back" button to connect_jira step
  - "Continue →" button submits form
  - "Skip" link to connect_slack

## Phase 5: Testing (Effort: M)

- [ ] **5.1** Create `apps/onboarding/tests/test_jira_onboarding.py`:
  - Test `connect_jira` initiates OAuth
  - Test `select_jira_projects` GET displays projects
  - Test `select_jira_projects` POST creates TrackedJiraProject
  - Test "Select All" creates all projects
  - Test empty selection allowed (skip)
- [ ] **5.2** Create `apps/auth/tests/test_jira_callback.py`:
  - Test callback with onboarding flow redirects correctly
  - Test callback with integration flow redirects correctly
  - Test error handling (invalid state, API errors)
- [ ] **5.3** Run full test suite: `make test`
- [ ] **5.4** Manual E2E testing:
  - Complete full onboarding with Jira
  - Verify projects appear in integrations settings
  - Verify skip flow works

## Phase 6: Polish (Effort: S)

- [ ] **6.1** Add loading state while fetching projects
- [ ] **6.2** Add error handling UI (toast messages)
- [ ] **6.3** Ensure mobile responsiveness
- [ ] **6.4** Update PRD/docs if needed

## Verification Checklist

After implementation, verify:
- [ ] User can click "Connect Jira" and reach Atlassian OAuth
- [ ] After OAuth, user sees project selection screen
- [ ] "Select All" toggles all checkboxes
- [ ] Submitting creates `TrackedJiraProject` records in DB
- [ ] User can skip without selecting any projects
- [ ] Flow continues to Slack step
- [ ] All tests pass (`make test`)
- [ ] No ruff errors (`make ruff`)

## Notes

- Follow TDD: Write tests first, then implement
- Use `jira-python` library (already installed) for API calls
- Reuse existing `jira_client.get_accessible_projects()` service
- OAuth credentials must be configured in `.env` for local testing
