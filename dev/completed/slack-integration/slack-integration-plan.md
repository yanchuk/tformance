# Phase 4: Slack Integration Plan

> Last Updated: 2025-12-12

## Executive Summary

Phase 4 implements Slack integration for the AI Impact Analytics Platform, enabling:
1. **PR Surveys** - Ask PR authors about AI assistance and reviewers for quality ratings + AI detection
2. **Reveal Mechanism** - Show reviewers if their AI detection guess was correct
3. **Weekly Leaderboard** - Post team rankings to a configured Slack channel

This is a HIGH complexity phase per IMPLEMENTATION-PLAN.md due to interactive, real-time, multiple flows.

## Current State Analysis

### Completed Prerequisites
- ✅ **Phase 0**: Foundation (auth, accounts)
- ✅ **Phase 1**: Core Data Models (TeamMember, PRSurvey, PRSurveyReview models exist)
- ✅ **Phase 2**: GitHub Integration (OAuth, webhooks, PR sync)
- ✅ **Phase 3**: Jira Integration (OAuth, issue sync, user matching)

### Existing Infrastructure
- `IntegrationCredential` model supports `PROVIDER_SLACK = "slack"`
- `TeamMember.slack_user_id` field exists for Slack user matching
- `PRSurvey` and `PRSurveyReview` models exist in `apps/metrics/models.py`
- OAuth pattern established (GitHub, Jira) - same pattern applies to Slack
- Celery tasks infrastructure ready for async message sending

### Data Model Ready
```python
# apps/metrics/models.py - Already exists
class PRSurvey:
    pull_request = OneToOneField(PullRequest)
    author = ForeignKey(TeamMember)
    author_ai_assisted = BooleanField(null=True)  # null = not responded
    author_responded_at = DateTimeField(null=True)

class PRSurveyReview:
    survey = ForeignKey(PRSurvey)
    reviewer = ForeignKey(TeamMember)
    quality_rating = IntegerField(choices=QUALITY_CHOICES)  # 1/2/3
    ai_guess = BooleanField(null=True)  # Reviewer's guess
    guess_correct = BooleanField(null=True)  # Calculated after author responds
    responded_at = DateTimeField(null=True)
```

## Proposed Architecture

### Component Structure

```
apps/integrations/
├── services/
│   ├── slack_oauth.py       # OAuth flow (new)
│   ├── slack_client.py      # slack-sdk client wrapper (new)
│   ├── slack_surveys.py     # Survey message sending/handling (new)
│   ├── slack_leaderboard.py # Leaderboard computation + posting (new)
│   └── slack_user_matching.py  # Match Slack users to TeamMembers (new)
├── webhooks/
│   └── slack_interactions.py  # Handle button clicks (new)
├── tests/
│   ├── test_slack_oauth.py
│   ├── test_slack_client.py
│   ├── test_slack_surveys.py
│   ├── test_slack_leaderboard.py
│   ├── test_slack_user_matching.py
│   └── test_slack_interactions.py
└── models.py                 # Add SlackIntegration model

apps/metrics/
└── services/
    └── survey_service.py     # Survey business logic (new)
```

### Data Flow

```
PR Merged (GitHub Webhook)
    │
    ▼
sync_repository_task() → Creates PullRequest record
    │
    ▼
post_pr_survey_task() → Looks up Slack IDs → Sends DMs via slack-sdk
    │
    ├── Author DM: "Was this PR AI-assisted? [Yes] [No]"
    └── Reviewer DMs: "Quality rating? AI guess?"

Button Click (Slack Interaction)
    │
    ▼
/slack/interactions endpoint → slack_interactions.py
    │
    ▼
Record response → Check if both responded → Send reveal (if applicable)
```

## Implementation Phases

### Section 1: SlackIntegration Model
**Effort: S | Dependencies: None**

Create model to store Slack workspace configuration.

```python
class SlackIntegration(BaseTeamModel):
    credential = OneToOneField(IntegrationCredential, CASCADE)
    workspace_id = CharField(max_length=20, db_index=True)  # T12345678
    workspace_name = CharField(max_length=255)
    bot_user_id = CharField(max_length=20)  # U12345678 (bot's Slack ID)
    leaderboard_channel_id = CharField(max_length=20, blank=True)  # C12345678
    leaderboard_day = IntegerField(default=0)  # 0=Monday, 6=Sunday
    leaderboard_time = TimeField(default=time(9, 0))  # 09:00
    leaderboard_enabled = BooleanField(default=True)
    surveys_enabled = BooleanField(default=True)
    reveals_enabled = BooleanField(default=True)
    last_sync_at = DateTimeField(null=True, blank=True)
    sync_status = CharField(choices=SYNC_STATUS_CHOICES)
```

