# PostHog Analytics Guide

> Back to [CLAUDE.md](../../CLAUDE.md)

We use PostHog for product analytics. Events are tracked both server-side (Python) and client-side (JavaScript).

## Key Files

| File | Purpose |
|------|---------|
| `apps/utils/analytics.py` | Server-side tracking helpers |
| `apps/utils/middleware.py` | Error tracking middleware |
| `assets/javascript/analytics.js` | Client-side tracking module |
| `templates/web/components/posthog_init.html` | PostHog JS SDK initialization |

## Server-Side Events (Python)

Use helpers from `apps/utils/analytics`:

```python
from apps.utils.analytics import track_event, identify_user, update_user_properties

# Track an event
track_event(user, "pr_list_exported", {"format": "csv", "team_slug": team.slug})

# Update user properties (lightweight, no defaults)
update_user_properties(user, {"has_connected_github": True})
```

## Client-Side Events (JavaScript)

Use the global `TformanceAnalytics` object:

```javascript
// Track custom event
TformanceAnalytics.trackEvent('custom_action', { property: 'value' });

// Track chart interaction (auto-attached to Chart.js instances)
TformanceAnalytics.trackChartInteraction('cycle-time-chart', 'click', { label: 'Week 1', value: 24 });
```

## Event Catalog

| Event | Trigger | Key Properties |
|-------|---------|----------------|
| `integration_connected` | OAuth callback success | `provider`, `team_slug`, `is_reconnect` |
| `integration_disconnected` | User disconnects | `provider`, `team_slug` |
| `team_member_invited` | Invite sent | `team_slug`, `inviter_role` |
| `team_member_joined` | Invite accepted | `team_slug`, `invite_age_days` |
| `analytics_viewed` | Dashboard page view | `tab`, `date_range`, `team_slug` |
| `pr_list_filtered` | Filter applied | `filter_type`, `active_filters_count` |
| `pr_list_exported` | CSV export | `format`, `row_count`, `has_filters` |
| `insight_viewed` | Insight summary/Q&A | `insight_type`, `team_slug` |
| `feedback_submitted` | Feedback form | `category`, `has_text` |
| `repo_filter_applied` | Repo filter used | `tab`, `repo_name` |
| `error_occurred` | 500 errors (middleware) | `error_type`, `path`, `status_code` |
| `chart_interaction` | Chart click (frontend) | `chart_type`, `action`, `data_label` |
| `navigation` | Sidebar click (frontend) | `from_page`, `to_page` |
| `theme_switched` | Theme toggle (frontend) | `new_theme`, `previous_theme` |

## Adding New Events

1. **Backend**: Use `track_event()` from `apps/utils/analytics.py`
2. **Frontend**: Use `TformanceAnalytics.trackEvent()` from `analytics.js`
3. **Always include** `team_slug` for team-scoped events
4. **Document** new events in this table
