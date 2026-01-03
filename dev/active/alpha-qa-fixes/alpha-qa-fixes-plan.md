# Alpha QA Fixes - Implementation Plan

## Executive Summary

This plan addresses 18 QA issues found during alpha version testing. Issues span UI/UX bugs, feature flag compliance, accessibility fixes, and one P0 blocker (sync stall). Implementation follows strict TDD methodology with E2E validation where appropriate.

**Total Issues:** 18
- **P0 (Blocker):** 1
- **P1 (Critical):** 5
- **P2 (Important):** 10
- **P3 (Minor):** 2

**Estimated Effort:** M-L (2-3 sessions)

---

## Current State Analysis

### Codebase Context

| Component | Current State |
|-----------|--------------|
| Feature Flags | `integration_flags.py` provides Jira/Slack/Copilot flags, but templates don't fully respect them |
| Onboarding Flow | 5-step stepper hardcoded in `base.html`, doesn't adapt to disabled features |
| Dashboard Service | `MIN_SPARKLINE_SAMPLE_SIZE = 3` too low, no percentage cap |
| Profile Page | Includes `api_keys.html` without feature flag check |
| Sync System | Celery tasks + Redis, progress polling via `/celery-progress/` |
| UI Styling | DaisyUI + Tailwind, some `pg-*` Pegasus classes may not be styled |

### Key Files Identified

| Issue Area | Primary Files |
|------------|---------------|
| Trend Percentages | `apps/metrics/services/dashboard_service.py` (line 42, 2216-2280) |
| Feature Flags | `apps/integrations/services/integration_flags.py`, templates |
| Onboarding | `templates/onboarding/base.html`, `start.html`, `complete.html`, `sync_progress.html` |
| Profile/Settings | `templates/account/profile.html`, `components/api_keys.html`, `components/social/social_accounts.html` |
| Team Settings | `templates/teams/manage_team.html` |
| Sync Progress | `apps/onboarding/views.py`, Celery tasks |

---

## Implementation Phases

### Phase 1: P0 Blocker - Sync Investigation (TDD) ⚠️

**Issue:** A-006 - GitHub sync stalls at 0%

**Investigation Steps:**
1. Check Celery worker status: `celery -A tformance inspect active`
2. Check Redis connection: `redis-cli ping`
3. Review Celery task logs
4. Verify `start_onboarding_pipeline` task execution

**Root Cause Hypothesis:**
- Celery worker not running or crashed
- Redis connection issue
- Task serialization error
- GitHub API rate limiting

**Acceptance Criteria:**
- [ ] Identify root cause
- [ ] Sync progresses past 0%
- [ ] Sync completes successfully for 1 repo
- [ ] E2E test validates sync completion

---

### Phase 2: Critical Bug Fixes (P1 - TDD)

#### 2.1 A-001: Unrealistic Trend Percentages

**Files to Modify:**
- `apps/metrics/services/dashboard_service.py`
- `apps/metrics/tests/dashboard/test_sparkline_data.py`

**Changes:**
```python
# dashboard_service.py line 42
MIN_SPARKLINE_SAMPLE_SIZE = 10  # Changed from 3

# Add new constant after line 42
MAX_TREND_PERCENTAGE = 500

# In _calculate_change_and_trend() ~line 2270
change_pct = max(-MAX_TREND_PERCENTAGE, min(MAX_TREND_PERCENTAGE, change_pct))
```

**TDD Tests:**
1. `test_trend_percentage_capped_at_positive_500`
2. `test_trend_percentage_capped_at_negative_500`
3. Update existing tests to use 10+ PR sample sizes

**Effort:** S

---

#### 2.2 A-002: Hide Jira/Slack When Flags Disabled

**Files to Modify:**
- `templates/onboarding/base.html` (stepper)
- `templates/onboarding/sync_progress.html` ("Continue to Jira" button)
- `templates/onboarding/complete.html` (Setup Summary + footer)
- `templates/metrics/cto_dashboard.html` ("Enhance insights" banner)

**Strategy:**
Pass feature flag context to templates and use conditional rendering.