**Acceptance Criteria:**
- [ ] Model with all fields per spec
- [ ] Migration creates table
- [ ] Factory exists
- [ ] Admin registered with inline for TrackedRepository style

---

### Section 2: Slack OAuth Service
**Effort: M | Dependencies: Section 1**

Implement OAuth flow following GitHub/Jira pattern.

**Files:**
- `apps/integrations/services/slack_oauth.py`

**Functions:**
```python
# Constants
SLACK_OAUTH_AUTHORIZE_URL = "https://slack.com/oauth/v2/authorize"
SLACK_OAUTH_TOKEN_URL = "https://slack.com/api/oauth.v2.access"
SLACK_OAUTH_SCOPES = "chat:write users:read users:read.email"

def create_oauth_state(team_id: int) -> str
def verify_oauth_state(state: str) -> dict
def get_authorization_url(team_id: int, redirect_uri: str) -> str
def exchange_code_for_token(code: str, redirect_uri: str) -> dict
    # Returns: {access_token, bot_user_id, team: {id, name}}
```

**Acceptance Criteria:**
- [ ] State creation/verification (signed, tamper-proof)
- [ ] Authorization URL generation with correct scopes
- [ ] Token exchange returns bot token + workspace info
- [ ] Error handling with SlackOAuthError

---

### Section 3: Slack OAuth Views
**Effort: M | Dependencies: Section 2**

Views for OAuth flow (connect, callback, disconnect).

**Files:**
- `apps/integrations/views.py` (add views)
- `apps/integrations/urls.py` (add routes)

**Views:**
```python
@team_admin_required
def slack_connect(request, team_slug):
    # Redirect to Slack OAuth

@login_and_team_required
def slack_callback(request, team_slug):
    # Handle OAuth callback, create SlackIntegration

@team_admin_required
def slack_disconnect(request, team_slug):
    # POST only, delete SlackIntegration

@team_admin_required
def slack_settings(request, team_slug):
    # GET/POST for configuring leaderboard channel, day, time
```

**URL Patterns (team_urlpatterns):**
```python
path("integrations/slack/connect/", slack_connect, name="slack_connect"),
path("integrations/slack/callback/", slack_callback, name="slack_callback"),
path("integrations/slack/disconnect/", slack_disconnect, name="slack_disconnect"),
path("integrations/slack/settings/", slack_settings, name="slack_settings"),
```

**Acceptance Criteria:**
- [ ] Connect redirects to Slack with correct params
- [ ] Callback creates credential + SlackIntegration
- [ ] Disconnect removes integration (POST only)
- [ ] Settings view updates configuration
- [ ] All views require proper auth decorators

---

### Section 4: Slack Client Service
**Effort: M | Dependencies: Section 1**

Wrapper around slack-sdk for common operations.

**Files:**
- `apps/integrations/services/slack_client.py`

**Functions:**
```python
from slack_sdk import WebClient

def get_slack_client(credential: IntegrationCredential) -> WebClient:
    """Create authenticated Slack WebClient."""

def send_dm(client: WebClient, user_id: str, blocks: list) -> dict:
    """Send a direct message to a user."""

def send_channel_message(client: WebClient, channel_id: str, blocks: list) -> dict:
    """Send a message to a channel."""

def get_workspace_users(client: WebClient) -> list[dict]:
    """Fetch all users in workspace. Returns [{id, email, real_name}]"""

def get_user_info(client: WebClient, user_id: str) -> dict:
    """Get user info by Slack user ID."""
```

**Acceptance Criteria:**
- [ ] Client creation with bot token
- [ ] DM sending with Block Kit support
- [ ] Channel message sending
- [ ] User listing with pagination handling
- [ ] Error handling with SlackClientError

---

### Section 5: Slack User Matching
**Effort: S | Dependencies: Section 4**

Match Slack users to TeamMembers by email.

**Files:**
- `apps/integrations/services/slack_user_matching.py`

