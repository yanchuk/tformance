# Phase 2.3: Organization Discovery - Context Reference

> Last Updated: 2025-12-10 (Session Complete)

## Current Implementation Status

**Status:** COMPLETE ✅

**Depends on:**
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete

---

## Implementation Summary

Phase 2.3 is fully implemented with:
- 48 new tests added (431 total tests passing)
- Full member sync from GitHub organizations
- Member management UI with HTMX toggle
- Auto-import on OAuth completion
- Manual re-sync capability

### Files Created

| File | Purpose |
|------|---------|
| `apps/integrations/services/member_sync.py` | Member sync service with create/update/count logic |
| `apps/integrations/templates/integrations/github_members.html` | Member list page with DaisyUI styling |
| `apps/integrations/templates/integrations/components/member_row.html` | HTMX partial for toggle |
| `apps/integrations/tests/test_member_sync.py` | 7 tests for sync service |

### Files Modified

| File | Changes |
|------|---------|
| `apps/integrations/services/github_oauth.py` | Added `get_organization_members()`, `get_user_details()`, pagination support |
| `apps/integrations/views.py` | Added 3 new views: `github_members`, `github_members_sync`, `github_member_toggle`; OAuth callback now triggers member sync |
| `apps/integrations/urls.py` | Added 3 new URL patterns for member management |
| `apps/integrations/templates/integrations/home.html` | Added "Members" link with count badge |
| `apps/integrations/tests/test_github_oauth.py` | Added 17 tests for new GitHub API functions |
| `apps/integrations/tests/test_views.py` | Added 24 tests for member views and OAuth sync integration |

---

## Key Decisions Made This Session

### 1. Sync Strategy
**Decision:** Sync inline during OAuth callback (not async)
**Rationale:** Simpler for MVP, acceptable latency for typical org sizes (<100 members)

### 2. User Details Fetching
**Decision:** Fetch user details (name, email) only for NEW members
**Rationale:** Reduces API calls, existing members already have data

### 3. Error Handling
**Decision:** Graceful degradation - OAuth completes even if sync fails
**Rationale:** Don't block OAuth flow for sync errors

### 4. Pagination
**Decision:** Auto-paginate using GitHub's Link header
**Rationale:** Handles orgs of any size transparently

### 5. Private Email Handling
**Decision:** Store empty string when email is None
**Rationale:** Matches existing TeamMember model constraints

---

## New URL Endpoints

```
/a/{team}/integrations/github/members/              → github_members (GET)
/a/{team}/integrations/github/members/sync/         → github_members_sync (POST)
/a/{team}/integrations/github/members/{id}/toggle/  → github_member_toggle (POST)
```

---

## New Service Functions

### github_oauth.py Additions

```python
def get_organization_members(access_token: str, org_slug: str) -> list[dict]:
    """Get all members of a GitHub organization with pagination."""

def get_user_details(access_token: str, username: str) -> dict:
    """Get detailed information about a specific GitHub user."""

def _make_paginated_github_api_request(endpoint: str, access_token: str) -> list[dict]:
    """Make paginated GitHub API request, following Link headers."""

def _parse_next_link(link_header: str | None) -> str | None:
    """Parse GitHub Link header to extract next page URL."""
```

### member_sync.py

```python
def sync_github_members(team, access_token: str, org_slug: str) -> SyncResult:
    """Sync GitHub org members to TeamMember records.

    Returns:
        SyncResult with keys: created, updated, unchanged, failed
    """
```

---

## View Helper Functions

```python
# apps/integrations/views.py

def _sync_github_members_after_connection(team, access_token, org_slug) -> int:
    """Sync members after OAuth, returns created count or 0 on error."""
```

---

## Test Coverage

### test_github_oauth.py (40 tests total, 17 new)
- `TestGetOrganizationMembers` - 11 tests including pagination
- `TestGetUserDetails` - 6 tests

### test_member_sync.py (7 tests, all new)
- Sync creates new members
- Sync updates changed usernames
- Handles private emails
- Returns accurate counts
- Is idempotent
- Continues on partial failures

### test_views.py (110 tests total, 24 new)
- `TestGitHubCallbackMemberSync` - 4 tests
- `GitHubMembersViewTest` - 7 tests
- `GitHubMembersSyncViewTest` - 6 tests
- `GitHubMemberToggleViewTest` - 7 tests

---

## Environment Setup

**Required in .env:**
```bash
INTEGRATION_ENCRYPTION_KEY=<fernet-key>
GITHUB_CLIENT_ID=<github-oauth-app-client-id>
GITHUB_SECRET_ID=<github-oauth-app-secret>
```

---

## Verification Commands

```bash
# Run all tests (431 tests)
make test ARGS='--keepdb'

# Run integrations tests only (177 tests)
make test ARGS='apps.integrations --keepdb'

# Lint check
make ruff

# Check for missing migrations (none needed - no model changes)
make migrations

# Start dev server
make dev
# Visit http://localhost:8000/a/demo-team-1/integrations/
```

---

## Demo Data Setup

```bash
# Seed demo data
uv run python manage.py seed_demo_data --team-slug demo-team-1

# Create GitHub integration for demo
uv run python manage.py shell -c "
from apps.integrations.factories import GitHubIntegrationFactory
from apps.teams.models import Team
team = Team.objects.get(slug='demo-team-1')
GitHubIntegrationFactory(team=team, organization_slug='demo-org')
"
```

---

## Next Phase: 2.4 Repository Selection

After Phase 2.3, the next step is Phase 2.4 which will:
1. Fetch organization repositories from GitHub API
2. Create repository selection UI
3. Store selected repositories for tracking
4. Set up webhook configuration

---

## Session Handoff Notes

**Session Complete:**
- Phase 2.3 Organization Discovery is FULLY IMPLEMENTED
- All 431 tests passing
- All lint checks passing
- No uncommitted migrations needed
- Dev environment verified working

**Ready for Next Session:**
1. Move `dev/active/org-discovery/` to `dev/completed/` (optional)
2. Start Phase 2.4: Repository Selection
3. Or create PR for Phase 2.3 work

**Uncommitted Changes:**
Run `git status` to see all uncommitted files. Key changes:
- New files in `apps/integrations/services/`
- New files in `apps/integrations/templates/`
- Modified `apps/integrations/views.py`, `apps/integrations/urls.py`
- New test files
- Updated dev docs
