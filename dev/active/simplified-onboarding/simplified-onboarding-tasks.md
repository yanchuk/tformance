# Simplified Onboarding - Tasks

> Last Updated: 2025-12-11

## Overview

- **Total Tasks:** 25
- **Estimated Effort:** 3-5 days
- **Priority:** High (improves user onboarding experience)
- **Branch:** `feature/simplified-onboarding`
- **Worktree:** `/Users/yanchuk/Documents/GitHub/tformance-simplified-onboarding/`

---

## Phase 1: Remove Team Creation from Signup

**Goal:** Users can sign up without creating a team

### Tasks

- [x] **1.1** Remove `team_name` field from `TeamSignupForm`
  - File: `apps/teams/forms.py`
  - Effort: S
  - Remove field definition
  - Remove `_clean_team_name()` method
  - Update `save()` to not call `create_default_team_for_user()`

- [x] **1.2** Update signup signal to not auto-create team
  - File: `apps/teams/signals.py`
  - Effort: S
  - Modify `add_user_to_team` signal
  - Keep invitation handling, remove default team creation

- [x] **1.3** Update signup template
  - File: `templates/account/signup.html`
  - Effort: S
  - Remove `{% render_field form.team_name %}` line

- [x] **1.4** Write tests for signup without team
  - File: `apps/teams/tests/test_signup.py`
  - Effort: M
  - Test user signup creates no team
  - Test invitation flow still works
  - Test existing users unaffected

---

## Phase 2: Create Onboarding App

**Goal:** New Django app for onboarding wizard

### Tasks

- [x] **2.1** Create onboarding Django app
  - Created: `apps/onboarding/`
  - Effort: S
  - Create app structure

- [x] **2.2** Create onboarding URLs
  - File: `apps/onboarding/urls.py`
  - Effort: S
  - Define URL patterns for wizard steps

- [x] **2.3** Register app in settings
  - File: `tformance/settings.py`
  - Effort: S
  - Add to `INSTALLED_APPS`

- [x] **2.4** Add URLs to main urlconf
  - File: `tformance/urls.py`
  - Effort: S
  - Include onboarding URLs at `/onboarding/`

- [x] **2.5** Create base onboarding template
  - File: `templates/onboarding/base.html`
  - Effort: M
  - Wizard layout with progress indicator
  - Step navigation

- [x] **2.6** Create start view and template
  - Files: `apps/onboarding/views.py`, `templates/onboarding/start.html`
  - Effort: M
  - "Connect GitHub" CTA
  - Brief explanation of what happens next

---

## Phase 3: GitHub OAuth Creates Team

**Goal:** Team created when user selects GitHub organization

### Tasks

- [x] **3.1** Create GitHub initiate view in onboarding
  - File: `apps/onboarding/views.py`
  - Effort: M
  - Reuse `github_oauth.get_authorization_url()`
  - Store state in session (no team_id yet)

- [x] **3.2** Create GitHub callback view for onboarding
  - File: `apps/onboarding/views.py`
  - Effort: L
  - Handle OAuth callback
  - Fetch user's organizations
  - If single org: auto-select
  - If multiple: redirect to org selection

- [x] **3.3** Create organization selection view
  - Files: `apps/onboarding/views.py`, `templates/onboarding/select_org.html`
  - Effort: M
  - Display list of organizations
  - Handle selection POST

- [x] **3.4** Create team from selected organization
  - File: `apps/onboarding/views.py`
  - Effort: M
  - Create `Team` with org name
  - Add user as admin
  - Create `IntegrationCredential`
  - Create `GitHubIntegration`
  - Trigger member sync

- [x] **3.5** Create repository selection view (placeholder)
  - Files: `apps/onboarding/views.py`, `templates/onboarding/select_repos.html`
  - Effort: M
  - Placeholder for now - actual repo selection coming later

---

## Phase 4: Optional Integration Steps

**Goal:** Add Jira and Slack connection steps with skip option

### Tasks

- [x] **4.1** Create Jira connection view (placeholder)
  - Files: `apps/onboarding/views.py`, `templates/onboarding/connect_jira.html`
  - Effort: M
  - "Connect Jira" button (disabled - coming soon)
  - "Skip for now" button

- [x] **4.2** Create Slack connection view (placeholder)
  - Files: `apps/onboarding/views.py`, `templates/onboarding/connect_slack.html`
  - Effort: M
  - "Add to Slack" button (disabled - coming soon)
  - "Skip for now" button

- [x] **4.3** Create completion view
  - Files: `apps/onboarding/views.py`, `templates/onboarding/complete.html`
  - Effort: M
  - Show sync status (members, repos)
  - "View Dashboard" button
  - Link to settings for skipped integrations

---

## Phase 5: Update Routing

**Goal:** Route users appropriately based on onboarding status

### Tasks

- [x] **5.1** Update home view routing
  - File: `apps/web/views.py`
  - Effort: S
  - If no team: redirect to `/onboarding/`
  - Remove old "create team" message

- [ ] **5.2** Create onboarding required decorator (optional)
  - File: `apps/onboarding/decorators.py` (new)
  - Effort: S
  - `@onboarding_complete_required`
  - Redirects teamless users to onboarding

- [ ] **5.3** Add tests for routing
  - File: `apps/onboarding/tests/test_routing.py` (new)
  - Effort: M
  - Test teamless user → onboarding
  - Test user with team → dashboard
  - Test invitation user → team dashboard

---

## Phase 6: Polish and Edge Cases

**Goal:** Handle edge cases and improve UX

### Tasks

- [x] **6.1** Handle OAuth errors gracefully
  - File: `apps/onboarding/views.py`
  - Effort: M
  - Show friendly error messages
  - Allow retry

- [x] **6.2** Handle no organizations found
  - File: `apps/onboarding/views.py`
  - Effort: S
  - Show helpful message
  - Link to GitHub org creation

- [ ] **6.3** Add session-based progress tracking
  - File: `apps/onboarding/views.py`
  - Effort: M
  - Store progress in session
  - Resume abandoned onboarding

- [ ] **6.4** Integration tests for full flow
  - File: `apps/onboarding/tests/test_full_flow.py` (new)
  - Effort: L
  - Test complete onboarding flow
  - Test skip flows
  - Test error recovery

---

## Summary by Phase

| Phase | Tasks | Status |
|-------|-------|--------|
| 1. Remove Team from Signup | 4 | DONE |
| 2. Create Onboarding App | 6 | DONE |
| 3. GitHub Creates Team | 5 | DONE |
| 4. Optional Steps | 3 | DONE |
| 5. Update Routing | 3 | 1/3 DONE |
| 6. Polish | 4 | 2/4 DONE |
| **Total** | **25** | **21/25 DONE** |

---

## Definition of Done

- [x] Phase 1-4 completed and checked off
- [x] Signup tests passing (`make test apps.teams.tests.test_signup`)
- [ ] All tests passing (`make test`)
- [ ] Code linted (`make ruff`)
- [ ] Manual testing completed (see context.md checklist)
- [x] PRD documentation updated
- [x] No regressions in invitation flow

---

## Next Steps

1. Commit and push the feature branch
2. Manual testing of the full onboarding flow
3. Add remaining tests (routing tests, integration tests)
4. Implement actual repository selection
5. Implement Jira/Slack OAuth in onboarding
