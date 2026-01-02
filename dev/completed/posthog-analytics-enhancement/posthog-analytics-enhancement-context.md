# PostHog Analytics Enhancement - Context

**Last Updated:** 2026-01-02

---

## Key Files

### Core Analytics Module
| File | Purpose |
|------|---------|
| `apps/utils/analytics.py` | PostHog wrapper functions (`track_event`, `identify_user`, `group_identify`, `is_feature_enabled`) |
| `apps/utils/tests/test_analytics.py` | Tests for analytics functions |
| `templates/web/components/posthog_init.html` | Frontend JS SDK initialization |

### Files with Existing Tracking
| File | Events Tracked |
|------|----------------|
| `apps/users/signals.py` | `user_signed_up` |
| `apps/onboarding/views.py` | `github_connected`, `onboarding_step_completed`, `onboarding_skipped`, `onboarding_completed`, `slack_configured` |
| `apps/auth/views.py` | `jira_connected`, `slack_connected` |
| `apps/metrics/views/analytics_views.py` | `dashboard_first_view`, `analytics_viewed` |
| `apps/metrics/views/pr_list_views.py` | `pr_list_exported` |

### Files Modified (Completed)
| File | Changes Made |
|------|--------------|
| `apps/auth/views.py` | Added `integration_connected` events, `update_user_properties` calls |
| `apps/integrations/views/github.py` | Added `integration_disconnected` event |
| `apps/integrations/views/jira.py` | Added `integration_disconnected` event |
| `apps/integrations/views/slack.py` | Added `integration_disconnected` event |
| `apps/teams/views/manage_team_views.py` | Added `team_member_invited` event |
| `apps/teams/views/invitation_views.py` | Added `team_member_joined` event, property updates |
| `apps/users/signals.py` | Enhanced signup with initial user properties |
| `apps/utils/analytics.py` | Added `update_user_properties`, `update_team_properties`, `track_error` |
| `apps/utils/middleware.py` | Added `ErrorTrackingMiddleware` for 500 errors |
| `tformance/settings.py` | Registered `ErrorTrackingMiddleware` |

### Files to Modify (Pending)
| File | Changes Needed |
|------|----------------|
| `apps/feedback/views.py` | Add `feedback_submitted` event |
| `apps/insights/views.py` | Add `insight_viewed` event |
| `apps/metrics/views/analytics_views.py` | Add filter change events |
| `apps/metrics/views/pr_list_views.py` | Add `pr_list_filtered` event |
| `assets/javascript/analytics.js` | New file for frontend events |

---

## Key Decisions

### 1. Event Taxonomy Tiers
**Decision:** Implement events in three tiers based on priority
- Tier 1: Critical funnel events (must have)
- Tier 2: Engagement events (should have)
- Tier 3: UX optimization events (nice to have)

**Rationale:** Prevents event bloat, focuses on actionable data first

### 2. Property Standardization
**Decision:** All team-scoped events must include `team_slug`
**Rationale:** Enables team-level analytics and filtering

### 3. User Property Updates
**Decision:** Update user properties on each relevant action (not just signup)
**Rationale:** Keeps user profiles current for accurate segmentation

### 4. Error Tracking Scope
**Decision:** Only track 500 errors, not 404s or client errors
**Rationale:** Focuses on actionable server issues, reduces noise

### 5. Frontend Event Loading
**Decision:** Create separate `analytics.js` module, not inline in templates
**Rationale:** Maintainable, testable, follows project conventions

---

## Dependencies

### Python Dependencies
- `posthog>=7.4.0` - Already installed in pyproject.toml

### JavaScript Dependencies
- PostHog JS SDK - Already loaded via CDN in `posthog_init.html`

### External Services
- PostHog Cloud (`us.i.posthog.com`) - API key in `.env`

---

## Event Properties Reference

### Standard Properties (include in all events)
```python
{
    "team_slug": request.team.slug,  # For team-scoped events
}
```

### User Properties (set via identify_user)
```python
{
    "$email": user.email,  # PostHog reserved
    "$name": user.get_full_name(),  # PostHog reserved
    "role": "admin" | "member",
    "teams_count": user.teams.count(),
    "signup_source": "github" | "email" | "invite",
    "has_connected_github": True | False,
    "has_connected_jira": True | False,
    "has_connected_slack": True | False,
}
```

### Group (Team) Properties (set via group_identify)
```python
{
    "name": team.name,
    "slug": team.slug,
    "plan": "trial" | "starter" | "pro",
    "onboarding_complete": True | False,
    "repos_tracked": TrackedRepository.objects.filter(team=team).count(),
    "total_prs": PullRequest.objects.filter(team=team).count(),
    "ai_adoption_rate": ai_prs / total_prs * 100,  # Calculated
    "member_count": team.members.count(),
}
```

---

## Testing Strategy

### Unit Tests
- Mock PostHog SDK calls
- Verify correct properties are passed
- Test graceful handling when PostHog is unconfigured

### Integration Tests
- Verify events fire on real user actions
- Check user/group properties are updated correctly

### Manual Verification
- Check PostHog dashboard for event appearance
- Verify funnel tracking works end-to-end

---

## PostHog Dashboard Setup (Post-Implementation)

### Funnels to Create
1. **Onboarding Funnel**
   ```
   user_signed_up → github_connected → onboarding_step_completed(repos) → dashboard_first_view
   ```

2. **Integration Adoption Funnel**
   ```
   github_connected → jira_connected → slack_configured
   ```

3. **Activation Funnel**
   ```
   dashboard_first_view → analytics_viewed → pr_list_exported
   ```

### Cohorts to Define
1. **Active Users** - analytics_viewed in last 7 days
2. **Power Users** - pr_list_exported + analytics_viewed (5+ tabs) in last 30 days
3. **At Risk** - No activity in 14+ days after onboarding

---

## Related Documentation

- `prd/DASHBOARDS.md` - Dashboard views that need tracking
- `prd/ONBOARDING.md` - Onboarding flow details
- `dev/completed/posthog-analytics/` - Previous implementation docs
- `CLAUDE.md` - Coding guidelines
