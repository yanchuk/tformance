# Context: Jira Project Selection in Onboarding

**Last Updated: 2025-12-28**
**Status: COMPLETED**

## Implementation Summary

This feature enables users to connect Jira during onboarding and select which Jira projects to track. The implementation follows the unified OAuth callback pattern established for GitHub.

## Files Modified

| File | Changes |
|------|---------|
| `apps/auth/oauth_state.py` | Added `FLOW_TYPE_JIRA_ONBOARDING` and `FLOW_TYPE_JIRA_INTEGRATION` constants |
| `apps/auth/urls.py` | Added `jira/callback/` URL route |
| `apps/auth/views.py` | Added `jira_callback` view (~150 lines), helper functions `_handle_jira_onboarding_callback` and `_handle_jira_integration_callback` |
| `apps/onboarding/urls.py` | Added `jira/projects/` URL route |
| `apps/onboarding/views.py` | Updated `connect_jira` (OAuth initiation), added `select_jira_projects` view (~95 lines) |
| `templates/onboarding/connect_jira.html` | Enabled Connect button with `?action=connect` |

## Files Created

| File | Purpose |
|------|---------|
| `templates/onboarding/select_jira_projects.html` | Project selection UI with Alpine.js Select All |
| `apps/auth/tests/test_jira_callback.py` | 11 tests for Jira callback |

## Files Updated (Tests)

| File | Changes |
|------|---------|
| `apps/auth/tests/test_oauth_state.py` | Added 5 tests for Jira flow types |
| `apps/onboarding/tests/test_views.py` | Added 13 tests (ConnectJiraViewTests, SelectJiraProjectsViewTests) |
| `tests/e2e/onboarding.spec.ts` | Added 4 new E2E tests for Jira UI elements |

## Key Decisions Made

1. **Unified OAuth Callback** - Jira callback uses same pattern as GitHub (`apps/auth/views.py`) with flow type routing
2. **State Management** - Uses `create_oauth_state(FLOW_TYPE_JIRA_ONBOARDING, team_id=team.id)` for CSRF protection
3. **Alpine.js for Select All** - Follows `select_repos.html` pattern for consistent UX
4. **No `project_type` Field** - `TrackedJiraProject` model doesn't have this field, removed from view

## Bugs Fixed

1. **Variable Shadowing** - Renamed `_` to `_created` in `update_or_create()` calls to avoid shadowing `gettext_lazy`
2. **Constant Name** - Changed `JIRA_OAUTH_AUTHORIZE_URL` to `JIRA_AUTH_URL` (correct name from `jira_oauth.py`)
3. **Invalid Field** - Removed `project_type` from `TrackedJiraProject.objects.get_or_create()` defaults

## OAuth Flow Implemented

```
1. User clicks "Connect Jira" button on /onboarding/jira/
2. connect_jira() creates state with FLOW_TYPE_JIRA_ONBOARDING
3. User redirects to Atlassian OAuth (auth.atlassian.com)
4. Atlassian redirects to /auth/jira/callback/ with code
5. jira_callback() exchanges code for tokens
6. Creates IntegrationCredential and JiraIntegration
7. Redirects to /onboarding/jira/projects/
8. select_jira_projects() displays projects with checkboxes
9. User selects projects and clicks Continue
10. TrackedJiraProject records created
11. Redirects to /onboarding/slack/
```

## Test Coverage

| Test File | Tests | Coverage |
|-----------|-------|----------|
| `apps/auth/tests/test_oauth_state.py` | 20 total (5 new Jira) | OAuth state creation/verification |
| `apps/auth/tests/test_jira_callback.py` | 11 | Callback routing, token exchange, errors |
| `apps/onboarding/tests/test_views.py` | 29 total (13 new Jira) | View access, redirects, project creation |
| `tests/e2e/onboarding.spec.ts` | 6 Jira tests | UI elements, button links, auth |

## Commands to Verify

```bash
# Run all auth/onboarding tests
.venv/bin/pytest apps/auth/tests/ apps/onboarding/tests/ -v

# Run E2E tests for Jira
npx playwright test tests/e2e/onboarding.spec.ts --grep "jira"

# Lint check
.venv/bin/ruff check apps/auth/views.py apps/onboarding/views.py
```

## No Migrations Needed

This implementation uses existing models (`JiraIntegration`, `TrackedJiraProject`, `IntegrationCredential`). No new migrations required.

## Related Files (Reference)

| File | Pattern Used |
|------|--------------|
| `apps/auth/views.py:github_callback` | Unified callback pattern |
| `templates/onboarding/select_repos.html` | Template structure, Alpine.js |
| `apps/integrations/services/jira_oauth.py` | OAuth functions |
| `apps/integrations/services/jira_client.py` | `get_accessible_projects()` |
