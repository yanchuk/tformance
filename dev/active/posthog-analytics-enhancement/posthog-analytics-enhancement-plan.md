# PostHog Analytics Enhancement Plan

**Last Updated:** 2026-01-02

---

## Executive Summary

Enhance PostHog analytics implementation to achieve comprehensive user behavior tracking across the Tformance platform. The goal is to enable data-driven decisions as the product moves toward paid subscriptions by tracking:
- Complete user journey from signup to activation
- Key conversion funnels (onboarding, integration, engagement)
- Feature usage and engagement patterns
- Error monitoring for debugging

**Current State:** ~60% coverage of critical user flows
**Target State:** ~95% coverage with actionable insights

---

## Current State Analysis

### What's Already Implemented ✅

**Backend (Python SDK):**
| Event | Location | Properties |
|-------|----------|------------|
| `user_signed_up` | `apps/users/signals.py:42` | `method` |
| `github_connected` | `apps/onboarding/views.py:325` | `org_name`, `member_count`, `team_slug` |
| `onboarding_step_completed` | `apps/onboarding/views.py:334` | `step`, `team_slug`, `repos_count` |
| `onboarding_skipped` | `apps/onboarding/views.py:646` | `step`, `team_slug` |
| `onboarding_completed` | `apps/onboarding/views.py:994` | `team_slug` |
| `slack_configured` | `apps/onboarding/views.py:888` | `team_slug`, feature toggles |
| `jira_connected` | `apps/auth/views.py:328` | `team_slug`, `site_url` |
| `dashboard_first_view` | `apps/metrics/views/analytics_views.py:91` | `team_slug` |
| `analytics_viewed` | `apps/metrics/views/analytics_views.py` | `tab`, `date_range`, `team_slug` |
| `pr_list_exported` | `apps/metrics/views/pr_list_views.py:229` | `format`, `row_count`, `has_filters` |

**Frontend (JS SDK):**
- `templates/web/components/posthog_init.html` - Autocapture, session recording, user/team identification

**Utility Module:**
- `apps/utils/analytics.py` - `track_event()`, `identify_user()`, `group_identify()`, `is_feature_enabled()`

### Identified Gaps

1. **Integration lifecycle** - No disconnect tracking, no reconnection tracking
2. **Team expansion** - Invite sent but no invite acceptance tracking
3. **User properties** - Missing role, signup source, feature adoption flags
4. **Group properties** - Missing plan, repos_tracked, ai_adoption_rate
5. **Error tracking** - No global error events
6. **Frontend events** - No custom chart/filter interaction tracking

---

## Proposed Future State

### Event Taxonomy (Tiered)

**Tier 1: Critical Funnel Events**
- `integration_connected` / `integration_disconnected`
- `team_member_invited` / `team_member_joined`
- `repo_sync_started` / `repo_sync_completed`
- `error_occurred`

**Tier 2: Engagement Events**
- `date_filter_changed`
- `repo_filter_applied`
- `pr_detail_viewed`
- `insight_viewed`
- `settings_updated`

**Tier 3: UX Optimization Events (Frontend)**
- `chart_interacted`
- `sidebar_navigation`
- `theme_switched`
- `external_link_clicked`

### User Identity Enrichment

| Property | Value | Purpose |
|----------|-------|---------|
| `role` | "admin" / "member" | Segment by role |
| `teams_count` | user.teams.count() | Multi-team users |
| `signup_source` | "github" / "email" / "invite" | Acquisition channel |
| `has_connected_github` | True/False | Feature adoption |
| `has_connected_jira` | True/False | Feature adoption |
| `has_connected_slack` | True/False | Feature adoption |

### Group (Team) Identity Enrichment

| Property | Value | Purpose |
|----------|-------|---------|
| `plan` | "trial" / "starter" / "pro" | Revenue segmentation |
| `onboarding_complete` | True/False | Activation tracking |
| `repos_tracked` | count | Usage intensity |
| `total_prs` | count | Data volume |
| `ai_adoption_rate` | percentage | Key business metric |

---

## Implementation Phases

### Phase 1: Backend Events (Critical Funnel) [M]

**Goal:** Track integration lifecycle and team expansion

**Files to modify:**
- `apps/integrations/views.py` - Add connect/disconnect events
- `apps/teams/views.py` - Add invite/join events
- `apps/utils/analytics.py` - Add helper for user properties update

