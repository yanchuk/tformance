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

## Phase 2: User & Group Properties Enrichment [S] ✅ COMPLETE

### 2.1 Enhanced identify_user

- [x] **Add helper function `update_user_properties`** [S]
  - File: `apps/utils/analytics.py:119-146`
  - Purpose: Lightweight property updates without re-sending full profile
  - Tests: 6 new tests in test_analytics.py
  - Commit: 689c7c9

- [x] **Enhance signup identification** [S]
  - File: `apps/users/signals.py:handle_sign_up`
  - Added: `signup_source`, `teams_count`, `has_connected_*` initial values
  - Commit: 689c7c9

- [x] **Update user properties on integration connect** [S]
  - File: `apps/auth/views.py` (lines 418, 647, 879)
  - Added: Set `has_connected_github/jira/slack` = True on connect
  - Commit: 689c7c9

### 2.2 Enhanced group_identify

- [x] **Create `update_team_properties` helper** [S]
  - File: `apps/utils/analytics.py:149-177`
  - Purpose: Lightweight team property updates
  - Tests: 6 new tests in test_analytics.py
  - Commit: 689c7c9

- [x] **Call group_identify on team changes** [S]
  - File: `apps/teams/views/invitation_views.py:71-79`
  - Added: Update `teams_count` for user, `member_count` for team on join
  - Commit: 689c7c9

---

## Phase 3: Error Tracking [S] ✅ COMPLETE

### 3.1 Error Middleware

- [x] **Add `track_error` helper** [S]
  - File: `apps/utils/analytics.py:180-222`
  - Purpose: Standardized error tracking with anonymous user support
  - Properties: `error_type`, `path`, `method`, `status_code`, `view_name`, `team_id`
  - Tests: 5 new tests in test_analytics.py
  - Commit: c09bc38

- [x] **Create error tracking middleware** [M]
  - File: `apps/utils/middleware.py:83-131`
  - Trigger: 500 errors only
  - Properties: `path`, `method`, `status_code`, `view_name`
  - Commit: c09bc38

- [x] **Register middleware** [S]
  - File: `tformance/settings.py`
  - Added after TeamsMiddleware
  - Commit: c09bc38

---

## Phase 4: Engagement Events [M] ✅ COMPLETE

### 4.1 Analytics Enhancements

- [x] **Add `repo_filter_applied` event** [S]
  - File: `apps/metrics/views/analytics_views.py:72-92`
  - Helper: `_track_filter_events()` called from all analytics views
  - Properties: `tab`, `repo_name`, `team_slug`
  - Commit: b65287b

### 4.2 PR List Enhancements

- [x] **Add `pr_list_filtered` event** [S]
  - File: `apps/metrics/views/pr_list_views.py:189-202`
  - Helper: `_count_active_filters()` for counting non-date filters
  - Properties: `filter_type`, `active_filters_count`, `team_slug`
  - Commit: b65287b

- [ ] **Add `pr_detail_viewed` event** [S]
  - Status: Deferred - no PR detail view exists yet
  - Will be added when PR detail modal/page is implemented

### 4.3 Other Features

- [x] **Add `insight_viewed` event** [S]
  - File: `apps/insights/views.py:46-55, 126-135`
  - Trigger: get_summary and ask_question views
  - Properties: `insight_type` (summary/question), `team_slug`, `is_refresh`/`question_length`
  - Commit: b65287b

- [x] **Add `feedback_submitted` event** [S]
  - File: `apps/feedback/views.py:98-107`
  - Properties: `team_slug`, `category`, `has_text`
  - Commit: b65287b

---

## Phase 5: Frontend Events [M] ✅ COMPLETE

### 5.1 Analytics Module

- [x] **Create `assets/javascript/analytics.js`** [M]
  - File: `assets/javascript/analytics.js` (new, 145 lines)
  - Functions: `trackEvent`, `trackChartInteraction`, `trackNavigation`, `trackThemeSwitch`
  - Exposed globally as `window.TformanceAnalytics`
  - Commit: 2ba0d56

- [x] **Add to Vite build** [S]
  - File: `assets/javascript/app.js` - imports analytics module
  - Module bundled into app-bundle.js (68.84 kB)
  - Commit: 2ba0d56

### 5.2 Chart Interactions

- [x] **Track chart clicks** [M]
  - File: `assets/javascript/analytics.js:addChartTracking()`
  - Integrated via `addChartTrackingToAll()` after HTMX swaps
  - Properties: `chart_type`, `action`, `data_label`, `data_value`
  - Commit: 2ba0d56

### 5.3 Navigation & UI

- [x] **Track sidebar navigation** [S]
  - File: `assets/javascript/analytics.js:initNavigationTracking()`
  - Auto-attaches to sidebar links, tracks navigation event
  - Properties: `from_page`, `to_page`
  - Commit: 2ba0d56

- [x] **Track theme switching** [S]
  - File: `assets/javascript/theme.js` - integrated with syncDarkMode()
  - Only tracks after initial page load (not on first load)
  - Properties: `new_theme`, `previous_theme`
  - Commit: 2ba0d56

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
| Phase 2 | 5 | 5 | ✅ Complete |
| Phase 3 | 3 | 3 | ✅ Complete |
| Phase 4 | 5 | 4 | ✅ Complete (1 deferred) |
| Phase 5 | 5 | 5 | ✅ Complete |
| Verification | 4 | 0 | Pending |
| **Total** | **28** | **23** | **82%** |
