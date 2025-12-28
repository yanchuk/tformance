# PostHog Analytics Integration Plan

**Last Updated:** 2025-12-25

---

## Executive Summary

Integrate PostHog analytics comprehensively into the AI Impact Analytics Platform to track user behavior, measure conversion funnels, and understand product usage. This will enable data-driven decisions as the product moves toward paid subscriptions.

**Primary Goals:**
1. Track the complete user journey from signup to activation
2. Measure key conversion funnels (onboarding, integration connection, dashboard engagement)
3. Enable session replay for debugging and UX research
4. Deploy in-app surveys for qualitative feedback
5. Set up feature flags for gradual rollout capabilities

**Why PostHog (not Mixpanel/Amplitude):**
- Already installed and partially configured
- Free tier: 1M events, 5K recordings, 1M flag requests, 100K exceptions, 1.5K surveys/month
- Single platform for analytics + replays + surveys + flags
- Open source option available if needed

---

## Current State Analysis

### What's Already Done

| Component | Status | Details |
|-----------|--------|---------|
| Python SDK | ✅ Installed | `posthog>=7.4.0` in pyproject.toml |
| Settings Config | ✅ Configured | `POSTHOG_API_KEY` and `POSTHOG_HOST` in settings.py |
| Server Init | ✅ Working | `posthog.project_api_key` set on startup |
| LLM Tracking | ✅ Partial | Used in `gemini_client.py` for AI observability |
| Frontend JS | ❌ Missing | No posthog-js loaded in templates |
| Session Replay | ❌ Missing | Requires JS SDK |
| Autocapture | ❌ Missing | Requires JS SDK |
| Surveys | ❌ Missing | Requires JS SDK + config |
| Feature Flags | ❌ Missing | Not implemented |

### Key Metrics Not Currently Tracked

| Category | Missing Events |
|----------|---------------|
| **Onboarding** | signup_started, github_connected, repos_selected, jira_connected, slack_connected, onboarding_completed |
| **Activation** | first_dashboard_view, first_pr_survey_sent, first_survey_response |
| **Engagement** | dashboard_view, analytics_tab_changed, date_filter_changed, export_csv |
| **Value** | ai_correlation_viewed, benchmark_viewed, insight_dismissed |
| **Growth** | team_member_invited, integration_reconnected |

---

## Proposed Future State

### Analytics Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (Templates)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  posthog-js SDK                                           │   │
│  │  - Autocapture (clicks, page views)                       │   │
│  │  - Session recording                                      │   │
│  │  - Feature flag evaluation                                │   │
│  │  - Survey rendering                                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PostHog Cloud (us.posthog.com)                 │
│  - Event ingestion                                               │
│  - Session replay storage                                        │
│  - Survey definitions                                            │
│  - Feature flag definitions                                      │
│  - Cohort definitions                                            │
└──────────────────────────────────────────────────────────────────┘
                                ▲
                                │
┌─────────────────────────────────────────────────────────────────┐
│                         Backend (Django)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  posthog Python SDK                                       │   │
│  │  - Server-side events (syncs, errors, background jobs)   │   │
│  │  - User identification ($set, $set_once)                  │   │
│  │  - Feature flag server-side checks                        │   │
│  │  - Group analytics (Team as group)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Event Taxonomy (Minimal, High-Value)

**Principle:** Track only events that inform decisions. No "just in case" events.

#### Tier 1: Core Funnel Events (Must Have)

| Event | Properties | Purpose |
|-------|------------|---------|
| `user_signed_up` | method (email/google/github) | Acquisition |
| `onboarding_step_completed` | step (github/repos/jira/slack), duration_seconds | Onboarding drop-off |
| `onboarding_skipped` | step | Where users bail |
| `github_connected` | org_name, member_count | Key activation |
| `dashboard_first_view` | team_slug | Activation complete |
| `subscription_started` | plan, seats | Revenue |
| `subscription_cancelled` | reason, days_active | Churn |

#### Tier 2: Engagement Events (Should Have)

| Event | Properties | Purpose |
|-------|------------|---------|
| `analytics_viewed` | tab (overview/ai/delivery/quality/team), date_range | Feature usage |
| `pr_list_exported` | format (csv), row_count | Value extraction |
| `survey_response_submitted` | type (author/reviewer), ai_assisted | Core feature usage |
| `leaderboard_viewed` | team_slug | Gamification engagement |

#### Tier 3: Growth Events (Nice to Have)

| Event | Properties | Purpose |
|-------|------------|---------|
| `team_member_invited` | role | Expansion |
| `integration_health_checked` | integration, status | Support needs |

### Group Analytics

Track metrics at the **Team** level (organization):

```python
posthog.group_identify(
    group_type="team",
    group_key=team.slug,
    properties={
        "name": team.name,
        "member_count": team.members.count(),
        "plan": team.subscription.plan if team.subscription else "trial",
        "github_connected": team.has_github_connection,
        "jira_connected": team.has_jira_connection,
        "slack_connected": team.has_slack_connection,
    }
)
```

### User Properties

Set once on signup, update as needed:

```python
posthog.identify(
    distinct_id=user.id,
    properties={
        "$email": user.email,
        "$name": user.get_full_name(),
        "role": "admin" if user.is_team_admin else "member",
        "signup_date": user.date_joined.isoformat(),
    }
)
```

---

## Implementation Phases

### Phase 1: Frontend JS SDK [S] - Day 1-2

**Goal:** Enable autocapture, session replay, and user identification in browser

