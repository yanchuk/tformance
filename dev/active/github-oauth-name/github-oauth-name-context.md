# Context: GitHub OAuth Name Population

**Last Updated:** 2026-01-18

## Key Files

### Primary Files (Will Modify)
- `apps/auth/views/github.py` - GitHub OAuth callback handlers
  - Line 155: `github_name = github_user.get("name")`
  - Lines 187-190: User creation (needs first_name/last_name)
  - Lines 176-181: SocialAccount linking (stores extra_data)
- `apps/auth/tests/test_github_login.py` - Existing test coverage

### Reference Files (Read Only)
- `apps/users/models.py` - `CustomUser` model (extends AbstractUser)
- `apps/integrations/services/github_oauth.py` - `get_github_user()` API call

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Name parsing strategy | Split on first space | Handles "First Last" and "First van Last" patterns |
| Empty name handling | Store empty strings | Graceful degradation, no errors |
| Field truncation | 150 chars | Django AbstractUser field limit |
| Test approach | TDD (Red-Green-Refactor) | Project standard per CLAUDE.md |

## Dependencies

### Internal
- `CustomUser` model's `first_name`/`last_name` fields (inherited from AbstractUser)
- `get_display_name()` method already checks `get_full_name()` first

### External
- GitHub API `/user` endpoint returns `name` field
- Field may be null if user hasn't set a display name

## GitHub API Response Example

```json
{
  "id": 12345,
  "login": "ianchuk",
  "name": "Ivan Yanchuk",
  "email": "ivan@example.com",
  "avatar_url": "https://avatars.githubusercontent.com/u/12345"
}
```

## Code Flow

```
github_callback()
  └── _handle_login_callback(request, code)
        ├── get_github_user(access_token)  # Returns user dict
        ├── Extract: github_name = github_user.get("name")
        ├── [NEW] Parse: first_name, last_name = _parse_github_name(github_name)
        └── CustomUser.objects.create(
              username=...,
              email=...,
              first_name=first_name,  # [NEW]
              last_name=last_name,    # [NEW]
            )
```

## Test Cases to Add

### Unit Tests: `_parse_github_name()`
| Input | Expected Output |
|-------|-----------------|
| `"Ivan Yanchuk"` | `("Ivan", "Yanchuk")` |
| `"Ivan"` | `("Ivan", "")` |
| `"Ivan van Beethoven"` | `("Ivan", "van Beethoven")` |
| `None` | `("", "")` |
| `""` | `("", "")` |
| `"   "` | `("", "")` |
| `"  Ivan  Yanchuk  "` | `("Ivan", "Yanchuk")` |
| `"A" * 200` | First 150 chars |

### Integration Tests
| Scenario | Verification |
|----------|--------------|
| New user signup with name | `user.first_name == "Ivan"` |
| New user signup without name | `user.first_name == ""` |

## Related Features

- **Weekly Insights Email** (`dev/active/weekly-insights-email/`) - Consumer of first_name for personalization
- **Avatar URL** - Already pulls from `SocialAccount.extra_data` via `CustomUser.avatar_url`
