# PostHog Analytics Integration - Context

**Last Updated:** 2025-12-25

---

## Quick Reference

### Worktree Location
```
/Users/yanchuk/Documents/GitHub/tformance-posthog
```

### Branch
```
posthog-analytics-integration
```

### PostHog Config (from .env)
```
POSTHOG_API_KEY=""      # Set your key
POSTHOG_HOST="https://us.i.posthog.com"
```

---

## Key Files to Modify

### Backend (Django)

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `tformance/settings.py:692-701` | PostHog init | Already configured |
| `apps/web/context_processors.py` | Template context | Add `posthog_config` processor |
| `apps/users/signals.py` | User lifecycle | Add identify/group calls |
| `apps/onboarding/views.py` | Onboarding flow | Add step tracking events |
| `apps/integrations/views/` | OAuth flows | Add connection events |
| `apps/metrics/views/analytics_views.py` | Dashboard views | Add page view events |
| `apps/subscriptions/views.py` | Billing | Add subscription events |

### Frontend (Templates)

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `templates/web/base.html` | Base template | Add PostHog JS snippet |
| `templates/web/components/` | May need new component | `posthog_init.html` partial |
| `templates/onboarding/*.html` | Onboarding steps | Data attributes for autocapture |
| `templates/metrics/analytics/*.html` | Analytics pages | Data attributes for tab tracking |

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/utils/analytics.py` | PostHog helper functions |
| `templates/web/components/posthog_init.html` | JS initialization partial |

---

## Related Ongoing Work

### trends-benchmarks-dashboard

**Status:** In progress (see `dev/active/trends-benchmarks-dashboard/`)

**Coordination Needed:**
- Feature flag `trends-dashboard` should be created in PostHog
- Tracking events for new trends features should be added
- Phase 5 (Actionable Insights) will need analytics

**Key Files:**
- `apps/metrics/views/trends_views.py` (to be created)
- `templates/metrics/analytics/trends/` (to be created)

### repo-language-tech-detection

**Status:** In progress

**No coordination needed** - this is backend-only work

---

## PostHog JavaScript Snippet

Use this in `templates/web/components/posthog_init.html`:

```html
{% if POSTHOG_API_KEY %}
<script>
!function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],u.toString=function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e},u.people.toString=function(){return u.toString(1)+".people (stub)"},o="init push capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSurveys onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug getPageViewId".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);

posthog.init('{{ POSTHOG_API_KEY }}', {
    api_host: '{{ POSTHOG_HOST }}',
    person_profiles: 'identified_only',
    capture_pageview: true,
    capture_pageleave: true,
    autocapture: true,
    session_recording: {
        maskAllInputs: true,
        maskInputOptions: {
            password: true,
            email: false,  // Show email for user identification
        },
    },
    loaded: function(posthog) {
        {% if user.is_authenticated %}
        posthog.identify('{{ user.id }}', {
            email: '{{ user.email }}',
            name: '{{ user.get_full_name }}',
        });
        {% if team %}
        posthog.group('team', '{{ team.slug }}', {
            name: '{{ team.name }}',
        });
        {% endif %}
        {% endif %}
    }
});
</script>
{% endif %}
```

---

## Event Naming Conventions

### Format
`<noun>_<past_tense_verb>` (e.g., `user_signed_up`, `dashboard_viewed`)

### Standard Properties

Always include when applicable:

```python
{
    "team_slug": team.slug,        # Which team
    "user_role": "admin|member",    # User's role
    "$current_url": request.path,   # Page context
}
```

---

## Privacy Considerations

### Data We Track

- User ID, email, name (for identification)
- Team slug, name, plan (for group analytics)
- Page views, button clicks (autocapture)
- Session recordings (masked inputs)

### Data We DON'T Track

- OAuth tokens (never sent to PostHog)
- GitHub/Jira/Slack data content
- Survey response content to PostHog (we have our own DB)
- API keys, secrets

### Excluded Pages from Recording

```javascript
// Don't record on these paths
const RECORDING_EXCLUDE = [
    '/accounts/',       // Auth pages
    '/admin/',          // Django admin
    '/api/',            // API endpoints
    '/__reload__/',     // Dev reload
];
```

---

## Testing Strategy

### Manual Testing

1. **Enable in dev:** Set `POSTHOG_API_KEY` in `.env`
2. **View live events:** PostHog Dashboard → Events → Live
3. **Check recordings:** PostHog Dashboard → Recordings
4. **Verify user props:** PostHog Dashboard → Persons → Search

### Unit Tests

Mock PostHog calls in tests:

```python
from unittest.mock import patch

class TestAnalytics(TestCase):
    @patch('posthog.capture')
    def test_signup_tracks_event(self, mock_capture):
        # ... signup user ...
        mock_capture.assert_called_once_with(
            distinct_id=user.id,
            event='user_signed_up',
            properties={'method': 'email'}
        )
```

---

## Rollout Plan

### Week 1: Internal Testing
- Deploy to staging
- Team uses product normally
- Review event data quality
- Fix any issues

### Week 2: Gradual Rollout
- Enable for 25% of users (feature flag)
- Monitor performance impact
- Monitor PostHog usage/costs

### Week 3: Full Rollout
- Enable for 100%
- Set up dashboards in PostHog
- Create key funnels
- Set up alerts

---

## PostHog Dashboard Setup

### Key Dashboards to Create

1. **Onboarding Funnel**
   - Conversion rates per step
   - Drop-off points
   - Time to complete

2. **Weekly Engagement**
   - DAU/WAU/MAU
   - Session count trends
   - Feature usage breakdown

3. **Activation Metrics**
   - Time to first dashboard view
   - Time to first survey response
   - Integration connection rates

---

## References

### Documentation
- [PostHog Django Integration](https://posthog.com/docs/libraries/django)
- [PostHog Session Replay](https://posthog.com/docs/session-replay)
- [PostHog Surveys](https://posthog.com/docs/surveys/installation)
- [PostHog Python V6 Migration](https://posthog.com/tutorials/python-v6-migration)

### Project Docs
- `prd/PRD-MVP.md` - Product requirements
- `prd/ONBOARDING.md` - Onboarding flow details
- `prd/DASHBOARDS.md` - Dashboard specifications
- `CLAUDE.md` - Coding guidelines

### Related Tasks
- `dev/active/trends-benchmarks-dashboard/` - Trends feature work
