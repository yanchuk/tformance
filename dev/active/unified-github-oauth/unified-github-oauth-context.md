# Unified GitHub OAuth - Context

**Last Updated:** 2025-12-28

## Key Files

### Onboarding OAuth Flow
| File | Purpose |
|------|---------|
| `apps/onboarding/views.py:91-116` | `github_connect` - initiates OAuth for onboarding |
| `apps/onboarding/views.py:118-191` | `github_callback` - handles callback, creates team |
| `apps/onboarding/views.py:44-72` | State creation/verification (`_create_onboarding_state`, `_verify_onboarding_state`) |
| `apps/onboarding/urls.py` | URL patterns for `/onboarding/github/callback/` |

### Integration OAuth Flow
| File | Purpose |
|------|---------|
| `apps/integrations/views/github.py:28-58` | `github_connect` - initiates OAuth for existing team |
| `apps/integrations/views/github.py:61-128` | `github_callback` - handles callback, creates integration |
| `apps/integrations/services/github_oauth.py:44-104` | State creation/verification with team_id |
| `apps/integrations/urls.py` | URL patterns for `/app/<team>/integrations/github/callback/` |

### Shared OAuth Services
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_oauth.py` | OAuth URL building, token exchange, API calls |
| `apps/integrations/services/encryption.py` | Token encryption/decryption |
| `apps/integrations/views/helpers.py` | Shared helper functions |

## Key Decisions

### Decision 1: Single Callback at `/auth/github/callback/`
**Rationale:**
- GitHub OAuth Apps support only one callback URL
- Subdirectory paths work, but having a single dedicated auth endpoint is cleaner
- Separates authentication concerns from app-specific logic

### Decision 2: Use `type` Field in State Parameter
**Rationale:**
- Simple discriminator between flows
- State already contains `team_id` for integration flow
- Onboarding flow doesn't have team_id (team doesn't exist yet)

### Decision 3: Keep Existing Post-Callback Logic Separate
**Rationale:**
- Onboarding creates team, stores token in session, continues wizard
- Integration creates credential in DB, redirects to integrations home
- Different security decorators needed
- Logic is different enough to warrant separate handler functions

## State Parameter Formats

### Current Onboarding State
```python
# Created in apps/onboarding/views.py:44-53
payload = {"type": "onboarding"}
# Base64 encoded and signed with Django Signer
```

### Current Integration State
```python
# Created in apps/integrations/services/github_oauth.py:44-63
payload = {"team_id": team_id, "iat": timestamp}
# Base64 encoded and signed with Django Signer
```

### Proposed Unified State
```python
# Onboarding
{"type": "onboarding", "iat": timestamp}

# Integration
{"type": "integration", "team_id": team_id, "iat": timestamp}
```

## Dependencies

### Internal Dependencies
- `apps.teams.models.Team` - Team creation in onboarding
- `apps.teams.models.Membership` - Adding user as admin
- `apps.integrations.models.IntegrationCredential` - Token storage
- `apps.integrations.models.GitHubIntegration` - Integration record
- `apps.integrations.services.encryption` - Token encryption

### External Dependencies
- GitHub OAuth App configuration (need to update callback URL)

## Test Coverage

### Existing Tests
| File | Coverage |
|------|----------|
| `apps/onboarding/tests/` | Onboarding flow tests |
| `apps/integrations/tests/test_github_oauth.py` | OAuth service tests |
| `apps/integrations/tests/test_github_views.py` | Integration view tests |

### New Tests Needed
- Unified callback routing tests
- State type discrimination tests
- Error handling for invalid state types
- Cross-flow redirect tests

## Security Considerations

1. **State Validation:** Must validate state signature and expiration before routing
2. **Team Access:** Integration flow must verify user has access to team_id in state
3. **Rate Limiting:** Keep existing rate limiting on callback endpoint
4. **CSRF Protection:** State parameter provides CSRF protection

## Jira/Slack Analysis

**No changes needed** - these integrations already use single callback URLs:
- Jira: `/app/<team>/integrations/jira/callback/`
- Slack: `/app/<team>/integrations/slack/callback/`

The onboarding pages for Jira/Slack (`/onboarding/jira/`, `/onboarding/slack/`) are informational pages that link to the main integration connect URLs. They don't have their own OAuth callbacks.
