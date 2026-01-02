# PostHog Analytics Enhancement - Tasks

**Last Updated:** 2026-01-02

---

## Phase 1: Backend Events (Critical Funnel) [M] ✅ COMPLETE

### 1.1 Integration Lifecycle Events

- [x] **Add `integration_connected` event** [S]
  - Files: `apps/auth/views.py` (lines 405-416, 632-643, 863-873)
  - Trigger: GitHub, Jira, Slack OAuth callback success paths
  - Properties: `provider`, `org_name/site_name/workspace_name`, `team_slug`, `is_reconnect`, `flow`
  - Commit: 6418e7e

- [x] **Add `integration_disconnected` event** [S]
  - Files: `apps/integrations/views/github.py:104-113`, `jira.py:160-169`, `slack.py:125-134`
  - Properties: `provider`, `org_name/site_name/workspace_name`, `team_slug`
  - Commit: 6418e7e

- [x] **Write tests for integration events** [S]
  - File: `apps/integrations/tests/test_analytics_events.py` (10 tests)
  - Coverage: disconnect events for all 3 providers, property validation
  - Commit: 6418e7e

### 1.2 Team Expansion Events

- [x] **Add `team_member_invited` event** [S]
  - File: `apps/teams/views/manage_team_views.py:121-130`
  - Properties: `team_slug`, `inviter_role`, `invite_method` (email)
  - Commit: 6418e7e

- [x] **Add `team_member_joined` event** [S]
  - File: `apps/teams/views/invitation_views.py:60-69`
  - Properties: `team_slug`, `invite_age_days`, `joined_via` (invite)
  - Commit: 6418e7e

- [x] **Write tests for team events** [S]
  - File: `apps/teams/tests/test_analytics_events.py` (6 tests)
  - Coverage: invite and join events, failure cases
  - Commit: 6418e7e

---

## Phase 2: User & Group Properties Enrichment [S] - Est. 1-2 hours

### 2.1 Enhanced identify_user

- [ ] **Add helper function `update_user_properties`** [S]
  - File: `apps/utils/analytics.py`
  - Purpose: Update user properties without full identify
  - Properties: role, teams_count, has_connected_* flags
  - Acceptance: Function exists with tests

- [ ] **Enhance signup identification** [S]
  - File: `apps/users/signals.py:handle_sign_up`
  - Add: `signup_source` property based on sociallogin
  - Acceptance: New signups have signup_source property

- [ ] **Update user properties on integration connect** [S]
  - File: `apps/integrations/views.py`
  - Add: Set `has_connected_github`, etc. on connection
  - Acceptance: User properties update on connection

### 2.2 Enhanced group_identify

- [ ] **Create `update_team_properties` helper** [S]
  - File: `apps/utils/analytics.py`
  - Purpose: Update team group properties
  - Properties: plan, repos_tracked, total_prs, ai_adoption_rate
  - Acceptance: Function exists with tests

- [ ] **Call group_identify on team changes** [S]
  - Files: `apps/teams/views.py`, `apps/integrations/views.py`
  - Trigger: Member join, repo add, subscription change
  - Acceptance: Team properties stay current

---

## Phase 3: Error Tracking [S] - Est. 1 hour

### 3.1 Error Middleware

- [ ] **Create error tracking middleware** [M]
  - File: `tformance/middleware.py` (add to existing or create)
  - Trigger: 500 errors only
  - Properties: `error_type`, `view_name`, `path`, `user_id`
  - Acceptance: 500 errors appear in PostHog

- [ ] **Add `track_error` helper** [S]
  - File: `apps/utils/analytics.py`
  - Purpose: Standardized error tracking
  - Features: Rate limiting, PII scrubbing
  - Acceptance: Function exists with tests

- [ ] **Register middleware** [S]
  - File: `tformance/settings.py`
  - Add: Middleware to MIDDLEWARE list
  - Acceptance: Middleware runs on requests

---

## Phase 4: Engagement Events [M] - Est. 2-3 hours