**View Changes:**
```python
# In onboarding views, add to context:
from apps.integrations.services.integration_flags import is_integration_enabled

context['jira_enabled'] = is_integration_enabled(request, 'jira')
context['slack_enabled'] = is_integration_enabled(request, 'slack')
```

**Template Changes (base.html stepper):**
```django
{% if jira_enabled %}
{# Step 3: Jira #}
{% endif %}
{% if slack_enabled %}
{# Step 4: Slack #}
{% endif %}
```

**Dynamic Step Numbering:**
Use Alpine.js to calculate visible step numbers or pass from backend.

**TDD Tests:**
- `test_onboarding_stepper_hides_jira_when_disabled`
- `test_onboarding_stepper_hides_slack_when_disabled`
- `test_complete_page_hides_jira_slack_when_disabled`
- `test_dashboard_hides_enhance_banner_when_both_disabled`

**E2E Tests:**
- `integration-flags.spec.ts` - add onboarding flow checks

**Effort:** M

---

#### 2.3 A-004: Copilot "Coming Soon" Label

**File:** `templates/onboarding/start.html` (line 41-45)

**Change:**
```django
<li class="flex items-start gap-3">
  <i class="fa-solid fa-robot text-accent mt-1"></i>
  <div>
    <span class="text-base-content font-medium">
      {% translate "Copilot usage metrics" %}
      <span class="text-base-content/50 text-sm">({% translate "coming soon" %})</span>
    </span>
    <p class="text-xs text-base-content/60 mt-0.5">{% translate "Correlate AI tool usage with delivery outcomes" %}</p>
  </div>
</li>
```

**TDD Tests:**
- `test_github_onboarding_shows_copilot_coming_soon`

**Effort:** S

---

#### 2.4 A-007: Team Members Shows 0

**Investigation:**
- Check if `member_sync.sync_github_members(team)` runs during onboarding
- Verify `TeamMember` records created
- Check if count query is correct

**Files:**
- `apps/integrations/services/member_sync.py`
- `apps/integrations/models.py`
- `apps/metrics/models.py` (TeamMember)

**Potential Fix:**
- Ensure member sync completes before dashboard shows
- Or show "Syncing..." state while in progress

**TDD Tests:**
- `test_team_members_count_after_github_connection`

**Effort:** M (depends on investigation)

---

#### 2.5 A-015: Hide API Keys Section

**File:** `templates/account/profile.html` (line 12)

**Change:**
```django
{% comment %}A-015: Hide API Keys for alpha{% endcomment %}
{% comment %}{% include 'account/components/api_keys.html' %}{% endcomment %}
```

Or add feature flag:
```django
{% load waffle_tags %}
{% flag "api_keys_enabled" %}
{% include 'account/components/api_keys.html' %}
{% endflag %}
```

**TDD Tests:**
- `test_profile_hides_api_keys_for_alpha`

**Effort:** S

---

### Phase 3: UX Improvements (P2 - TDD)

#### 3.1 A-003: Privacy Message Callout Box

**File:** `templates/onboarding/start.html` (line 61-66)

**Change to:**
```django
<div class="mt-6 pt-4 border-t border-base-300">
  <div class="bg-accent/5 border border-accent/20 rounded-lg p-4 flex items-start gap-3">
    <i class="fa-solid fa-shield-halved text-accent text-xl mt-0.5"></i>
    <div>
      <p class="text-sm font-medium text-base-content mb-1">{% translate "Privacy First" %}</p>
      <p class="text-xs text-base-content/70">
        {% translate "We never see your code — only PR metadata like titles, timestamps, and review counts." %}
      </p>
    </div>
  </div>
</div>
```

**Effort:** S

---

#### 3.2 A-005: Blank Space After Loader

**Files:**
- `templates/onboarding/select_repos.html`
- `templates/onboarding/partials/repos_list.html`

**Fix:** Ensure loader container has no fixed height, or use Alpine.js to remove container after load.

**Effort:** S

---

#### 3.3 A-008: Tracked Repos at Top

**File:** `apps/integrations/views/github.py` (or wherever repo list is sorted)

**Change:** Sort repos with `is_tracked=True` first.

```python
repos = sorted(repos, key=lambda r: (not r.get('is_tracked', False), r.get('name', '').lower()))
```

**TDD Tests:**
- `test_tracked_repos_appear_first_in_list`

