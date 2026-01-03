# Alpha QA Backlog

Tracking issues found during alpha version QA testing.

**Scope:** GitHub integration, 90-day data sync, LLM PR analysis, LLM dashboard insights.
**Out of scope:** Slack, Copilot, Jira connections.

---

## A-001: Unrealistic 12-week trend percentages on dashboard

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | PostHog team user |

### Description
Dashboard shows extreme trend percentages that don't look credible:
- PRs Merged: +3100% (should be ~+10%)
- Review Time: +12096% (should be ~+69%)

### Root Cause
1. `MIN_SPARKLINE_SAMPLE_SIZE = 3` is too low
2. First week (Oct 6) has only 3 PRs with 0.04h review time - unreliable baseline
3. Comparing tiny baseline to large current values = extreme percentages
4. No cap on displayed percentage values

### Reproduction
1. Log in as PostHog team user
2. Go to http://localhost:8000/app/
3. View dashboard with 30d time range selected
4. Observe +3100% and +12096% trends

### Acceptance Criteria
- [x] Increase `MIN_SPARKLINE_SAMPLE_SIZE` from 3 to 10
- [x] Cap trend percentages at ±500%
- [x] Update tests to use new sample sizes
- [x] Add test for percentage cap
- [x] Verify fix in browser

### Proposed Code Changes

**File: `apps/metrics/services/dashboard_service.py`**

```python
# Line 42: Changed from 3 to 10
MIN_SPARKLINE_SAMPLE_SIZE = 10

# Line 44-46: Added new constant
# Maximum trend percentage to display (A-001)
# Caps extreme percentages to avoid showing misleading values like +3100%
MAX_TREND_PERCENTAGE = 500

# Line 2271-2272: Added cap in _calculate_change_and_trend()
# Cap at ±MAX_TREND_PERCENTAGE to avoid misleading extreme values (A-001)
change_pct = max(-MAX_TREND_PERCENTAGE, min(MAX_TREND_PERCENTAGE, change_pct))
```

**File: `apps/metrics/tests/dashboard/test_sparkline_data.py`**

- Updated `test_trend_is_up_when_value_increases`: 3→10, 6→20 PRs
- Updated `test_trend_is_down_when_value_decreases`: 6→20, 3→10 PRs
- Updated `test_change_pct_calculated_correctly`: 3→10, 6→20 PRs
- Updated `test_trend_ignores_first_week_with_insufficient_data`: 5→10, 10→20 PRs
- Updated `test_trend_ignores_last_week_with_insufficient_data`: 5→10, 10→20 PRs
- Updated `test_pr_count_trend_also_respects_minimum_sample_size`: 5→10, 10→20 PRs
- Added new test `test_trend_percentage_capped_at_500`

### Expected Result After Fix
| Metric | Before | After |
|--------|--------|-------|
| PRs Merged trend | +3100% | +10% |
| Review Time trend | +12096% | +69% |

---

## A-002: Onboarding shows Jira/Slack steps despite feature flags being disabled

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
Onboarding shows Jira/Slack content in multiple places even though these integrations are feature-flagged off for alpha release.

### Affected Locations

1. **Stepper** - Shows all 5 steps including Jira (3) and Slack (4)
   - Current: GitHub → Repos → Jira (optional) → Slack (optional) → Done
   - Expected: GitHub → Repos → Done

2. **Sync page** - Button says "Continue to Jira" instead of "Continue to Dashboard"

3. **Completion page - Setup Summary**:
   - Shows "Jira – Available to connect later"
   - Shows "Slack – Available to connect later"
   - Should hide these items entirely

4. **Completion page - Footer text**:
   - Shows "You can connect Jira and Slack later from Settings > Integrations"
   - Should say "You can connect more integrations later from Settings > Integrations" or hide

5. **Dashboard - "Enhance your insights" banner**:
   - Shows banner with "Connect Jira" and "Connect Slack" buttons
   - Should hide entire banner when both integrations are disabled

### Reproduction
1. Log in as new user via OAuth
2. Complete GitHub OAuth
3. Go through onboarding flow
4. Observe Jira/Slack references throughout

