# Phase 2: GitHub Integration - Context Reference

> Last Updated: 2025-12-10 (Session 1 Complete)

## Current Implementation Status

### Phase 2.1: Integration App Foundation ✅ COMPLETE

**What was implemented this session:**
- Created `apps/integrations/` Django app with full structure
- Implemented 3 models using strict TDD (Red-Green-Refactor)
- Created encryption service for OAuth tokens
- Registered all models in Django admin with custom displays
- 52 tests written and passing

**Migrations applied:** 6 migrations (0001 through 0006)

---

## Implemented Models (apps/integrations/models.py)

### IntegrationCredential
```python
class IntegrationCredential(BaseTeamModel):
    PROVIDER_CHOICES = [("github", "GitHub"), ("jira", "Jira"), ("slack", "Slack")]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, db_index=True)
    access_token = models.TextField()  # Store encrypted at application layer
    refresh_token = models.TextField(blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list)
    connected_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["team", "provider"], name="unique_team_provider")]
```

### GitHubIntegration
```python
class GitHubIntegration(BaseTeamModel):
    SYNC_STATUS_CHOICES = [("pending", "Pending"), ("syncing", "Syncing"),
                          ("complete", "Complete"), ("error", "Error")]

    credential = models.OneToOneField(IntegrationCredential, on_delete=models.CASCADE,
                                      related_name="github_integration")
    organization_slug = models.CharField(max_length=100, db_index=True)
    organization_id = models.BigIntegerField()
    webhook_secret = models.CharField(max_length=100)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(max_length=20, choices=SYNC_STATUS_CHOICES, default="pending", db_index=True)
```

### TrackedRepository
```python
class TrackedRepository(BaseTeamModel):
    integration = models.ForeignKey(GitHubIntegration, on_delete=models.CASCADE,
                                    related_name="tracked_repositories")
    github_repo_id = models.BigIntegerField()
    full_name = models.CharField(max_length=255)  # owner/repo format
    is_active = models.BooleanField(default=True)
    webhook_id = models.BigIntegerField(null=True, blank=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [UniqueConstraint(fields=["team", "github_repo_id"], name="unique_team_github_repo")]
```

---

## Encryption Service (apps/integrations/services/encryption.py)

```python
from apps.integrations.services.encryption import encrypt, decrypt

# Encrypt OAuth token before storing
credential.access_token = encrypt(raw_token)

# Decrypt when using
raw_token = decrypt(credential.access_token)
```

**Key configuration in settings.py:**
```python
INTEGRATION_ENCRYPTION_KEY = env(
    "INTEGRATION_ENCRYPTION_KEY",
    default="r8pmePXvrfFN4L_IjvTbZP3hWPTIN0y4KDw2wbuIRYg=" if "test" in sys.argv else None,
)
```

**IMPORTANT:** In production, `INTEGRATION_ENCRYPTION_KEY` MUST be set as environment variable.

---

## File Structure (Current State)

```
apps/integrations/
├── __init__.py
├── admin.py              ✅ Implemented - masked tokens, inlines
├── apps.py               ✅ Configured
├── factories.py          ✅ 4 factories (User, IntegrationCredential, GitHubIntegration, TrackedRepository)
├── models.py             ✅ 3 models implemented
├── views.py              ⏳ Empty - needed for Phase 2.2
├── urls.py               ❌ Not created yet - needed for Phase 2.2
├── migrations/
│   ├── 0001_initial.py                    ✅
│   ├── 0002_alter_...                     ✅
│   ├── 0003_githubintegration.py          ✅
│   ├── 0004_alter_...                     ✅
│   ├── 0005_trackedrepository.py          ✅
│   └── 0006_...                           ✅
├── services/
│   ├── __init__.py       ✅
│   ├── encryption.py     ✅ Implemented with tests
│   ├── github_client.py  ❌ Not created - Phase 2.3
│   ├── github_oauth.py   ❌ Not created - Phase 2.2
│   └── github_sync.py    ❌ Not created - Phase 2.6
├── webhooks/
│   ├── __init__.py       ✅
│   ├── github.py         ❌ Not created - Phase 2.5
│   └── signature.py      ❌ Not created - Phase 2.5
├── tasks.py              ❌ Not created - Phase 2.6/2.7
└── tests/
    ├── __init__.py       ✅
    ├── test_models.py    ✅ 33 tests
    └── test_encryption.py ✅ 19 tests
```

---

## Key Decisions Made This Session

1. **Token Storage**: Using custom `IntegrationCredential` model instead of django-allauth's SocialToken for better team scoping and encryption control.

2. **Encryption**: Fernet symmetric encryption with key from settings. Base64 output is database-safe.

3. **Model Relationships**:
   - IntegrationCredential → GitHubIntegration (1:1)
   - GitHubIntegration → TrackedRepository (1:N)
   - All models extend BaseTeamModel for team isolation

4. **Indexes**: Added strategic indexes on frequently queried fields (provider, organization_slug, sync_status, is_active).

---

## Integration Points (Existing Models)

### With TeamMember (apps/metrics/models.py)
- TeamMember already has `github_username` and `github_id` fields
- After OAuth, create TeamMember records for org members
- Match by `github_id` (primary) or `email` (secondary)

### With PullRequest, PRReview, Commit (apps/metrics/models.py)
- Sync creates/updates these records
- Authors/reviewers linked via TeamMember.github_id lookup
- Calculate cycle_time and review_time on sync

---

## GitHub API Reference

### OAuth Scopes Required
| Scope | Purpose |
|-------|---------|
| `read:org` | List org members, teams |
| `repo` | Read repository data, PRs, commits |
| `read:user` | Read user profile data |

### Key Endpoints (for Phase 2.2+)
```
GET /orgs/{org}/members          # List org members
GET /orgs/{org}/repos            # List repos
GET /repos/{owner}/{repo}/pulls  # List PRs
POST /repos/{owner}/{repo}/hooks # Create webhook
```

---

## Environment Variables Needed

```bash
# Already configured (with test defaults)
INTEGRATION_ENCRYPTION_KEY=xxx   # Fernet key - REQUIRED in production

# Needed for Phase 2.2
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
```

---

## Next Steps (Phase 2.2: GitHub OAuth Flow)

1. Create `apps/integrations/urls.py` with team_urlpatterns
2. Implement OAuth views (connect, callback, disconnect)
3. Configure django-allauth GitHub provider
4. Create OAuth service in `services/github_oauth.py`
5. Add templates for connect flow

---

## Verification Commands

```bash
# Run all tests (should show 306 passing)
make test

# Run integrations tests only (52 tests)
make test ARGS='apps.integrations'

# Check for missing migrations
make migrations  # Should say "No changes detected"

# Verify code style
make ruff
```

---

## Related PRD Documents

- `/prd/IMPLEMENTATION-PLAN.md` - Phase 2 definition
- `/prd/ARCHITECTURE.md` - System architecture, GitHub scopes
- `/prd/DATA-MODEL.md` - Database schema

---

## Session Handoff Notes

**Last completed work:** Phase 2.1 Integration App Foundation - ALL TASKS COMPLETE

**No uncommitted changes** - all work is in files, ready for commit

**No blockers** - ready to proceed with Phase 2.2

**TDD Workflow used:** All models and encryption service implemented with strict Red-Green-Refactor cycle using tdd-test-writer, tdd-implementer, and tdd-refactorer agents.