**Acceptance Criteria:**
- [ ] `integration_connected` fires for GitHub, Jira, Slack connections
- [ ] `integration_disconnected` fires for all disconnect actions
- [ ] `team_member_invited` fires when invite is sent
- [ ] `team_member_joined` fires when invite is accepted
- [ ] All events include proper properties

### Phase 2: User & Group Properties Enrichment [S]

**Goal:** Rich user and team profiles for segmentation

**Files to modify:**
- `apps/utils/analytics.py` - Enhance `identify_user()` and `group_identify()`
- `apps/users/signals.py` - Add properties on signup
- `apps/teams/views.py` - Update properties on team changes
- `apps/integrations/views.py` - Update user properties on integration connect

**Acceptance Criteria:**
- [ ] User properties include role, teams_count, has_connected_* flags
- [ ] Team properties include plan, repos_tracked, ai_adoption_rate
- [ ] Properties update in real-time on relevant actions

### Phase 3: Error Tracking [S]

**Goal:** Capture application errors for debugging

**Files to modify:**
- `tformance/middleware.py` - Add error tracking middleware
- `apps/utils/analytics.py` - Add `track_error()` helper

**Acceptance Criteria:**
- [ ] 500 errors are tracked with view name, error type
- [ ] Error events don't expose sensitive data
- [ ] Rate limiting to prevent event spam

### Phase 4: Engagement Events [M]

**Goal:** Understand feature usage patterns

**Files to modify:**
- `apps/metrics/views/analytics_views.py` - Enhance existing events
- `apps/metrics/views/pr_list_views.py` - Add filter/sort events
- `apps/insights/views.py` - Add insight view events
- `apps/feedback/views.py` - Add feedback events

**Acceptance Criteria:**
- [ ] `date_filter_changed` captures filter interactions
- [ ] `repo_filter_applied` tracks multi-repo usage
- [ ] `pr_detail_viewed` captures PR engagement
- [ ] `insight_viewed` tracks insights feature usage

### Phase 5: Frontend Events [M]

**Goal:** Client-side interaction tracking

**Files to modify:**
- `assets/javascript/analytics.js` - Create new module
- `assets/javascript/alpine.js` - Add tracking to Alpine stores
- `templates/web/components/posthog_init.html` - Load analytics module

**Acceptance Criteria:**
- [ ] `chart_interacted` fires on chart clicks/hovers
- [ ] `sidebar_navigation` tracks navigation patterns
- [ ] `theme_switched` captures theme preference
- [ ] Events don't impact page performance

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Event volume exceeds PostHog free tier | Low | Medium | Start with Tier 1 events, monitor usage |
| Performance impact from tracking | Low | Medium | Use async tracking, batch events |
| Privacy concerns with user data | Medium | High | Only track necessary properties, no PII in events |
| Breaking existing tracking | Low | Medium | Add tests for existing events first |

---

## Success Metrics

| Metric | Target (Week 2) | Target (Month 1) |
|--------|-----------------|------------------|
| Events tracked per day | 500+ | 2,000+ |
| Funnel visibility | 100% of key steps | 100% of key steps |
| Error events captured | All 500 errors | All 500 errors |
| User properties coverage | 100% of users | 100% of users |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| PostHog API key | ✅ Ready | In .env |
| posthog Python SDK | ✅ Installed | v7.4.0+ |
| posthog-js | ✅ Loaded | CDN in template |
| Test infrastructure | ✅ Ready | pytest + factories |

---

## Technical Notes

### Event Naming Convention
- Use snake_case for event names
- Use past tense for completed actions: `connected`, `submitted`
- Use present tense for ongoing states: `viewing`, `filtering`

### Property Naming Convention
- Use snake_case for property names
- Include `team_slug` in all team-scoped events
- Include timestamp where relevant

### Code Pattern

```python
# In views
from apps.utils.analytics import track_event, identify_user

def my_view(request):
    # ... action code ...

    track_event(
        request.user,
        "action_completed",
        {
            "team_slug": request.team.slug,
            "relevant_property": value,
        },
    )
```

```javascript
// In frontend
posthog.capture('chart_interacted', {
    chart_type: 'ai_adoption',
    action: 'click',
    team_slug: window.teamSlug,
});
```
