# Slack Onboarding OAuth Integration

**Last Updated:** 2025-12-28

## Overview

Implement Slack OAuth for onboarding step 4, following the unified callback pattern used by GitHub and Jira. User connects Slack, sees workspace confirmation, and SlackIntegration is created.

## Implementation Phases

### Phase 1: OAuth State Management
- Add `FLOW_TYPE_SLACK_ONBOARDING` and `FLOW_TYPE_SLACK_INTEGRATION`
- Add to `VALID_FLOW_TYPES` tuple
- Slack onboarding has optional team_id (like Jira)

### Phase 2: Unified Slack Callback
- Create `slack_callback()` with rate limiting and state validation
- Create `_handle_slack_onboarding_callback()` - exchanges token, creates SlackIntegration
- Create `_handle_slack_integration_callback()` - for post-onboarding
- Add URL pattern in auth urls

### Phase 3: Onboarding View Update
- Update `connect_slack()` to handle `?action=connect`
- Check if Slack already connected
- Update template: enable button, show workspace name

### Phase 4: Integration View Cleanup
- Update `slack_connect()` to use unified state
- Simplify old callback

## OAuth Flow

```
User clicks "Add to Slack" → creates state with FLOW_TYPE_SLACK_ONBOARDING
→ Redirect to Slack OAuth → User approves → /auth/slack/callback/
→ Validate state, exchange code → Create SlackIntegration
→ Redirect to onboarding:complete
```

## Key Files

| File | Change |
|------|--------|
| `apps/auth/oauth_state.py` | Add Slack flow types |
| `apps/auth/views.py` | Add `slack_callback()` and handlers |
| `apps/auth/urls.py` | Add `slack/callback/` URL |
| `apps/onboarding/views.py` | Update `connect_slack()` |
| `templates/onboarding/connect_slack.html` | Enable button |
