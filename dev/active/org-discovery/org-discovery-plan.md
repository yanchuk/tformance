# Phase 2.3: Organization Discovery - Implementation Plan

> Last Updated: 2025-12-10

## Executive Summary

This phase implements automatic discovery of GitHub organization members after OAuth connection. When a team connects their GitHub org, we fetch all org members and create/update TeamMember records in the metrics app. This enables all downstream features (PR tracking, surveys, leaderboards) to work with identified team members.

### Key Outcomes
- Auto-import all GitHub org members on OAuth completion
- Create/update TeamMember records with github_id and github_username
- Display discovered members in integrations UI
- Allow manual member management (activate/deactivate)
- Background sync for member updates

### Dependencies
- Phase 2.1 (Integration App Foundation) - ✅ Complete
- Phase 2.2 (GitHub OAuth Flow) - ✅ Complete

---

## Current State Analysis

### Existing Infrastructure

**Models Available:**
- `TeamMember` (apps/metrics/models.py) - Has `github_username`, `github_id`, `email`, `display_name` fields
- `GitHubIntegration` (apps/integrations/models.py) - Has `organization_slug`, `organization_id`
- `IntegrationCredential` (apps/integrations/models.py) - Stores encrypted OAuth token

**Services Available:**
- `github_oauth.py` - Has `get_user_organizations()`, `_make_github_api_request()` helper
- `encryption.py` - Has `encrypt()`, `decrypt()` functions

**Views Available:**
- `integrations_home` - Shows integration status
- `github_callback` - Completes OAuth flow

### Missing Components
- GitHub API service for fetching org members
- Member sync service
- Member management views/templates
- Background Celery task for periodic sync
- Member list UI in integrations dashboard

---

## Technical Architecture

### Member Discovery Flow
```
OAuth Callback completes (existing)
    │
    ▼
Fetch org members from GitHub API
GET /orgs/{org}/members
    │
    ▼
For each member:
  - Check if TeamMember exists (by github_id)
  - Create or update TeamMember record
  - Set github_username, github_id, display_name
  - Fetch user email if available
    │
    ▼
Display member list in UI
    │
    ▼
Redirect to repo selection (Phase 2.4)
```

### GitHub API Endpoints

| Endpoint | Purpose | Rate Limit Notes |
|----------|---------|------------------|
| `GET /orgs/{org}/members` | List all org members | Paginated (30/page) |
| `GET /users/{username}` | Get user details (email) | 5000/hour authenticated |
| `GET /orgs/{org}/members?filter=all` | Include outside collaborators | Only for org owners |

### Data Mapping

| GitHub Field | TeamMember Field | Notes |
|--------------|------------------|-------|
| `id` | `github_id` | Primary identifier |
| `login` | `github_username` | Username for display |
| `name` (from user) | `display_name` | May require extra API call |
| `email` (from user) | `email` | Often private, may be null |

---

## Implementation Phases

### 2.3.1: GitHub API Service Extension [Effort: S]
Extend the existing github_oauth.py service with org member fetching capabilities.

**Deliverables:**
- `get_organization_members(access_token, org_slug)` function
- `get_user_details(access_token, username)` function
- Pagination handling for large orgs
- Rate limit handling

### 2.3.2: Member Sync Service [Effort: M]
Create a dedicated service for syncing GitHub members to TeamMember records.

**Deliverables:**
- `apps/integrations/services/member_sync.py`
- `sync_github_members(team, access_token, org_slug)` function
- Create/update logic with upsert pattern
- Handle unknown emails gracefully
- Return sync results (created, updated, unchanged)

### 2.3.3: Post-OAuth Member Import [Effort: S]
Trigger member sync automatically after successful OAuth connection.

**Deliverables:**
- Update `github_callback` view to call member sync
- Or redirect to intermediate "Importing members..." page
- Handle sync errors gracefully
- Show success message with member count

### 2.3.4: Member Management Views [Effort: M]
Create views for viewing and managing synced members.

**Deliverables:**
- `github_members` view - List discovered members
- Member list template with status indicators
- Toggle member active/inactive
- Manual re-sync button

### 2.3.5: Member Management Templates [Effort: M]
Create styled templates for member management.

**Deliverables:**
- `integrations/github_members.html` - Member list
- `integrations/components/member_card.html` - Individual member card
- HTMX for inline status toggle
- Empty state for no members

### 2.3.6: Background Sync Task [Effort: M]
Create Celery task for periodic member sync.

**Deliverables:**
- `apps/integrations/tasks.py`
- `sync_github_org_members` Celery task
- Celery beat schedule (daily)
- Error handling and retry logic
- Sync status tracking on GitHubIntegration

---

## API Endpoints

### New Endpoints

