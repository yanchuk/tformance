# Slack Onboarding OAuth - Context

**Last Updated:** 2025-12-28

## Key Files

### OAuth State Management
- `apps/auth/oauth_state.py` - Flow types and state creation/verification
- Pattern: `create_oauth_state(flow_type, team_id)` / `verify_oauth_state(state)`

### Auth Views (Callbacks)
- `apps/auth/views.py` - GitHub and Jira unified callbacks
- Pattern: `*_callback()` validates state, routes to `_handle_*_onboarding_callback()` or `_handle_*_integration_callback()`

### Slack OAuth Service
- `apps/integrations/services/slack_oauth.py`
- `exchange_code_for_token(code, redirect_uri)` - returns token data
- `SLACK_OAUTH_SCOPES = "chat:write users:read users:read.email"`

### Onboarding Views
- `apps/onboarding/views.py:505-531` - Current `connect_slack()` stub

### Models
- `apps/integrations/models.py:SlackIntegration` - workspace_id, workspace_name, bot_user_id
- `apps/integrations/models.py:IntegrationCredential` - encrypted tokens

## Existing Patterns

### Jira Onboarding Callback (Reference)
```python
def _handle_jira_onboarding_callback(request, code: str, team_id: int | None):
    # Get user's team
    team = request.user.teams.first()
    # Exchange code for token
    token_data = jira_oauth.exchange_code_for_token(code, callback_url)
    # Create credential
    credential = IntegrationCredential.objects.update_or_create(...)
    # Create integration
    integration = JiraIntegration.objects.update_or_create(...)
    # Track event
    track_event(...)
    # Redirect
    return redirect("onboarding:select_jira_projects")
```

### Slack OAuth Response
```python
{
    "ok": True,
    "access_token": "xoxb-...",
    "bot_user_id": "U12345678",
    "team": {
        "id": "T12345678",
        "name": "Workspace Name"
    }
}
```

## Dependencies

- `django_ratelimit` for rate limiting callbacks
- `apps.integrations.services.slack_oauth` for token exchange
- `apps.integrations.services.encryption` for token storage
