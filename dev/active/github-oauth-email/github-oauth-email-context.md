# GitHub OAuth Email Fetching - Context

**Last Updated: 2025-12-29**

## Key Files

### Primary Files to Modify
| File | Purpose | Lines |
|------|---------|-------|
| `apps/integrations/services/github_oauth.py` | GitHub OAuth service - add scope + email fetching | 28-35, 171-200 |
| `apps/auth/views.py` | Login callback - use enhanced email fetching | 156-230 |
| `apps/integrations/tests/test_github_oauth.py` | Tests for GitHub OAuth | New tests |

### Related Files (Reference Only)
| File | Purpose |
|------|---------|
| `tformance/settings.py:350-352` | SOCIALACCOUNT_PROVIDERS GitHub scope (allauth, not our custom OAuth) |
| `apps/auth/oauth_state.py` | OAuth state management |
| `apps/users/models.py` | CustomUser model |

## Key Decisions

### D1: Use PyGithub's get_emails() method
**Decision**: Use PyGithub library instead of raw API calls
**Rationale**:
- Already using PyGithub throughout the codebase
- Handles authentication, rate limiting, pagination
- Type hints and documentation available

### D2: Primary email selection logic
**Decision**: Primary verified > First verified > None
**Rationale**:
- Primary email is user's preferred email
- Only use verified emails to ensure deliverability
- Never use unverified emails for account creation

### D3: Keep placeholder fallback
**Decision**: Keep `username@github.placeholder` as absolute last resort
**Rationale**:
- Some GitHub accounts have no verified emails
- Better to create account with placeholder than fail authentication
- Can prompt user to add email later

### D4: Don't auto-update existing users
**Decision**: Only update email for existing users when they re-authenticate
**Rationale**:
- Avoid changing user data without their action
- User may have intentionally set a different email
- Re-authentication confirms user consent

## Dependencies

### External
- GitHub OAuth API
- PyGithub library

### Internal
- `apps/integrations/services/github_oauth.py` - Core OAuth service
- `apps/auth/views.py` - Authentication views

## API Reference

### GitHub /user/emails Response
```json
[
  {
    "email": "user@example.com",
    "primary": true,
    "verified": true,
    "visibility": "public"
  },
  {
    "email": "user@private.com",
    "primary": false,
    "verified": true,
    "visibility": null
  }
]
```

### PyGithub Usage
```python
from github import Github

github = Github(access_token)
user = github.get_user()
emails = user.get_emails()  # Returns PaginatedList of email dicts
```

## Testing Strategy

### Unit Tests
- Mock PyGithub responses
- Test email selection logic
- Test error handling

### Manual Testing
1. Delete test user from database
2. Initiate GitHub OAuth login
3. Verify real email captured (not placeholder)
4. Check SocialAccount extra_data

## Code Patterns

### Existing Pattern (get_authenticated_user)
```python
def get_authenticated_user(access_token: str) -> dict[str, Any]:
    try:
        github = Github(access_token)
        user = github.get_user()
        return {
            "login": user.login,
            "id": user.id,
            "email": user.email,  # This returns None for private emails
            ...
        }
    except GithubException as e:
        raise GitHubOAuthError(...) from e
```

### New Pattern (get_user_primary_email)
```python
def get_user_primary_email(access_token: str) -> str | None:
    try:
        github = Github(access_token)
        user = github.get_user()
        emails = list(user.get_emails())

        # Find primary verified email
        for email_data in emails:
            if email_data.get("primary") and email_data.get("verified"):
                return email_data["email"]

        # Fallback to first verified email
        for email_data in emails:
            if email_data.get("verified"):
                return email_data["email"]

        return None
    except GithubException as e:
        raise GitHubOAuthError(...) from e
```

## Notes

- The `user:email` scope is already used in the login flow (`GITHUB_LOGIN_SCOPES = "user:email"` in views.py:60)
- The integration flow uses `GITHUB_OAUTH_SCOPES` which needs the scope added
- PyGithub's `user.get_emails()` requires the `user:email` scope to work
