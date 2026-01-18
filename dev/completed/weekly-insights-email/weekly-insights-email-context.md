# Weekly Insights Email - Context & Dependencies

**Last Updated: 2026-01-18**

## Key Files

### Files to Create
| File | Purpose |
|------|---------|
| `apps/insights/services/weekly_email.py` | Email service functions |
| `apps/insights/tests/test_weekly_email.py` | Unit tests (TDD) |

### Files to Modify
| File | Change |
|------|--------|
| `apps/metrics/tasks.py` | Add `send_weekly_insight_emails()` task |
| `tformance/settings.py` | Add scheduled task config and routing |

### Reference Files (Read-Only)
| File | Purpose |
|------|---------|
| `apps/onboarding/services/notifications.py` | Email pattern to follow |
| `apps/onboarding/tests/test_welcome_email.py` | Test pattern to follow |
| `apps/metrics/models/insights.py` | DailyInsight model definition |
| `apps/teams/models.py` | Membership model, BaseTeamModel |
| `apps/teams/roles.py` | `ROLE_ADMIN` constant |
| `apps/metrics/services/insight_llm.py:800` | How `comparison_period` is set |
| `tformance/settings.py:628-698` | `SCHEDULED_TASKS` pattern |
| `dev/guides/TESTING-GUIDE.md` | TDD workflow reference |

## Key Decisions Made

### 1. Task Location
**Decision**: Add task to `apps/metrics/tasks.py` (not create new `apps/insights/tasks.py`)

**Rationale**: All insight-related tasks (`generate_weekly_insights`, `generate_monthly_insights`, `generate_team_llm_insights`) already live in `apps/metrics/tasks.py`. Consistency > separation.

### 2. Recipients
**Decision**: Send to ALL team admins (not just first admin)

**Rationale**: All admins should be informed of team performance. User confirmed this is intentional.

### 3. Email Format
**Decision**: Plain text (no HTML)

**Rationale**: Matches existing email patterns, faster to implement, works in all email clients.

### 4. Schedule
**Decision**: Monday 9 AM UTC (3 hours after insight generation)

**Rationale**:
- Insights generated at 6 AM UTC on Monday
- 3-hour buffer ensures insights are ready
- User selected this timing

### 5. Insight Query
**Decision**: Filter by `date=monday` (not `date__gte=cutoff`)

**Rationale**: Prevents returning stale insights from previous weeks. Critical fix identified in plan review.

## Dependencies

### External Services
- **Resend.com** - Email delivery (via django-anymail)
- **Redis** - Celery broker and result backend

### Internal Dependencies
| Dependency | Used For |
|------------|----------|
| `DailyInsight` model | Query weekly insights |
| `Team` model | Get team info for email |
| `Membership` model | Find team admins |
| `roles.ROLE_ADMIN` | Filter admin memberships |
| `settings.PROJECT_METADATA` | Build dashboard URL |
| `settings.DEFAULT_FROM_EMAIL` | Email sender |

### Task Dependencies
| This Task | Depends On |
|-----------|------------|
| `send_weekly_insight_emails` | `generate_weekly_insights` (runs 3 hours earlier) |

## Code Patterns to Follow

### Email Service Pattern (from `apps/onboarding/services/notifications.py`)
```python
from django.conf import settings
from django.core.mail import send_mail

def send_weekly_insight_email(team: Team) -> dict:
    # 1. Guard: Check preconditions (insight exists, admins have email)
    # 2. Build content: Subject and body from insight data
    # 3. Send: Use send_mail with fail_silently=True
    # 4. Return: Dict with results
```

### Test Pattern (from `apps/onboarding/tests/test_welcome_email.py`)
```python
@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class WeeklyInsightEmailTests(TestCase):
    def setUp(self):
        # Create user, team, membership, insight

    def test_send_email_success(self):
        result = send_weekly_insight_email(self.team)
        self.assertTrue(result["sent_to"] > 0)
        self.assertEqual(len(mail.outbox), 1)
```

### Celery Task Pattern
```python
@shared_task
def send_weekly_insight_emails() -> dict:
    """Send weekly insight emails to all teams. Monday 9 AM UTC."""
    from apps.insights.services.weekly_email import send_weekly_insight_email

    teams = Team.objects.filter(onboarding_complete=True)  # noqa: TEAM001 - system job
    results = {"teams_processed": 0, "emails_sent": 0, "skipped": 0}

    for team in teams:
        result = send_weekly_insight_email(team)
        # ... aggregate results

    return results
```

## Model Structure Reference

### DailyInsight (for weekly insights)
```python
# When querying weekly LLM insights:
DailyInsight.objects.filter(
    team=team,
    category="llm_insight",      # LLM-generated insight
    comparison_period="7",       # Weekly (7 days)
    date=monday,                 # This week's Monday
)

# metric_value JSONField contains:
{
    "headline": "AI adoption grew 15%",
    "detail": "Your team merged 25 PRs this week...",
    "recommendation": "Keep up the momentum!",
    "metric_cards": [...],
    "actions": [...]
}
```

### Membership (for team admins)
```python
# Get admin users with email:
Membership.objects.filter(
    team=team,
    role=roles.ROLE_ADMIN
).select_related('user')
```

## Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `DEFAULT_FROM_EMAIL` | Sender address | `noreply@ianchuk.com` |
| `PROJECT_METADATA.URL` | Base URL for links | `http://localhost:8000` |

## Known Limitations

1. **Fixed UTC time** - No per-team timezone support
2. **No unsubscribe** - Must add before public launch (compliance)
3. **Graceful degradation** - No email if insight generation failed
