# Context: GitHub Personal Account Sync Fix

**Last Updated:** 2026-01-18

## Key Files

### Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `apps/integrations/services/member_sync.py` | Member sync service | Add `sync_single_user_as_member()` function |
| `apps/integrations/_task_modules/github_sync.py` | Celery task | Add account_type routing at line ~790 |
| `apps/integrations/tests/test_member_sync.py` | Tests | Add tests for new function |

### Files to Reference (Read-Only)

| File | Purpose |
|------|---------|
| `apps/integrations/services/github_oauth.py:311` | `get_user_details()` - already exists, reuse it |
| `apps/integrations/models/github.py:119` | `GitHubAppInstallation` model with `account_type` field |
| `apps/metrics/models/team_member.py` | `TeamMember` model |
| `apps/metrics/factories.py` | `TeamFactory`, `TeamMemberFactory` for tests |

---

## Key Code References

### Existing `get_user_details()` Function

**Location:** `apps/integrations/services/github_oauth.py:311-341`

```python
def get_user_details(access_token: str, username: str) -> dict[str, Any]:
    """Get detailed information about a specific GitHub user."""
    github = Github(access_token)
    user = github.get_user(username)
    return {
        "login": user.login,
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "avatar_url": user.avatar_url,
        # ... more fields
    }
```

### Existing `SyncResult` TypedDict

**Location:** `apps/integrations/services/member_sync.py:13-19`

```python
class SyncResult(TypedDict):
    """Result of GitHub member synchronization."""
    created: int
    updated: int
    unchanged: int
    failed: int
```

### GitHubAppInstallation Model

**Location:** `apps/integrations/models/github.py`

```python
class GitHubAppInstallation(BaseTeamModel):
    account_type = models.CharField(max_length=20)  # "User" or "Organization"
    account_login = models.CharField(max_length=100)
    account_id = models.BigIntegerField()
    # ...
```

---

## Dependencies

### Python Packages

- `PyGithub` - GitHub API client (already installed)

### Internal Dependencies

- `apps.integrations.services.github_oauth.get_user_details` - Fetch user info
- `apps.metrics.models.TeamMember` - Member model
- `apps.teams.models.Team` - Team model

---

## Test Patterns to Follow

Based on existing `test_member_sync.py`:

```python
class TestSyncSingleUserAsMember(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.access_token = "gho_test_token_12345"
        self.username = "yanchuk"

    @patch("apps.integrations.services.member_sync.get_user_details")
    def test_creates_team_member_for_new_user(self, mock_get_user_details):
        mock_get_user_details.return_value = {
            "login": "yanchuk",
            "id": 12345,
            "name": "Ivan Yanchuk",
            "email": "ivan@example.com",
        }
        # ... test code
```

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Separate function vs modify existing | Separate `sync_single_user_as_member()` | Cleaner separation of concerns |
| Skip member sync for personal accounts | No - create owner as member | PRs need member attribution |
| Handle collaborators on personal repos | No - document limitation | MVP scope, use org for full support |
| Error handling approach | Return `failed=1` | Match existing pattern in `sync_github_members` |

---

## Heroku Commands Reference

```bash
# Check logs for sync errors
heroku logs --tail --app tformance | grep -E "(sync|member|error)"

# Check dyno status
heroku ps --app tformance

# Manual re-sync stuck installations (after fix deployed)
heroku run python manage.py shell --app tformance
>>> from apps.integrations.models import GitHubAppInstallation
>>> from apps.integrations._task_modules.github_sync import sync_github_app_members_task
>>> inst = GitHubAppInstallation.objects.get(account_login="yanchuk")
>>> sync_github_app_members_task(inst.id)
```