**Functions:**
```python
def get_slack_users(credential: IntegrationCredential) -> list[dict]:
    """Fetch Slack users with emails."""

def match_slack_user_to_team_member(slack_user: dict, team: Team) -> TeamMember | None:
    """Match by email (case-insensitive)."""

def sync_slack_users(team: Team, credential: IntegrationCredential) -> dict:
    """Sync all Slack users. Returns {matched_count, unmatched_count, unmatched_users}."""
    # Updates TeamMember.slack_user_id
```

**Acceptance Criteria:**
- [ ] Fetch users with email addresses
- [ ] Case-insensitive email matching
- [ ] Updates TeamMember.slack_user_id field
- [ ] Returns match report

---

### Section 6: Survey Message Templates
**Effort: M | Dependencies: Section 4**

Block Kit message templates for surveys.

**Files:**
- `apps/integrations/services/slack_surveys.py`

**Functions:**
```python
def build_author_survey_blocks(pr: PullRequest, survey: PRSurvey) -> list:
    """Build Block Kit blocks for author survey DM."""
    # "Was this PR AI-assisted? [Yes] [No]"

def build_reviewer_survey_blocks(pr: PullRequest, survey: PRSurvey, reviewer: TeamMember) -> list:
    """Build Block Kit blocks for reviewer survey DM."""
    # Quality rating + AI guess buttons

def build_author_thanks_blocks() -> list:
    """Thank you message after author responds."""

def build_reviewer_thanks_blocks() -> list:
    """Thank you message after reviewer responds."""

def build_reveal_correct_blocks(reviewer: TeamMember, was_ai_assisted: bool, accuracy_stats: dict) -> list:
    """Reveal message when guess was correct."""

def build_reveal_wrong_blocks(reviewer: TeamMember, was_ai_assisted: bool, accuracy_stats: dict) -> list:
    """Reveal message when guess was wrong."""
```

**Block Kit Action IDs:**
```python
ACTION_AUTHOR_AI_YES = "author_ai_yes"
ACTION_AUTHOR_AI_NO = "author_ai_no"
ACTION_QUALITY_1 = "quality_1"  # Could be better
ACTION_QUALITY_2 = "quality_2"  # OK
ACTION_QUALITY_3 = "quality_3"  # Super
ACTION_AI_GUESS_YES = "ai_guess_yes"
ACTION_AI_GUESS_NO = "ai_guess_no"
```

**Acceptance Criteria:**
- [ ] Author survey with action buttons
- [ ] Reviewer survey with quality + AI guess buttons
- [ ] Thank you messages
- [ ] Reveal messages (correct/wrong variants)
- [ ] All blocks use proper Block Kit format

---

### Section 7: Survey Service
**Effort: M | Dependencies: Section 6**

Business logic for creating/managing surveys.

**Files:**
- `apps/metrics/services/survey_service.py`

**Functions:**
```python
def create_pr_survey(pull_request: PullRequest) -> PRSurvey:
    """Create survey for a merged PR."""

def record_author_response(survey: PRSurvey, ai_assisted: bool) -> None:
    """Record author's AI-assisted response."""

def create_reviewer_survey(survey: PRSurvey, reviewer: TeamMember) -> PRSurveyReview:
    """Create reviewer survey entry."""

def record_reviewer_response(survey_review: PRSurveyReview, quality: int, ai_guess: bool) -> None:
    """Record reviewer's response and calculate guess_correct if author responded."""

def check_and_send_reveal(survey: PRSurvey, survey_review: PRSurveyReview) -> bool:
    """Check if reveal should be sent, send if appropriate. Returns True if sent."""

def get_reviewer_accuracy_stats(reviewer: TeamMember) -> dict:
    """Get reviewer's guess accuracy stats. Returns {correct, total, percentage}."""
```

**Acceptance Criteria:**
- [ ] Survey creation for merged PRs
- [ ] Author response recording
- [ ] Reviewer response recording + guess_correct calculation
- [ ] Reveal trigger logic (both responded + reveals_enabled)
- [ ] Accuracy stats calculation

---

### Section 8: Slack Interactions Webhook
**Effort: L | Dependencies: Section 6, 7**

Handle button clicks from Slack.

**Files:**
- `apps/integrations/webhooks/slack_interactions.py`
- `apps/integrations/urls.py` (add webhook route)