### 4.1 Analytics Enhancements

- [ ] **Add `date_filter_changed` event** [S]
  - File: `apps/metrics/views/analytics_views.py`
  - Trigger: When date params change (detect via comparison)
  - Properties: `tab`, `days`, `previous_days`, `preset`
  - Acceptance: Filter changes tracked

- [ ] **Add `repo_filter_applied` event** [S]
  - File: `apps/metrics/views/analytics_views.py`
  - Trigger: When repo filter is applied
  - Properties: `tab`, `repo_name`, `team_slug`
  - Acceptance: Repo filter usage tracked

### 4.2 PR List Enhancements

- [ ] **Add `pr_detail_viewed` event** [S]
  - File: Add to PR detail view/modal endpoint
  - Properties: `pr_id`, `is_ai_assisted`, `cycle_time_hours`
  - Acceptance: PR detail views tracked

- [ ] **Add `pr_list_filtered` event** [S]
  - File: `apps/metrics/views/pr_list_views.py`
  - Trigger: When filters are applied
  - Properties: `filter_type`, `active_filters_count`
  - Acceptance: Filter usage patterns visible

### 4.3 Other Features

- [ ] **Add `insight_viewed` event** [S]
  - File: `apps/insights/views.py`
  - Properties: `team_slug`, `insight_type`, `date_range`
  - Acceptance: Insights engagement tracked

- [ ] **Add `feedback_submitted` event** [S]
  - File: `apps/feedback/views.py:create_feedback`
  - Properties: `team_slug`, `sentiment`, `has_text`
  - Acceptance: Feedback submissions tracked

---

## Phase 5: Frontend Events [M] - Est. 2-3 hours

### 5.1 Analytics Module

- [ ] **Create `assets/javascript/analytics.js`** [M]
  - Purpose: Centralized frontend tracking
  - Functions: `trackChartInteraction`, `trackNavigation`, etc.
  - Acceptance: Module loads without errors

- [ ] **Add to Vite build** [S]
  - File: `vite.config.js` or entry point
  - Ensure: Module is bundled and available
  - Acceptance: Module accessible in browser

### 5.2 Chart Interactions

- [ ] **Track chart clicks/hovers** [M]
  - File: `assets/javascript/analytics.js`
  - Trigger: Chart.js event handlers
  - Properties: `chart_type`, `action`, `data_point`
  - Acceptance: Chart interactions appear in PostHog

### 5.3 Navigation & UI

- [ ] **Track sidebar navigation** [S]
  - File: `assets/javascript/analytics.js`
  - Trigger: Sidebar link clicks
  - Properties: `from_page`, `to_page`
  - Acceptance: Navigation patterns visible

- [ ] **Track theme switching** [S]
  - File: `assets/javascript/analytics.js`
  - Trigger: Theme toggle clicks
  - Properties: `new_theme`, `previous_theme`
  - Acceptance: Theme preferences tracked

---

## Verification & Cleanup

- [ ] **Verify all events in PostHog dashboard** [M]
  - Action: Trigger each event, check PostHog
  - Acceptance: All events appear with correct properties

- [ ] **Create PostHog funnels** [S]
  - Funnels: Onboarding, Activation, Integration Adoption
  - Acceptance: Funnels show data

- [ ] **Document events in CLAUDE.md** [S]
  - Add: Event tracking section to documentation
  - Acceptance: Future devs know about tracking

- [ ] **Remove any debug/test code** [S]
  - Action: Clean up console.logs, test events
  - Acceptance: No debug code in production

---

## Progress Summary

| Phase | Tasks | Completed | Status |
|-------|-------|-----------|--------|
| Phase 1 | 6 | 6 | ✅ Complete |
| Phase 2 | 5 | 0 | Not Started |
| Phase 3 | 3 | 0 | Not Started |
| Phase 4 | 6 | 0 | Not Started |
| Phase 5 | 5 | 0 | Not Started |
| Verification | 4 | 0 | Not Started |
| **Total** | **29** | **6** | **21%** |