### Acceptance Criteria
- [x] Stepper hides Jira/Slack steps when flags disabled
- [x] Step numbers adjust dynamically (1, 2, 3 not 1, 2, 5)
- [x] Sync page "Continue" button skips to Done/Dashboard
- [x] Setup Summary hides Jira/Slack items
- [x] Footer text doesn't mention disabled integrations
- [x] Dashboard "Enhance your insights" banner hidden when both disabled

### Implementation Notes
- Added `_get_onboarding_flags_context()` helper
- Template conditionals in base.html, complete.html
- Dynamic step numbering implemented

---

## A-003: Privacy message needs more emphasis on onboarding

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UX Improvement |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
The privacy reassurance message "We never see your code — only PR metadata like titles, timestamps, and review counts." is currently shown in small gray text at the bottom of the card. This is an important trust signal that should be more prominent.

### Current State
- Small text below the "Grant Access" button
- Gray color, easy to miss
- No visual emphasis

### Acceptance Criteria
- [ ] Make privacy message more visually prominent
- [ ] Consider: larger text, different color, icon, or callout box
- [ ] Message should be clearly visible before user clicks "Grant Access"

### Design Decision
**Callout box** - Light background with border, shield icon (Option 1 selected)

---

## A-004: Copilot usage metrics needs "coming soon" label

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Copy Change |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On the GitHub onboarding step, "Copilot usage metrics" is listed as a feature we'll access, but this isn't tested/ready for alpha. Needs "(coming soon)" label to set correct expectations.

### Current Copy
> **Copilot usage metrics**
> Correlate AI tool usage with delivery outcomes

### Expected Copy
> **Copilot usage metrics** (coming soon)
> Correlate AI tool usage with delivery outcomes

### Acceptance Criteria
- [ ] Add "(coming soon)" to Copilot usage metrics item
- [ ] Style "(coming soon)" as muted/secondary text

---

## A-005: Blank space remains after repo list loader finishes

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UI Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On the "Select Repositories" step, after the repo list finishes loading, there's a large blank space between the description text and the search bar. This is where the loader was displayed - the space doesn't collapse when loader is removed.

### Current Behavior
1. Loader shows while fetching repos (correct)
2. Repos load successfully (correct)
3. Large blank gap remains where loader was (bug)

### Expected Behavior
When loader finishes, the space should collapse and the search bar should move up closer to the description.

### Acceptance Criteria
- [ ] Loader container collapses when loading completes
- [ ] No visible gap between description and search bar after load
- [ ] Smooth transition (no jarring layout shift)

### Investigation Needed
- [ ] Find repo selection template
- [ ] Check loader container CSS (likely has fixed height)

---

## A-006: GitHub sync stalls at 0% and doesn't progress

| Field | Value |
|-------|-------|
| **Priority** | P0 (Blocker) |
| **Type** | Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
After selecting a repository (railsware/falcon) and starting sync, the sync stalls at 0% with "Starting sync... Calculating..." for over 45 seconds. Error message "Sync May Have Stalled" appears. Retry button doesn't help.

### Symptoms
- Progress stays at 0%
- Status shows "Calculating..." indefinitely
- Repo shows "Pending" status
- After ~45s: "Sync May Have Stalled - No progress in 45 seconds"
- Retry Sync button doesn't fix the issue
- Even on completion page, sync indicator shows "Syncing data... 0% complete"
- Sync progress indicator disappears on Dashboard (should persist until sync done)

### Additional Issues Found
1. Sync happens on step 3 labeled "Jira" (should skip to Done if Jira disabled)
2. Button says "Continue to Jira" instead of "Continue to Dashboard" or "Done"

### Reproduction
1. Complete GitHub OAuth as new user
2. Select repository (e.g., railsware/falcon)
3. Click to start sync
4. Wait 45+ seconds
5. Observe stall error

### Acceptance Criteria
- [ ] Investigate why sync is stuck (Celery? Redis? Task queue?)
- [ ] Sync should progress and complete successfully
- [ ] Retry should actually restart the sync task
- [ ] "Continue to Jira" should respect feature flags (shows "Continue to Dashboard" when Jira disabled)

### Investigation Completed (2026-01-03)

**Root Cause Found:**
1. Celery workers can hang indefinitely on GitHub API calls with no timeout
2. Redis is running (Docker), but Celery workers may not be started
3. Tasks get queued but never execute if worker isn't running
4. When worker is running, API calls can hang causing zombie processes