**Effort:** S

---

#### 3.4 A-009, A-010: Sync Progress Consistency

**Decision Needed:** Use bottom-right widget OR top banner consistently.

**Recommendation:** Use bottom-right widget (less intrusive, already implemented in onboarding).

**Files:**
- `templates/metrics/cto_dashboard.html` (remove/update banner)
- `templates/web/app/app_base.html` (add global sync indicator)

**Effort:** M

---

#### 3.5 A-011: Sync Banner Contrast

**File:** Sync banner template (find location)

**Change:** `text-white` instead of `text-black` on blue background.

**Effort:** S

---

#### 3.6 A-012: Delete Team Button

**File:** `templates/teams/manage_team.html` (line 85)

**Current:**
```django
<label for="delete-modal" class="pg-button-danger modal-button">{% translate 'Delete Team' %}</label>
```

**Fix:** Change to DaisyUI button class:
```django
<label for="delete-modal" class="btn btn-error modal-button">{% translate 'Delete Team' %}</label>
```

**Effort:** S

---

#### 3.7 A-013: Profile Page Button Styling

**Files:**
- `templates/account/components/profile_form.html`
- `templates/account/components/social/social_accounts.html`

**Fix:** Update `pg-button-*` classes to `btn btn-*` DaisyUI classes.

**Effort:** S

---

#### 3.8 A-016: Delete User Account

**New Feature - Requires:**
1. New view in `apps/users/views.py`
2. URL pattern
3. Template with confirmation modal
4. Account deletion logic (handle team ownership)

**Effort:** M

---

#### 3.9 A-018: Third Party Accounts Page Styling

**File:** `templates/socialaccount/connections.html` (django-allauth template)

**Fix:** Override allauth template with DaisyUI styling.

**Effort:** S

---

### Phase 4: Polish (P3)

#### 4.1 A-014: GitHub Logo Size

**File:** `templates/account/components/social/social_accounts.html`

**Fix:** Add size constraint to GitHub logo (e.g., `w-12 h-12` or `max-w-12`).

**Effort:** S

---

#### 4.2 A-017: GitHub Avatar Import

**Files:**
- `apps/users/signals.py` (or OAuth callback)
- `apps/users/models.py`

**Implementation:**
On GitHub OAuth callback, fetch avatar URL and save to user profile.

**Effort:** S-M

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Sync blocker unfixable | Low | High | Investigate thoroughly, have fallback manual sync |
| Feature flag changes break existing users | Medium | Medium | Test with both flag states |
| Template changes break responsive layout | Medium | Low | E2E visual regression tests |
| Avatar import privacy concerns | Low | Medium | Only import public avatar URL |

---

## Success Metrics

- [ ] All 18 issues marked resolved
- [ ] All unit tests pass (TDD compliance)
- [ ] E2E smoke tests pass
- [ ] No regressions in existing functionality
- [ ] Alpha users can complete onboarding flow
- [ ] Sync completes successfully

---

## E2E Test Coverage

| Test File | New/Updated Tests |
|-----------|-------------------|
| `integration-flags.spec.ts` | Onboarding flow with flags disabled |
| `onboarding.spec.ts` | New - full onboarding flow |
| `dashboard.spec.ts` | Sync progress, banner visibility |
| `profile.spec.ts` | New - API keys hidden, button styling |

---

## Implementation Order

1. **A-006** (P0) - Investigate sync blocker FIRST
2. **A-001** - Trend percentages (quick win, high impact)
3. **A-015** - Hide API Keys (quick win)
4. **A-004** - Copilot coming soon (quick win)
5. **A-002** - Jira/Slack hiding (complex, multiple files)
6. **A-007** - Team members count (depends on A-006)
7. **A-003** - Privacy callout (UX)
8. **A-012, A-013** - Button styling fixes
9. **A-011** - Sync banner contrast
10. **A-005** - Loader blank space
11. **A-008** - Tracked repos sorting
12. **A-009, A-010** - Sync progress consistency
13. **A-018** - Third party accounts styling
14. **A-014** - GitHub logo size
15. **A-016** - Delete user account (new feature)
16. **A-017** - GitHub avatar import

---

*Last Updated: 2026-01-03*