**Views:**
```python
@csrf_exempt
def slack_interactions(request):
    """Handle Slack interaction payloads (button clicks)."""
    # 1. Verify Slack signature
    # 2. Parse payload
    # 3. Route to appropriate handler based on action_id
    # 4. Return acknowledgment (empty 200)
```

**Handlers:**
```python
def handle_author_response(payload: dict) -> None:
    """Handle author AI-assisted response."""

def handle_reviewer_response(payload: dict) -> None:
    """Handle reviewer quality + AI guess response."""
```

**URL Pattern (urlpatterns - not team-scoped):**
```python
path("webhooks/slack/interactions/", slack_interactions, name="slack_interactions"),
```

**Acceptance Criteria:**
- [ ] Signature verification using signing secret
- [ ] Payload parsing (form-urlencoded with JSON payload)
- [ ] Action routing by action_id
- [ ] Author response handling
- [ ] Reviewer response handling
- [ ] Reveal sending when appropriate
- [ ] Duplicate response handling (ignore)

---

### Section 9: PR Survey Celery Tasks
**Effort: M | Dependencies: Section 6, 7, 8**

Async tasks for sending surveys.

**Files:**
- `apps/integrations/tasks.py` (add tasks)

**Tasks:**
```python
@shared_task
def send_pr_surveys_task(pull_request_id: int) -> dict:
    """Send surveys for a merged PR.

    Returns: {author_sent, reviewers_sent, errors}
    """
    # 1. Get PR and check if merged
    # 2. Get SlackIntegration for team
    # 3. Create PRSurvey
    # 4. Send author DM (if slack_user_id exists)
    # 5. Send reviewer DMs (for each reviewer with slack_user_id)

@shared_task
def send_reveal_task(survey_review_id: int) -> dict:
    """Send reveal message to a reviewer.

    Returns: {sent: bool, error: str | None}
    """

@shared_task
def sync_slack_users_task(team_id: int) -> dict:
    """Sync Slack users to TeamMembers for a team."""
```

**Acceptance Criteria:**
- [ ] Survey sending task dispatched on PR merge
- [ ] Author DM sent (skip if no slack_user_id)
- [ ] Reviewer DMs sent (skip those without slack_user_id)
- [ ] Reveal task sends message
- [ ] User sync task works

---

### Section 10: Weekly Leaderboard
**Effort: M | Dependencies: Section 4, 7**

Compute and post weekly leaderboard.

**Files:**
- `apps/integrations/services/slack_leaderboard.py`

**Functions:**
```python
def compute_weekly_leaderboard(team: Team, week_start: date) -> dict:
    """Compute leaderboard data for a week.

    Returns: {
        top_guessers: [{name, correct, total, percentage}],
        team_stats: {prs_merged, ai_percentage, detection_rate, avg_rating},
        quality_champions: [{name, super_count}, {name, fastest_review_hours}]
    }
    """

def build_leaderboard_blocks(leaderboard_data: dict, date_range: str) -> list:
    """Build Block Kit blocks for leaderboard message."""

def should_post_leaderboard(integration: SlackIntegration) -> bool:
    """Check if leaderboard should be posted now (day + time match)."""
```

**Celery Task:**
```python
@shared_task
def post_weekly_leaderboards_task() -> dict:
    """Check all teams and post leaderboards where appropriate.

    Returns: {teams_checked, leaderboards_posted, errors}
    """
```

**Celery Beat Schedule:**
```python
"check-leaderboards-hourly": {
    "task": "apps.integrations.tasks.post_weekly_leaderboards_task",
    "schedule": schedules.crontab(minute=0),  # Every hour on the hour
}
```

**Acceptance Criteria:**
- [ ] Leaderboard computation (top guessers, stats, champions)
- [ ] Block Kit message formatting per SLACK-BOT.md spec
- [ ] Scheduled posting based on team settings
- [ ] Edge cases: <3 participants, no PRs, small team

---

### Section 11: GitHub Webhook Integration
**Effort: S | Dependencies: Section 9**

Trigger surveys when PR is merged.

**Files:**
- `apps/integrations/services/github_webhooks.py` (modify)

**Changes:**
```python
def handle_pull_request_event(payload: dict) -> dict:
    # Existing logic...

    # ADD: Dispatch survey task when PR is merged
    if action == "closed" and payload["pull_request"]["merged"]:
        send_pr_surveys_task.delay(pull_request.id)
```