**Observed Behavior:**
- Tasks received by Celery but `acknowledged: False` indefinitely
- Worker processes stuck in uninterruptible sleep (kernel block)
- Database shows `sync_status: syncing` but `sync_progress: 0`

**Solution Required:**
- [ ] Add `soft_time_limit` and `time_limit` to sync tasks
- [ ] Implement circuit breaker for GitHub API calls
- [ ] Add health check for Celery worker status on dashboard
- [ ] Reset stuck repos to `pending` on worker restart

---

## A-007: Team Members shows 0 after GitHub connection

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On the Dashboard "Integration Status" section, "Team Members" shows "0 linked" even though GitHub org is connected and has members.

### Current Behavior
- GitHub: Connected (correct)
- Tracked Repos: 1 repositories (correct)
- Team Members: 0 linked (incorrect)

### Expected Behavior
Team Members should show actual count of org members imported from GitHub.

### Acceptance Criteria
- [ ] Team Members count reflects actual GitHub org members
- [ ] Members should be imported during initial sync
- [ ] Count should update when sync completes

### Investigation Needed
- [ ] Check if member sync is part of repo sync or separate task
- [ ] Verify member data is being fetched from GitHub API
- [ ] Check if this depends on sync completing (blocked by A-006)

---

## A-008: Tracked repositories should appear at top of list

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UX Improvement |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On the repositories page (`/app/integrations/github/repos/`), tracked repos are mixed with untracked repos. Hard to find which ones are being tracked in a long list.

### Current Behavior
Repos appear in default order (alphabetical or by GitHub order), tracked mixed with untracked.

### Expected Behavior
Tracked repositories should be sorted to the top of the list.

### Acceptance Criteria
- [ ] Tracked repos appear first in the list
- [ ] Within each group (tracked/untracked), maintain alphabetical order

---

## A-009: Resync button doesn't show progress indicator

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UX Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On the repositories page, clicking the Resync button (↻) doesn't show any sync progress indicator. User has no feedback that sync is happening.

### Current Behavior
- Click Resync button
- No visible progress indicator
- Repo shows "Syncing" badge but no progress percentage

### Expected Behavior
- Show sync progress indicator (spinner, progress bar, or percentage)
- Ideally show same "Syncing data... X% complete" indicator as onboarding

### Acceptance Criteria
- [ ] Resync shows visible progress indicator
- [ ] User gets feedback that sync started
- [ ] Progress updates as sync proceeds

---

## A-010: Sync progress display inconsistent across app

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UX Consistency |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
Sync progress is displayed differently in different parts of the app:
1. **Onboarding** - Small widget in bottom-right corner ("Syncing data... 0% complete")
2. **Dashboard** - Large blue banner at top ("Syncing 0% - 0 of 1 repos synced")

Should unify to one consistent pattern.

### Recommendation
Pick one approach and use consistently:
- **Option A:** Bottom-right widget (less intrusive, persistent across pages)
- **Option B:** Top banner (more visible, but takes up space)

### Acceptance Criteria
- [ ] Choose one sync progress pattern
- [ ] Apply consistently across all pages during sync

---

## A-011: Sync banner text has poor contrast (black on blue)

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | Accessibility/UI |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
The dashboard sync banner has black text on blue background. The secondary text "0 of 1 repos synced - railsware/falcon" is especially hard to read.

