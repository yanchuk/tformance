# GitHub UX Improvement - Context

Last Updated: 2025-12-29

## Key Files

### Primary Files to Modify
| File | Purpose | Changes |
|------|---------|---------|
| `apps/onboarding/views.py` | Onboarding views | Add `has_github_social` context |
| `templates/onboarding/start.html` | Start page template | Conditional messaging |

### Test Files
| File | Purpose |
|------|---------|
| `apps/onboarding/tests/test_views.py` | Main onboarding view tests |
| `apps/onboarding/tests/test_ux_improvements.py` | UX-specific tests (new) |

### Reference Files (Read Only)
| File | Purpose |
|------|---------|
| `apps/allauth_settings.py:35-40` | Login OAuth scopes definition |
| `apps/integrations/services/github_oauth.py:17-25` | Integration OAuth scopes |
| `apps/auth/views.py:45-82` | OAuth callback routing |

## Architecture Context

### Two OAuth Flows

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub OAuth Flows                        │
├──────────────────────────┬──────────────────────────────────┤
│     Login (allauth)      │     Integration (custom)          │
├──────────────────────────┼──────────────────────────────────┤
│ Callback:                │ Callback:                         │
│ /accounts/github/        │ /auth/github/callback/            │
│   login/callback/        │                                   │
├──────────────────────────┼──────────────────────────────────┤
│ Scopes:                  │ Scopes:                           │
│ - profile                │ - read:org                        │
│ - email                  │ - repo                            │
│                          │ - read:user                       │
│                          │ - manage_billing:copilot          │
├──────────────────────────┼──────────────────────────────────┤
│ Purpose:                 │ Purpose:                          │
│ User authentication      │ Full GitHub integration           │
│ (who is this user?)      │ (read repos, PRs, org data)       │
└──────────────────────────┴──────────────────────────────────┘
```

### SocialAccount Model

Django-allauth stores social accounts in `allauth.socialaccount.models.SocialAccount`:

```python
# Example query
from allauth.socialaccount.models import SocialAccount

# Check if user has GitHub social account
has_github = SocialAccount.objects.filter(
    user=request.user,
    provider='github'
).exists()
```

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Detection method | Query SocialAccount | Authoritative source for social logins |
| Template approach | Django if/else | Simple, no JS needed, server-rendered |
| Messaging style | Explanatory | Reduce user confusion about "reconnecting" |

## Testing Strategy

### TDD Approach
1. **RED**: Write failing tests for GitHub-authenticated user messaging
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Clean up if needed

### Test Scenarios
1. Email signup user sees "Connect GitHub"
2. GitHub signup user sees "Grant Repository Access"
3. Both user types can proceed to OAuth flow
4. Context variable correctly set based on SocialAccount presence

## Related PRD References

- `prd/ONBOARDING.md` - Onboarding flow specification
- `prd/ARCHITECTURE.md` - OAuth architecture
