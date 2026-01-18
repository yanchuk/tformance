# Weekly Insights Email Feature - Implementation Plan

**Last Updated: 2026-01-18**

## Executive Summary

Implement a weekly email digest that sends team admins a summary of their engineering insights every Monday at 9 AM UTC. The feature leverages existing infrastructure: weekly LLM insights (generated at 6 AM UTC), Resend.com email backend, and Celery beat scheduling.

**TDD Requirement**: This feature MUST be implemented using strict Red-Green-Refactor cycle.

## Current State Analysis

### What Exists
| Component | Status | Location |
|-----------|--------|----------|
| Weekly LLM insights | ✅ Generated | `apps/metrics/tasks.py` - `generate_weekly_insights()` at 6 AM UTC Monday |
| DailyInsight model | ✅ Exists | `apps/metrics/models/insights.py` with `category="llm_insight"`, `comparison_period="7"` |
| Email backend | ✅ Configured | Resend.com via django-anymail |
| Email service pattern | ✅ Pattern exists | `apps/onboarding/services/notifications.py` |
| Celery beat scheduler | ✅ Configured | DatabaseScheduler with `SCHEDULED_TASKS` dict |
| Test pattern for emails | ✅ Exists | `apps/onboarding/tests/test_welcome_email.py` |

### What's Missing
- Email service for weekly insights (`apps/insights/services/weekly_email.py`)
- Tests for email service (`apps/insights/tests/test_weekly_email.py`)
- Celery task in `apps/metrics/tasks.py`
- Scheduled task config in `tformance/settings.py`

## Proposed Future State

### Architecture
```
Monday 6 AM UTC                    Monday 9 AM UTC
       │                                  │
       ▼                                  ▼
┌──────────────────┐              ┌────────────────────┐
│ generate_weekly_ │              │ send_weekly_       │
│ insights()       │──3hr gap───▶│ insight_emails()   │
└──────────────────┘              └────────────────────┘
       │                                  │
       ▼                                  ▼
┌──────────────────┐              ┌────────────────────┐
│ DailyInsight     │              │ Email to all       │
│ (category=       │              │ team admins        │
│  "llm_insight")  │              └────────────────────┘
└──────────────────┘
```

### Email Content
- **Subject**: `Weekly Insight: {headline}`
- **Body**: Greeting, headline, summary, dashboard link
- **Recipients**: All team admins with email addresses

## Implementation Phases (TDD)

### Phase 1: RED - Write Failing Tests (2 TDD cycles)

#### TDD Cycle 1.1: Test `get_latest_weekly_insight()`
Write tests that verify:
- Returns insight when it exists for current Monday
- Returns None when no insight exists
- Filters by team correctly
- Filters by `comparison_period="7"`

#### TDD Cycle 1.2: Test `send_weekly_insight_email()`
Write tests that verify:
- Email sent when insight exists
- No email when insight missing (graceful skip)
- No email when team has no admins with email
- Email content contains headline, summary, dashboard URL
- Multiple admins all receive email
- Returns correct result dict

### Phase 2: GREEN - Implement Minimum Code

#### Step 2.1: Implement `get_latest_weekly_insight()`
Minimum code to make Cycle 1.1 tests pass.

#### Step 2.2: Implement `send_weekly_insight_email()`
Minimum code to make Cycle 1.2 tests pass.

### Phase 3: REFACTOR - Clean Up

- Extract helper functions if needed
- Add logging
- Ensure code follows project patterns

### Phase 4: Integration

#### Step 4.1: Add Celery Task
Add `send_weekly_insight_emails()` to `apps/metrics/tasks.py`

#### Step 4.2: Configure Scheduled Task
Add to `tformance/settings.py`:
- `SCHEDULED_TASKS` entry
- `CELERY_TASK_ROUTES` entry

#### Step 4.3: Bootstrap and Test
Run `bootstrap_celery_tasks` and manual verification

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Insight not ready at email time | Low | Medium | 3-hour buffer between generation (6 AM) and email (9 AM) |
| Email delivery failure | Low | Low | `fail_silently=True`, Sentry monitoring |
| No insight for team | Medium | Low | Graceful skip with logging |
| Wrong insight sent (stale data) | Low | High | Date filter in query (`date=monday`) |

## Success Metrics

- [ ] All TDD tests pass
- [ ] Email received by test team admin
- [ ] Correct content (headline, summary, link)
- [ ] Scheduled task registered in Celery beat
- [ ] No errors in Sentry after first production run

## Required Resources

### Dependencies
- Django 5.2.9 (existing)
- django-anymail with Resend.com (existing)
- Celery with beat scheduler (existing)

### Skills/Agents
- `tdd-test-writer` - RED phase
- `tdd-implementer` - GREEN phase
- `tdd-refactorer` - REFACTOR phase

## Technical Details

### Query for Weekly Insight (CRITICAL)
```python
from datetime import date, timedelta
from apps.metrics.models import DailyInsight

def get_latest_weekly_insight(team):
    today = date.today()
    monday = today - timedelta(days=today.weekday())

    return DailyInsight.objects.filter(  # noqa: TEAM001 - team filter present
        team=team,
        category="llm_insight",
        comparison_period="7",
        date=monday,  # CRITICAL: prevents stale insights
    ).first()
```

### Getting Team Admins
```python
from apps.teams.models import Membership
from apps.teams import roles

def get_team_admins_with_email(team):
    return [
        m.user for m in Membership.objects.filter(
            team=team,
            role=roles.ROLE_ADMIN
        ).select_related('user')
        if m.user.email
    ]
```

### Email Structure
```python
subject = f"Weekly Insight: {insight.metric_value.get('headline', 'Your Team Summary')}"

body = f"""Hi {user.first_name or 'there'},

Here's your weekly engineering insight for {team.name}:

{insight.metric_value.get('headline', '')}

{insight.metric_value.get('detail', '')}

View your full dashboard: {dashboard_url}

Thanks,
The Tformance Team
"""
```

## Future Enhancements (Out of Scope)

- Unsubscribe mechanism (required before public launch)
- HTML email template with branding
- Per-team timezone for send time
- Monthly digest option
