# Slack Integration Context

> Last Updated: 2025-12-12 (PHASE 4 COMPLETE)

## Status: COMPLETED

Phase 4 Slack Integration is fully implemented and tested.
- **929 tests** total (138 new Slack tests)
- All ruff checks passing
- All migrations applied

---

## Files Created This Session

### Models & Migrations
- `apps/integrations/models.py` (SlackIntegration at lines 368-464)
- `apps/integrations/migrations/0011_slackintegration.py`
- `apps/integrations/migrations/0012_slackintegration_last_sync_error.py`
- `apps/integrations/factories.py` (SlackIntegrationFactory at lines 137-159)

### Services
- `apps/integrations/services/slack_oauth.py` - OAuth flow
- `apps/integrations/services/oauth_utils.py` - Shared OAuth state (DRY with GitHub/Jira)
- `apps/integrations/services/slack_client.py` - WebClient wrapper
- `apps/integrations/services/slack_user_matching.py` - Email-based matching
- `apps/integrations/services/slack_surveys.py` - Block Kit message builders
- `apps/integrations/services/slack_leaderboard.py` - Weekly leaderboard
- `apps/metrics/services/survey_service.py` - Survey business logic

### Webhooks
- `apps/integrations/webhooks/slack_interactions.py` - Button click handlers

### Tests (138 new tests)
- `apps/integrations/tests/test_slack_oauth.py` (14 tests)
- `apps/integrations/tests/test_slack_views.py` (27 tests)
- `apps/integrations/tests/test_slack_client.py` (12 tests)
- `apps/integrations/tests/test_slack_user_matching.py` (8 tests)
- `apps/integrations/tests/test_slack_surveys.py` (13 tests)
- `apps/integrations/tests/test_slack_interactions.py` (16 tests)
- `apps/integrations/tests/test_slack_tasks.py` (12 tests)
- `apps/integrations/tests/test_slack_leaderboard.py` (10 tests)
- `apps/metrics/tests/test_survey_service.py` (14 tests)
- `apps/metrics/tests/test_pr_processor.py` (4 new tests)

### Templates
- `templates/integrations/slack_settings.html`
- `apps/integrations/templates/integrations/home.html` (updated Slack card)

---

## Key Architecture Decisions

### SlackIntegration Model
```python
class SlackIntegration(BaseTeamModel):
    credential = OneToOneField(IntegrationCredential, CASCADE)
    workspace_id = CharField(max_length=20, db_index=True)
    workspace_name = CharField(max_length=255)
    bot_user_id = CharField(max_length=20)
    leaderboard_channel_id = CharField(max_length=20, blank=True)
    leaderboard_day = IntegerField(default=0)  # 0=Monday
    leaderboard_time = TimeField(default=time(9, 0))
    leaderboard_enabled = BooleanField(default=True)
    surveys_enabled = BooleanField(default=True)
    reveals_enabled = BooleanField(default=True)
    last_sync_at = DateTimeField(null=True)
    sync_status = CharField(choices=SYNC_STATUS_CHOICES, default="pending")
    last_sync_error = TextField(null=True, blank=True)
```

### Survey Flow
```
PR Merged (GitHub Webhook)
    ↓
handle_pull_request_event() → _trigger_pr_surveys_if_merged()
    ↓
send_pr_surveys_task.delay(pr_id)
    ↓
Create PRSurvey → Send Author DM → Send Reviewer DMs
    ↓
Button Click → /integrations/webhooks/slack/interactions/
    ↓
record_author_response() / record_reviewer_response()
    ↓
check_and_send_reveal() → send_reveal_task.delay()
```

### Block Kit Action IDs
```python
ACTION_AUTHOR_AI_YES = "author_ai_yes"
ACTION_AUTHOR_AI_NO = "author_ai_no"
ACTION_QUALITY_1 = "quality_1"  # Could be better
ACTION_QUALITY_2 = "quality_2"  # OK
ACTION_QUALITY_3 = "quality_3"  # Super
ACTION_AI_GUESS_YES = "ai_guess_yes"
ACTION_AI_GUESS_NO = "ai_guess_no"
```

### Celery Beat Schedule
```python
"check-leaderboards-hourly": {
    "task": "apps.integrations.tasks.post_weekly_leaderboards_task",
    "schedule": schedules.crontab(minute=0),  # Every hour
    "expire_seconds": 60 * 30,
},
```

---

## URL Patterns

### Team-scoped (in team_urlpatterns)
```
/a/<team_slug>/integrations/slack/connect/
/a/<team_slug>/integrations/slack/callback/
/a/<team_slug>/integrations/slack/disconnect/
/a/<team_slug>/integrations/slack/settings/
```

### Non-team-scoped (in urlpatterns)
```
/integrations/webhooks/slack/interactions/
```

---

## Environment Variables

```python
# settings.py (lines 347-350)
SLACK_CLIENT_ID = env("SLACK_CLIENT_ID", default="")
SLACK_CLIENT_SECRET = env("SLACK_CLIENT_SECRET", default="")
SLACK_SIGNING_SECRET = env("SLACK_SIGNING_SECRET", default="")
```

---

## Shared OAuth Utilities (DRY)

Created `apps/integrations/services/oauth_utils.py`:
```python
def create_oauth_state(team_id: int) -> str:
    """Create signed state with team_id - used by GitHub, Jira, Slack."""

def verify_oauth_state(state: str) -> dict:
    """Verify and decode state - raises ValueError on invalid/tampered."""
```

Used by all three OAuth services to eliminate ~60 lines of duplicate code.

---

## Testing Patterns

### Mocking Slack WebClient
```python
@patch("apps.integrations.services.slack_client.WebClient")
def test_something(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.conversations_open.return_value = {"channel": {"id": "C123"}}
```

### Mocking Signature Verification
```python
@patch("apps.integrations.webhooks.slack_interactions.verify_slack_signature")
def test_handler(mock_verify):
    mock_verify.return_value = True
```

---

## Verification Commands

```bash
# Full test suite
make test ARGS='--keepdb'  # 929 tests

# Slack-specific tests
make test ARGS='apps.integrations.tests.test_slack_oauth --keepdb'
make test ARGS='apps.integrations.tests.test_slack_views --keepdb'
make test ARGS='apps.integrations.tests.test_slack_client --keepdb'
make test ARGS='apps.integrations.tests.test_slack_user_matching --keepdb'
make test ARGS='apps.integrations.tests.test_slack_surveys --keepdb'
make test ARGS='apps.integrations.tests.test_slack_interactions --keepdb'
make test ARGS='apps.integrations.tests.test_slack_tasks --keepdb'
make test ARGS='apps.integrations.tests.test_slack_leaderboard --keepdb'

# Linting
make ruff
```

---

## Next Steps

Phase 4 is COMPLETE. Next phase per IMPLEMENTATION-PLAN.md:

**Phase 5: Basic Dashboard**
- Native dashboards (Chart.js + HTMX)
- Team metrics visualization
- AI correlation views

---

## Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| SDK | slack-sdk v3.39.0 | Official Python SDK |
| Message format | Block Kit | Rich formatting, interactive |
| OAuth state | Shared oauth_utils.py | DRY with GitHub/Jira |
| Survey trigger | PR merge webhook | Real-time, reliable |
| Leaderboard schedule | Per-team settings | Timezone flexibility |
| Reveal timing | Immediate | Per SLACK-BOT.md spec |
