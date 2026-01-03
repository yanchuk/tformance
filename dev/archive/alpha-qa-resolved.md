# Alpha QA - Resolved Issues Archive

**Archived:** 2026-01-03

This file contains resolved issues from the Alpha QA testing cycle. These issues have been fixed and verified.

---

## Summary

| ID | Priority | Type | Title | Resolved |
|----|----------|------|-------|----------|
| A-001 | P1 | Bug | Unrealistic 12-week trend percentages | 2026-01-03 |
| A-002 | P1 | Bug | Onboarding shows Jira/Slack despite feature flags | 2026-01-03 |
| A-003 | P2 | UX | Privacy message needs more emphasis | 2026-01-03 |
| A-004 | P1 | Copy | Copilot usage metrics needs "coming soon" | 2026-01-03 |
| A-005 | P2 | UI | Blank space after repo loader finishes | 2026-01-03 |
| A-006 | P0 | Bug | GitHub sync stalls at 0% | 2026-01-03 |
| A-007 | P1 | Bug | Team Members shows 0 after GitHub connection | 2026-01-03 |
| A-008 | P2 | UX | Tracked repos should appear at top of list | 2026-01-03 |
| A-009 | P2 | UX | Resync button doesn't show progress | 2026-01-03 |
| A-010 | P2 | UX | Sync progress display inconsistent | 2026-01-03 |
| A-011 | P2 | A11y | Sync banner text poor contrast | 2026-01-03 |
| A-012 | P2 | UI | Delete Team button not visible | 2026-01-03 |
| A-013 | P2 | UI | Profile page buttons styled as links | 2026-01-03 |
| A-014 | P3 | UI | GitHub logo too large in Connected Accounts | 2026-01-03 |
| A-015 | P1 | Flag | API Keys section should be hidden | 2026-01-03 |
| A-016 | P2 | Feature | No way to delete user account | 2026-01-03 |
| A-017 | P3 | Enhancement | Profile picture should use GitHub avatar | 2026-01-03 |
| A-018 | P2 | UI | Third party accounts page broken styling | 2026-01-03 |
| A-019 | P1 | Bug | Sync progress backend (GraphQL) | 2026-01-03 |
| A-021 | P1 | Bug | "Continue to Jira" button when Jira disabled | 2026-01-03 |
| A-026 | P1 | Bug | "Enhance your insights" banner when Jira/Slack disabled | 2026-01-03 |

---

## A-001: Unrealistic 12-week trend percentages on dashboard

**Priority:** P1 | **Type:** Bug | **Resolved:** 2026-01-03

### Description
Dashboard showed extreme trend percentages (+3100%, +12096%) that weren't credible.

### Root Cause
- `MIN_SPARKLINE_SAMPLE_SIZE = 3` was too low
- First week had only 3 PRs with 0.04h review time - unreliable baseline
- No cap on displayed percentage values

### Solution
- Increased `MIN_SPARKLINE_SAMPLE_SIZE` from 3 to 10
- Added `MAX_TREND_PERCENTAGE = 500` cap
- Updated all related tests

### Files Modified
- `apps/metrics/services/dashboard_service.py`
- `apps/metrics/tests/dashboard/test_sparkline_data.py`

---

## A-002: Onboarding shows Jira/Slack steps despite feature flags

**Priority:** P1 | **Type:** Bug | **Resolved:** 2026-01-03

### Description
Onboarding flow showed Jira/Slack steps even when feature flags disabled.

### Solution
- Added `_get_onboarding_flags_context()` helper
- Template conditionals in base.html, complete.html
- Dynamic step numbering implemented

### Files Modified
- `templates/onboarding/base.html`
- `templates/onboarding/complete.html`
- `apps/onboarding/views.py`

---

## A-003: Privacy message needs more emphasis

**Priority:** P2 | **Type:** UX Improvement | **Resolved:** 2026-01-03

### Description
Privacy reassurance message was too small and easy to miss.

### Solution
Added callout box with shield icon and light background.

---

## A-004: Copilot usage metrics needs "coming soon"

**Priority:** P1 | **Type:** Copy Change | **Resolved:** 2026-01-03

### Description
Copilot metrics listed as feature but not ready for alpha.

### Solution
Added "(coming soon)" label with muted styling.

---

## A-005: Blank space after repo list loader

**Priority:** P2 | **Type:** UI Bug | **Resolved:** 2026-01-03

### Description
Large blank gap remained after loader finished.

### Solution
Fixed loader container CSS to collapse when loading completes.

---

## A-006: GitHub sync stalls at 0%

**Priority:** P0 | **Type:** Bug | **Resolved:** 2026-01-03

### Description
Sync would stall indefinitely at 0% progress.

### Root Cause
- Celery workers hanging on GitHub API calls
- No task timeouts
- Tasks queued but not executing

### Solution
- Added task timeouts
- Fixed worker configuration
- Reset stuck repos to pending on restart

---

## A-007: Team Members shows 0 after GitHub connection

**Priority:** P1 | **Type:** Bug | **Resolved:** 2026-01-03

### Description
Team Members count showed 0 even after GitHub org connected.

### Solution
Fixed member sync task execution.

---

## A-008 through A-018: Various UI/UX Fixes

All resolved on 2026-01-03. See individual issue descriptions in original backlog for details.

---

## A-019: Sync progress backend (GraphQL)

**Priority:** P1 | **Type:** Bug | **Resolved:** 2026-01-03

### Description
GraphQL sync path didn't update progress tracking fields.

### Solution
1. Added `totalCount` to GraphQL queries
2. Added `_update_sync_progress()` async-safe helper
3. Updated sync functions to track progress
4. Added 3 tests for progress tracking

### Files Modified
- `apps/integrations/services/github_graphql.py`
- `apps/integrations/services/github_graphql_sync.py`
- `apps/integrations/tests/test_github_graphql_sync.py`

---

## A-021: "Continue to Jira" button shows when Jira disabled

**Priority:** P1 | **Type:** Bug (Regression) | **Resolved:** 2026-01-03

### Description
On sync page, the button says "Continue to Jira" even though Jira integration is feature-flagged off.

### Solution
Added `{% if enable_jira_integration %}` conditionals to three sections in `templates/onboarding/sync_progress.html`:
- Actions section (lines 70-84)
- Completion section (lines 86-106)
- Error/stalled section (lines 118-132)

When Jira disabled, buttons now say "Continue to Dashboard" and link to `{% url 'onboarding:complete' %}`.

### Files Modified
- `templates/onboarding/sync_progress.html`

---

## A-026: "Enhance your insights" banner shows when Jira/Slack disabled

**Priority:** P1 | **Type:** Bug (Regression) | **Resolved:** 2026-01-03

### Description
On Dashboard, the "Enhance your insights" banner shows with "Connect Jira" and "Connect Slack" buttons, but both integrations are feature-flagged off.

### Solution
Rewrote `templates/web/components/setup_prompt.html` to:
1. Use `{% with show_jira=enable_jira_integration %}` wrapper
2. Only show banner if at least one enabled integration is not connected
3. Only show buttons/messages for enabled integrations

### Files Modified
- `templates/web/components/setup_prompt.html`