| Method | URL | View | Purpose |
|--------|-----|------|---------|
| GET | `/a/{team}/integrations/github/members/` | `github_members` | List discovered members |
| POST | `/a/{team}/integrations/github/members/sync/` | `github_members_sync` | Trigger manual sync |
| POST | `/a/{team}/integrations/github/members/{id}/toggle/` | `github_member_toggle` | Toggle active status |

---

## Data Flow

### Member Sync Logic

```python
def sync_github_members(team, access_token, org_slug):
    """Sync GitHub org members to TeamMember records."""
    results = {"created": 0, "updated": 0, "unchanged": 0}

    # Fetch all org members (paginated)
    members = get_organization_members(access_token, org_slug)

    for gh_member in members:
        # Check if TeamMember exists
        team_member, created = TeamMember.objects.get_or_create(
            team=team,
            github_id=str(gh_member["id"]),
            defaults={
                "github_username": gh_member["login"],
                "display_name": gh_member["login"],  # Update later if name available
                "is_active": True,
            }
        )

        if created:
            results["created"] += 1
            # Fetch user details for email/name
            try:
                user_details = get_user_details(access_token, gh_member["login"])
                if user_details.get("name"):
                    team_member.display_name = user_details["name"]
                if user_details.get("email"):
                    team_member.email = user_details["email"]
                team_member.save()
            except GitHubOAuthError:
                pass  # Keep defaults
        else:
            # Check if update needed
            updated = False
            if team_member.github_username != gh_member["login"]:
                team_member.github_username = gh_member["login"]
                updated = True
            if updated:
                team_member.save()
                results["updated"] += 1
            else:
                results["unchanged"] += 1

    return results
```

---

## Risk Assessment

### High Risk
1. **Large Organizations** (1000+ members)
   - Mitigation: Paginate API calls, background task for initial sync
   - Show progress indicator during sync

2. **Rate Limiting**
   - GitHub API: 5000 requests/hour authenticated
   - Mitigation: Batch user detail requests, cache responses
   - For 100 members + details: ~200 API calls (well within limits)

### Medium Risk
1. **Private Emails**
   - Most GitHub users have private emails
   - Mitigation: Email field is optional, match by github_id instead

2. **Org Permission Changes**
   - Members may leave org between syncs
   - Mitigation: Mark as inactive rather than delete, preserve history

### Low Risk
1. **Network Failures**
   - Mitigation: Retry logic, partial sync resumption
   - Background task with Celery retry

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Member import success rate | >99% | Members imported / members in org |
| Sync time for 100 members | <30s | Time from trigger to completion |
| User detail fetch success | >80% | Users with name/email populated |

---

## Security Considerations

1. **Token Usage**: Only use stored encrypted token for API calls
2. **Member Privacy**: Don't expose emails in UI unless user owns them
3. **Rate Limiting**: Respect GitHub API limits, implement backoff
4. **Audit Logging**: Log sync operations for debugging

---

## Testing Strategy

### Unit Tests
- GitHub API mocking for member fetch
- TeamMember creation/update logic
- Pagination handling
- Error scenarios

### Integration Tests
- Full sync flow with mocked GitHub
- Background task execution
- View rendering with member data

### Manual Testing Checklist
1. Connect GitHub org with OAuth
2. Members auto-imported
3. View member list
4. Toggle member active/inactive
5. Manual re-sync works
6. Large org pagination works

---

## UI/UX Considerations

### Member List Design
- Show avatar (from GitHub), name, username
- Status indicator (active/inactive)
- Last synced timestamp
- Quick toggle for active status

### Integration with Existing UI
- Add "Members" tab/section to integrations dashboard
- Show member count on GitHub card
- Link from GitHub card to member list

---

## File Structure

```
apps/integrations/
├── services/
│   ├── github_oauth.py      # ⬆️ EXTEND - Add member fetching
│   └── member_sync.py       # ❌ CREATE - Member sync logic
├── views.py                 # ⬆️ EXTEND - Add member views
├── urls.py                  # ⬆️ EXTEND - Add member URLs
├── tasks.py                 # ❌ CREATE - Celery tasks
└── templates/
    └── integrations/
        ├── github_members.html           # ❌ CREATE
        └── components/
            └── member_card.html          # ❌ CREATE
```

---

## Dependencies & Prerequisites

### Required Before Starting
- Phase 2.2 complete (OAuth flow working)
- GitHub OAuth app configured in .env
- Celery and Redis running (for background tasks)

### Can Be Done in Parallel
- Repository selection UI (Phase 2.4) can start after 2.3.2

---

## Timeline Considerations

**Critical Path:**
1. GitHub API service extension must be first
2. Member sync service depends on API service
3. Views depend on sync service
4. Background tasks can parallel with views

**Estimated Total Effort:** Medium (2-3 days of focused work)