### Current State
- Background: Blue (#3B82F6 or similar)
- Text: Black (#000000)
- Contrast ratio: Poor, fails WCAG AA

### Expected State
- Text should be white for proper contrast on blue background

### Acceptance Criteria
- [ ] Change banner text to white
- [ ] Ensure WCAG AA compliance (4.5:1 contrast ratio minimum)

---

## A-012: Delete Team button not visible (styling broken)

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UI Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On Team Settings page (`/app/team/`), the "Danger Zone" section shows "Delete Team" text but the red delete button is not visible. Button exists but styling is broken.

### Current State
- "Danger Zone" heading visible
- "Delete Team" text visible
- No red button visible

### Expected State
- Large red "Delete Team" button should be visible
- Should match typical danger zone styling (red background, white text)

### Acceptance Criteria
- [ ] Delete Team button is visible with red styling
- [ ] Button is clearly identifiable as destructive action

---

## A-013: Profile page buttons styled as plain links

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UI Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
On Profile page (`/users/profile/`), all buttons appear as plain text links without proper button styling:
- "Save" button
- "Verify" button
- "Manage Accounts" button
- "New API Key" button

### Acceptance Criteria
- [ ] All action buttons have proper button styling
- [ ] Primary actions use primary button style
- [ ] Secondary actions use secondary/outline button style

---

## A-014: GitHub connected account logo too large

| Field | Value |
|-------|-------|
| **Priority** | P3 |
| **Type** | UI Polish |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
In the "Connected Accounts" section, the GitHub octocat logo is excessively large (takes up most of the card).

### Acceptance Criteria
- [ ] Reduce GitHub logo size to reasonable dimensions (e.g., 48-64px)
- [ ] Keep consistent with other UI elements

---

## A-015: API Keys section should be hidden for alpha

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Type** | Feature Flag |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
Profile page shows "API Keys" section but this functionality isn't ready for alpha. Should be hidden like Jira/Slack.

### Acceptance Criteria
- [ ] Hide API Keys section entirely for alpha
- [ ] Add feature flag for API Keys functionality

---

## A-016: No way to delete user account

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | Feature Gap |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
Users can delete their team but there's no option to delete their own user account. For GDPR compliance and user control, this should be available.

### Acceptance Criteria
- [ ] Add "Delete Account" option in Profile page
- [ ] Should be in a "Danger Zone" section like team deletion
- [ ] Include confirmation dialog with warnings

---

## A-017: Profile picture should use GitHub avatar (minor)

| Field | Value |
|-------|-------|
| **Priority** | P3 |
| **Type** | Enhancement |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
Profile picture shows default pattern instead of user's GitHub avatar. Since users sign in with GitHub, their avatar should be imported automatically.

### Acceptance Criteria
- [ ] Import GitHub avatar on OAuth
- [ ] Use as default profile picture

---

## Backlog Summary

**All 18 issues resolved on 2026-01-03**

| ID | Priority | Type | Title | Status |
|----|----------|------|-------|--------|
| A-006 | P0 | Bug | GitHub sync stalls at 0% | ✅ Resolved |
| A-001 | P1 | Bug | Unrealistic 12-week trend percentages | ✅ Resolved |
| A-002 | P1 | Bug | Onboarding shows Jira/Slack despite feature flags | ✅ Resolved |
| A-003 | P2 | UX | Privacy message needs more emphasis | ✅ Resolved |
| A-004 | P1 | Copy | Copilot usage metrics needs "coming soon" | ✅ Resolved |
| A-005 | P2 | UI | Blank space after repo loader finishes | ✅ Resolved |
| A-007 | P1 | Bug | Team Members shows 0 after GitHub connection | ✅ Resolved |
| A-008 | P2 | UX | Tracked repos should appear at top of list | ✅ Resolved |
| A-009 | P2 | UX | Resync button doesn't show progress | ✅ Resolved |
| A-010 | P2 | UX | Sync progress display inconsistent | ✅ Resolved |
| A-011 | P2 | A11y | Sync banner text poor contrast | ✅ Resolved |
| A-012 | P2 | UI | Delete Team button not visible | ✅ Resolved |
| A-013 | P2 | UI | Profile page buttons styled as links | ✅ Resolved |
| A-014 | P3 | UI | GitHub logo too large in Connected Accounts | ✅ Resolved |
| A-015 | P1 | Flag | API Keys section should be hidden | ✅ Resolved |
| A-016 | P2 | Feature | No way to delete user account | ✅ Resolved |
| A-017 | P3 | Enhancement | Profile picture should use GitHub avatar | ✅ Resolved |
| A-018 | P2 | UI | Third party accounts page broken styling | ✅ Resolved |

---

## A-018: Third party accounts page has broken styling

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Type** | UI Bug |
| **Status** | ✅ Resolved (2026-01-03) |
| **Reporter** | New user flow testing |

### Description
The third party accounts page (`/accounts/3rdparty/`) has broken styling - buttons and layout elements are not displaying correctly.

### Reproduction
1. Go to https://dev.ianchuk.com/accounts/3rdparty/
2. Observe broken button styles and layout

### Acceptance Criteria
- [ ] All buttons properly styled
- [ ] Layout matches design system
- [ ] Consistent with other profile/settings pages

---

*Last updated: 2026-01-03*
