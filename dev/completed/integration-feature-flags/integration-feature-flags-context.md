# Integration Feature Flags - Context

**Last Updated:** 2026-01-03

---

## Key Files

### Existing Files (To Be Modified)

| File | Purpose | Changes Needed |
|------|---------|----------------|
| `apps/integrations/views/status.py` | Integration status views | Add `track_integration_interest`, pass flag context |
| `apps/integrations/urls.py` | URL routing | Add `interest/` route |
| `apps/integrations/templates/integrations/home.html` | Integration page | Use card component, add Google Workspace |
| `apps/onboarding/views.py` | Onboarding wizard | Add `_get_next_onboarding_step()`, flag checks |

### New Files (To Be Created)

| File | Purpose |
|------|---------|
| `apps/teams/migrations/0008_add_integration_flags.py` | Create 4 waffle flags |
| `apps/integrations/services/integration_flags.py` | Flag helpers + IntegrationStatus |
| `apps/integrations/templates/integrations/components/integration_card.html` | Reusable card component |
| `apps/integrations/templates/integrations/partials/interest_confirmed.html` | HTMX response partial |
| `apps/integrations/tests/test_integration_flags.py` | Unit tests for flags |
| `apps/onboarding/tests/test_flag_skip.py` | Onboarding skip tests |

### Reference Files

| File | Purpose |
|------|---------|
| `apps/teams/migrations/0007_add_ai_adoption_survey_flag.py` | Pattern for flag migrations |
| `apps/metrics/services/dashboard_service.py` | Pattern for `should_use_survey_data()` |
| `apps/utils/analytics.py` | PostHog `track_event()` helper |

---

## Dependencies

### Django Waffle
- Used for feature flag management
- Flags stored in `teams.Flag` model (extended from waffle)
- Admin interface at `/admin/teams/flag/`

### PostHog Analytics
- `track_event(user, event_name, properties)` from `apps.utils.analytics`
- Events tracked: `integration_interest_clicked`

### HTMX
- Used for "I'm Interested" button swap
- POST to endpoint, swap button with "Thanks!" partial

---

## Key Decisions

| Decision | Choice | Date | Rationale |
|----------|--------|------|-----------|
| Flag scope | Global only | 2026-01-03 | Team-scoped adds complexity, defer |
| Button text | "I'm Interested" | 2026-01-03 | Clear call-to-action |
| Email collection | Track only | 2026-01-03 | No modal, simpler UX |
| Copilot card | Coming Soon when off | 2026-01-03 | Consistent with other integrations |
| US-6 Graceful Degradation | Removed | 2026-01-03 | User decision - not needed |

---

## Flag Names

```python
FLAG_JIRA = "integration_jira_enabled"
FLAG_COPILOT = "integration_copilot_enabled"
FLAG_SLACK = "integration_slack_enabled"
FLAG_GOOGLE_WORKSPACE = "integration_google_workspace_enabled"
```

**Default State:** All flags have `everyone=None` (disabled by default)

---

## TDD Test Cases

### Flag Helper Tests
- `test_integration_disabled_by_default`
- `test_integration_enabled_when_flag_active`
- `test_google_workspace_always_coming_soon`
- `test_get_enabled_onboarding_steps_none`
- `test_get_enabled_onboarding_steps_both`

### Interest Tracking Tests
- `test_track_interest_success`
- `test_track_interest_invalid_integration`
- `test_track_interest_htmx_returns_partial`

### Onboarding Skip Tests
- `test_jira_step_skipped_when_disabled`
- `test_jira_step_shown_when_enabled`
- `test_slack_step_skipped_when_disabled`

### E2E Tests (Playwright)
- Integration page shows Coming Soon badges
- "I'm Interested" button works and shows "Thanks!"
- Onboarding skips disabled integrations

---

## Integration Benefits Content

### Jira
```python
{
    "name": "Jira",
    "slug": "jira",
    "icon_color": "text-blue-500",
    "description": "Issues and sprint tracking",
    "benefits": [
        {"title": "Sprint velocity", "description": "Track story points delivered per sprint"},
        {"title": "Issue cycle time", "description": "Measure time from start to done"},
        {"title": "PR-to-issue linking", "description": "Connect code changes to business outcomes"},
    ]
}
```

### GitHub Copilot
```python
{
    "name": "GitHub Copilot",
    "slug": "copilot",
    "icon_color": "text-violet-500",
    "description": "AI coding assistant metrics",
    "benefits": [
        {"title": "Acceptance rate", "description": "Track how often suggestions are accepted"},
        {"title": "Lines of code", "description": "Measure AI-generated code volume"},
        {"title": "Time savings", "description": "Estimate productivity gains from AI"},
    ]
}
```

### Slack
```python
{
    "name": "Slack",
    "slug": "slack",
    "icon_color": "text-pink-500",  # Slack's brand color
    "description": "PR surveys and leaderboards",
    "benefits": [
        {"title": "PR surveys via DM", "description": "Quick 1-click surveys to capture AI-assisted PRs"},
        {"title": "Weekly leaderboards", "description": "Gamified AI Detective rankings"},
        {"title": "Higher response rates", "description": "Meet developers where they work"},
    ]
}
```

### Google Workspace
```python
{
    "name": "Google Workspace",
    "slug": "google_workspace",
    "icon_color": "text-green-500",
    "description": "Track communication workload in calendars",
    "benefits": [
        {"title": "Meeting time analysis", "description": "Track time spent in meetings vs coding"},
        {"title": "Focus time patterns", "description": "Identify optimal deep work windows"},
        {"title": "Team availability", "description": "Optimize collaboration windows"},
    ],
    "always_coming_soon": True,  # Always shows Coming Soon
}
```

---

## Onboarding Flow Logic

```
Current Flow:
sync_progress → connect_jira → connect_slack → complete

New Flow (with flags):
sync_progress → [jira if enabled] → [slack if enabled] → complete

Helper Function:
_get_next_onboarding_step(request, current_step):
    if current == "sync_progress":
        if jira_enabled: return "jira"
        elif slack_enabled: return "slack"
        else: return "complete"
    if current == "jira":
        if slack_enabled: return "slack"
        else: return "complete"
    if current == "slack":
        return "complete"
```

---

## Commands

```bash
# Run unit tests for integration flags
make test ARGS='apps.integrations.tests.test_integration_flags'

# Run onboarding skip tests
make test ARGS='apps.onboarding.tests.test_flag_skip'

# Run E2E tests
make e2e-ui  # Interactive mode for debugging

# Apply migration
make migrate

# Enable a flag via Django shell
make shell
>>> from apps.teams.models import Flag
>>> flag = Flag.objects.get(name="integration_jira_enabled")
>>> flag.everyone = True
>>> flag.save()
```
