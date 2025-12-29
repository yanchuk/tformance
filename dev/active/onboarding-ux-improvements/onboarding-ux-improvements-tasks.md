# Onboarding UX Improvements - Task Checklist

**Last Updated:** 2025-12-29
**Status:** COMPLETED

## Phase 1: P0 Critical Fixes
**Estimated Effort:** S (2-3 hours) | **Status:** COMPLETED

### 1.1 Progress Indicator - Optional Labels
- [x] **TEST**: Write test for optional labels on Jira/Slack steps
- [x] **IMPL**: Add "(optional)" text under Jira step label in `base.html`
- [x] **IMPL**: Add "(optional)" text under Slack step label in `base.html`
- [x] **VERIFY**: Run tests, check visual appearance

### 1.2 Progress Indicator - Time Estimate
- [x] **TEST**: Write test for time estimate presence
- [x] **IMPL**: Add "~5 min" text in `base.html`
- [x] **VERIFY**: Run tests, check visual appearance

### 1.3 Complete Page - Status Messaging
- [x] **TEST**: Write test for info icon instead of warning
- [x] **IMPL**: Change clock icon to info-circle for skipped integrations in `complete.html`
- [x] **IMPL**: Update copy to "Available to connect later" instead of "not connected"
- [x] **IMPL**: Add context vars `jira_connected` and `slack_connected` in view
- [x] **VERIFY**: Run tests, check visual appearance

---

## Phase 2: P1 High Priority
**Estimated Effort:** M (1 day) | **Status:** COMPLETED

### 2.1 Repository Search Filter
- [x] **TEST**: Write E2E test for repo search functionality
- [x] **IMPL**: Add search input field in `select_repos.html`
- [x] **IMPL**: Add Alpine.js filter logic for repo list
- [x] **IMPL**: Add "no results" empty state
- [x] **VERIFY**: Run tests, test with many repos

### 2.4 Button Hierarchy - Jira
- [x] **VERIFY**: Buttons already correct (connect=primary, skip=ghost)

### 2.5 Button Hierarchy - Slack
- [x] **VERIFY**: Buttons already correct (connect=primary, skip=ghost)

### 2.6 Sync Progress - Continue Prominence
- [x] **VERIFY**: Already implemented correctly

---

## Phase 4: P3 + Missing Features
**Estimated Effort:** L (1-2 days) | **Status:** COMPLETED

### 4.4 Welcome Email
- [x] **TEST**: Write unit tests for welcome email service
- [x] **IMPL**: Create `apps/onboarding/services/__init__.py`
- [x] **IMPL**: Create `apps/onboarding/services/notifications.py`
- [x] **IMPL**: Call service after team creation in `views.py` (both org and skip flows)
- [x] **VERIFY**: Run tests, send test email

### 4.6 Slack Configuration Form
- [x] **TEST**: Write tests for Slack config form fields
- [x] **IMPL**: Add configuration form in `connect_slack.html`
- [x] **IMPL**: Add channel input, day/time selects
- [x] **IMPL**: Add feature toggle checkboxes (surveys, leaderboard, reveals)
- [x] **IMPL**: Update view to save configuration on POST
- [x] **VERIFY**: Run tests, test full flow

---

## Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1 (P0) | 3 groups | COMPLETED |
| Phase 2 (P1) | 4 groups | COMPLETED |
| Phase 4 (P3) | 2 groups | COMPLETED |

**Total Tests:** 97 passing (onboarding module)

## Files Modified

### Templates
- `templates/onboarding/base.html` - Optional labels, time estimate
- `templates/onboarding/complete.html` - Neutral messaging for skipped integrations
- `templates/onboarding/select_repos.html` - Search filter with Alpine.js
- `templates/onboarding/connect_slack.html` - Configuration form

### Views
- `apps/onboarding/views.py` - Welcome email, Slack config POST handler, complete page context

### New Services
- `apps/onboarding/services/__init__.py`
- `apps/onboarding/services/notifications.py` - Welcome email service

### New Tests
- `apps/onboarding/tests/test_ux_improvements.py` - UX improvement tests
- `apps/onboarding/tests/test_welcome_email.py` - Welcome email tests
- `apps/onboarding/tests/test_slack_config.py` - Slack config form tests