**Changes:**
1. Add PostHog JS snippet to `templates/web/base.html`
2. Create Django context processor for PostHog config
3. Implement user identification on login
4. Enable session recording

### Phase 2: Core Funnel Tracking [M] - Day 3-5

**Goal:** Track the complete signup → activation funnel

**Changes:**
1. Track onboarding step completion
2. Track GitHub/Jira/Slack connection events
3. Track first dashboard view
4. Track subscription events

### Phase 3: Engagement Tracking [S] - Day 6-7

**Goal:** Understand how users interact with core features

**Changes:**
1. Track analytics page views
2. Track PR list exports
3. Track date filter changes
4. Track insight interactions

### Phase 4: Session Replay & Error Tracking [S] - Day 8

**Goal:** Enable debugging and UX research capabilities

**Changes:**
1. Configure session recording rules (exclude sensitive pages)
2. Enable exception autocapture
3. Set up recording privacy masks for PII

### Phase 5: In-App Surveys [M] - Day 9-11

**Goal:** Collect qualitative feedback at key moments

**Surveys to Create:**
1. **Post-onboarding NPS:** After first week, "How likely to recommend?"
2. **Feature satisfaction:** After viewing AI correlation, "Was this helpful?"
3. **Churn prevention:** On subscription cancel page, "Why are you leaving?"

### Phase 6: Feature Flags [S] - Day 12-13

**Goal:** Enable gradual rollout of new features

**Flags to Set Up:**
1. `trends-dashboard` - Gate the new trends feature
2. `benchmarks` - Gate industry benchmarks
3. `insights-engine` - Gate actionable insights

---

## Key Funnels to Build in PostHog

### 1. Onboarding Funnel

```
user_signed_up
  → onboarding_step_completed (github)
    → onboarding_step_completed (repos)
      → onboarding_step_completed (jira) [optional]
        → onboarding_step_completed (slack) [optional]
          → dashboard_first_view
```

**Target:** 80%+ completion rate for required steps

### 2. Activation Funnel

```
dashboard_first_view
  → analytics_viewed (any tab)
    → survey_response_submitted (first)
      → pr_list_exported (first)
```

**Target:** 50%+ reach survey response within 14 days

### 3. Engagement Cohort

Weekly active users who:
- Viewed dashboard at least 2x in last 7 days
- Or submitted 1+ survey response
- Or exported data

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Event volume exceeds free tier | Low | Medium | Start with Tier 1 events only, monitor usage |
| Session recording privacy concerns | Medium | High | Mask all form inputs, exclude auth pages |
| Performance impact from JS SDK | Low | Low | Load SDK async, enable compression |
| User identification failures | Low | Medium | Use server-side identify as fallback |

---

## Success Metrics

| Metric | Target (Week 4) | Target (Month 3) |
|--------|-----------------|------------------|
| Events tracked per week | 1,000+ | 10,000+ |
| Session recordings collected | 100+ | 500+ |
| Survey responses | 20+ | 100+ |
| Funnel visibility | 100% of key steps | 100% of key steps |

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| PostHog API key | ✅ Have | In .env |
| posthog Python SDK | ✅ Installed | v7.4.0+ |
| posthog-js | ❌ Need CDN | Will use CDN, not npm |
| trends-benchmarks-dashboard | 🔄 In Progress | Coordinate feature flags |

---

## Technical Notes

### PostHog SDK Version

Python SDK v7.x uses contexts API. Upgrade from v5.x patterns if found.

### Django Middleware Consideration

PostHog offers Django middleware for automatic context. Evaluate if useful:
```python
MIDDLEWARE = [
    ...
    'posthog.django.PostHogMiddleware',
]
```

### Worktree for Changes

Code changes will be made in:
```
/Users/yanchuk/Documents/GitHub/tformance-posthog
```

Branch: `posthog-analytics-integration`

### Reverse Proxy (Future Enhancement)

**Why:** Ad blockers block requests to `*.posthog.com`. A reverse proxy routes PostHog traffic through your own domain, bypassing blockers.

**Implementation Options:**

1. **Django View Proxy** (Simple)
   ```python
   # apps/web/views.py
   @require_POST
   def posthog_proxy(request):
       """Proxy PostHog events through our domain."""
       response = requests.post(
           f"{settings.POSTHOG_HOST}/capture/",
           data=request.body,
           headers={"Content-Type": "application/json"}
       )
       return JsonResponse(response.json(), status=response.status_code)
   ```
   - URL: `/ingest/` → proxies to PostHog
   - Update JS: `api_host: '/ingest'`

2. **Nginx/Cloudflare Proxy** (Production)
   ```nginx
   location /ingest/ {
       proxy_pass https://us.i.posthog.com/;
       proxy_set_header Host us.i.posthog.com;
   }
   ```

3. **PostHog Cloud Proxy** (Managed)
   - PostHog offers `us.i.posthog.com` which some blockers don't target
   - Already using this as default host

**Priority:** Low - implement after validating analytics value. Most users (CTOs, enterprise) don't use ad blockers on work devices.

**Task Tracking:** Add to Phase 7 or create separate follow-up task.

---

## Resources

- [PostHog Django Docs](https://posthog.com/docs/libraries/django)
- [PostHog Python SDK](https://posthog.com/docs/libraries/python)
- [PostHog Session Replay](https://posthog.com/docs/session-replay)
- [PostHog Surveys](https://posthog.com/docs/surveys)
- [Django Analytics Tutorial](https://posthog.com/tutorials/django-analytics)