**Acceptance Criteria:**
- [ ] Survey task dispatched on PR merge webhook
- [ ] Only triggers for merged PRs (not closed without merge)

---

### Section 12: UI Integration
**Effort: S | Dependencies: Sections 1-3**

Update integrations home to show Slack status.

**Files:**
- `apps/integrations/views.py` (modify integrations_home)
- `templates/integrations/home.html` (modify)
- `templates/integrations/slack_settings.html` (new)

**Changes:**
- Add Slack card to integrations home (like GitHub/Jira)
- Show connected status, workspace name
- Link to settings page for configuration
- Settings page with channel picker, day/time selectors

**Acceptance Criteria:**
- [ ] Slack card shows connected/not connected
- [ ] Settings link when connected
- [ ] Settings page allows configuration
- [ ] Channel selection via dropdown

---

## Risk Assessment

### High Risk
| Risk | Mitigation |
|------|------------|
| Slack rate limits (1 msg/sec) | Queue messages, implement backoff |
| Signature verification complexity | Use slack-sdk built-in verification |
| Interactive message state | Include survey_id in action value |

### Medium Risk
| Risk | Mitigation |
|------|------------|
| User email mismatch | Allow manual matching in admin |
| Self-merge edge case | Send combined author+reviewer survey |
| Duplicate responses | Check responded_at before processing |

### Low Risk
| Risk | Mitigation |
|------|------------|
| Bot token storage | Use existing IntegrationCredential encryption |
| Timezone handling | Store in UTC, convert for display |

## Success Metrics

- [ ] Slack OAuth flow works end-to-end
- [ ] Surveys sent within 1 minute of PR merge
- [ ] >90% button click responses recorded correctly
- [ ] Leaderboard posts on configured schedule
- [ ] All tests pass (target: ~60 new tests)

## Required Resources

### Dependencies
```
slack-sdk>=3.30.0
```

### Environment Variables
```
SLACK_CLIENT_ID=<from Slack app settings>
SLACK_CLIENT_SECRET=<from Slack app settings>
SLACK_SIGNING_SECRET=<from Slack app settings>
```

### Slack App Configuration
1. Create Slack App at api.slack.com
2. OAuth Scopes: `chat:write`, `users:read`, `users:read.email`
3. Enable Interactivity with request URL: `https://yourapp.com/webhooks/slack/interactions/`
4. Install to workspace during OAuth flow

## Test Coverage Plan

| Section | Test File | Est. Tests |
|---------|-----------|------------|
| 1. Model | test_models.py | 8 |
| 2. OAuth Service | test_slack_oauth.py | 12 |
| 3. OAuth Views | test_slack_views.py | 16 |
| 4. Client Service | test_slack_client.py | 10 |
| 5. User Matching | test_slack_user_matching.py | 8 |
| 6. Survey Templates | test_slack_surveys.py | 12 |
| 7. Survey Service | test_survey_service.py | 14 |
| 8. Interactions | test_slack_interactions.py | 16 |
| 9. Tasks | test_slack_tasks.py | 12 |
| 10. Leaderboard | test_slack_leaderboard.py | 10 |
| 11. Webhook Trigger | test_github_webhooks.py | 4 |
| **Total** | | **~122** |

## Implementation Order

```
Section 1 (Model) ─────────────┐
                               │
Section 2 (OAuth Service) ─────┼─→ Section 3 (OAuth Views)
                               │
Section 4 (Client) ────────────┼─→ Section 5 (User Matching)
                               │
                               └─→ Section 6 (Templates) ─┐
                                                          │
                                      Section 7 (Service) ┼─→ Section 8 (Interactions)
                                                          │
                                                          └─→ Section 9 (Tasks)
                                                               │
                                                               └─→ Section 11 (Webhook)

Section 10 (Leaderboard) ─────────→ (can be parallel after Section 4)

Section 12 (UI) ─────────────────→ (can be parallel after Section 3)
```

**Recommended Build Order:**
1. Sections 1-3: Model + OAuth (foundation)
2. Sections 4-5: Client + User matching
3. Sections 6-7: Templates + Service logic
4. Sections 8-9: Interactions + Tasks (core flow)
5. Sections 10-11: Leaderboard + Webhook trigger
6. Section 12: UI polish
