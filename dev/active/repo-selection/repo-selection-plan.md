# Phase 2.4: Repository Selection - Implementation Plan

> Last Updated: 2025-12-10

## Executive Summary

This phase implements the repository selection feature, allowing team admins to choose which GitHub repositories to track for metrics collection. After connecting GitHub (Phase 2.2) and importing org members (Phase 2.3), admins can view available repos and select which ones to monitor.

### Key Outcomes
- List all repositories from connected GitHub organization
- Multi-select UI for repository selection
- Store selected repos in TrackedRepository model
- Repository activation/deactivation controls
- Foundation for webhook setup (Phase 2.5) and data sync (Phase 2.6)

### Dependencies
- Phase 2.1 Integration App Foundation ✅ Complete
- Phase 2.2 GitHub OAuth Flow ✅ Complete
- Phase 2.3 Organization Discovery ✅ Complete

---

## Current State Analysis

### Existing Infrastructure

**Models (apps/integrations/models.py)**
- `GitHubIntegration` - Already exists with org slug, credential link
- `TrackedRepository` - Already exists with all required fields:
  - `integration` FK to GitHubIntegration
  - `github_repo_id` BigIntegerField
  - `full_name` CharField (owner/repo format)
  - `is_active` BooleanField
  - `webhook_id` BigIntegerField (for Phase 2.5)
  - `last_sync_at` DateTimeField

**Services (apps/integrations/services/github_oauth.py)**
- `get_organization_members()` - Paginated member fetching
- `get_user_details()` - User details fetching
- `_make_paginated_github_api_request()` - Reusable pagination helper

**Views (apps/integrations/views.py)**
- `integrations_home` - Shows GitHub card with connection status
- `github_members` - Lists org members (from Phase 2.3)

### Missing Components
- GitHub API function to list organization repositories
- Repository listing view
- Repository selection/toggle views
- Repository management templates
- Bulk selection capability

---

## Technical Architecture

### Repository Discovery Flow
```
User navigates to Repositories page
    │
    ▼
Fetch repos from GitHub API
GET /orgs/{org}/repos
    │
    ▼
Display repo list with checkboxes
    │
    ▼
User selects repos to track
    │
    ▼
Create TrackedRepository records
    │
    ▼
Redirect to repos page with success message
```

### GitHub API Endpoints

| Endpoint | Purpose | Rate Limit Notes |
|----------|---------|------------------|
| `GET /orgs/{org}/repos` | List all org repos | Paginated (30/page) |
| `GET /repos/{owner}/{repo}` | Get single repo details | For verification |

### Data Mapping

| GitHub Field | TrackedRepository Field | Notes |
|--------------|-------------------------|-------|
| `id` | `github_repo_id` | Unique identifier |
| `full_name` | `full_name` | owner/repo format |
| `private` | Display only | Show lock icon |
| `description` | Display only | Help users identify repos |
| `language` | Display only | Primary language |
| `updated_at` | Display only | Last activity |

---

## Implementation Phases

### 2.4.1: GitHub API Repository Functions [Effort: S]
Extend github_oauth.py with repository listing capabilities.

**Deliverables:**
- `get_organization_repositories(access_token, org_slug)` function
- Pagination support for large orgs (100+ repos)
- Handle private vs public repos
- Return repo metadata (id, name, description, language, private flag)

### 2.4.2: Repository List View [Effort: M]
Create view to display available repositories.

**Deliverables:**
- `github_repos` view - List all org repos
- Show tracked status for each repo
- Sort by name, filter by tracked/untracked
- Require team admin role for selection actions

### 2.4.3: Repository Selection Views [Effort: M]
Create views for selecting/deselecting repositories.

**Deliverables:**
- `github_repo_toggle` view - Toggle single repo tracking
- `github_repos_bulk` view - Bulk select/deselect
- HTMX support for inline updates
- Create/delete TrackedRepository records

### 2.4.4: Repository Templates [Effort: M]
Create styled templates for repository management.

**Deliverables:**
- `integrations/github_repos.html` - Repository list page
- `integrations/components/repo_card.html` - Individual repo card
- Search/filter functionality
- Empty state for no repos

### 2.4.5: Integration Dashboard Update [Effort: S]
Add repository link to integrations home page.

**Deliverables:**
- "Repositories" link on GitHub card
- Show tracked repo count
- Quick link to repo selection

---

## API Endpoints

### New Endpoints

| Method | URL | View | Purpose |
|--------|-----|------|---------|
| GET | `/a/{team}/integrations/github/repos/` | `github_repos` | List repos with tracked status |
| POST | `/a/{team}/integrations/github/repos/{repo_id}/toggle/` | `github_repo_toggle` | Toggle tracking |
| POST | `/a/{team}/integrations/github/repos/bulk/` | `github_repos_bulk` | Bulk select/deselect |

---

## UI/UX Design

### Repository List Page

```
┌─────────────────────────────────────────────────────────────┐
│ ← Back to Integrations                                      │
│                                                             │
│ GitHub Repositories                                         │
│ Select repositories to track for metrics collection         │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 🔍 Search repositories...          [Show: All ▼]        ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ [Select All] [Deselect All]       Tracking: 5 of 23 repos  │
│                                                             │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ ☑ acme-corp/api-server                           🔒     ││
│ │   REST API backend • Python • Updated 2 days ago        ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ ☐ acme-corp/web-frontend                                ││
│ │   React frontend application • TypeScript • 1 week ago  ││
│ ├─────────────────────────────────────────────────────────┤│
│ │ ☑ acme-corp/mobile-app                          🔒     ││
│ │   iOS and Android app • Swift • 3 days ago              ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│                              [Save Changes]                 │
└─────────────────────────────────────────────────────────────┘
```

### Empty State
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                         📁                                  │
│                                                             │
│              No repositories found                          │
│                                                             │
│    Your GitHub organization doesn't have any               │
│    repositories yet, or you may not have access            │
│    to view them.                                           │
│                                                             │
│                 [Check GitHub Settings]                     │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Repository Toggle Logic

```python
def toggle_repository_tracking(team, github_repo_id, repo_data):
    """Toggle tracking status for a repository.

    If TrackedRepository exists -> delete it (stop tracking)
    If TrackedRepository doesn't exist -> create it (start tracking)
    """
    try:
        tracked = TrackedRepository.objects.get(
            team=team,
            github_repo_id=github_repo_id
        )
        # Stop tracking
        tracked.delete()
        return {"action": "removed", "repo": repo_data["full_name"]}
    except TrackedRepository.DoesNotExist:
        # Start tracking
        integration = GitHubIntegration.objects.get(team=team)
        TrackedRepository.objects.create(
            team=team,
            integration=integration,
            github_repo_id=github_repo_id,
            full_name=repo_data["full_name"],
            is_active=True,
        )
        return {"action": "added", "repo": repo_data["full_name"]}
```

---

## Risk Assessment

### High Risk
1. **Large Organizations** (100+ repos)
   - Mitigation: Paginate API calls, client-side search/filter
   - Show loading indicator during fetch

### Medium Risk
1. **Private Repository Access**
   - OAuth scope includes `repo` which grants private repo access
   - Mitigation: Verify scope during OAuth, show appropriate error

2. **Stale Data**
   - Repos may be added/removed from org after initial fetch
   - Mitigation: Refresh button, periodic re-sync

### Low Risk
1. **Rate Limiting**
   - Authenticated: 5000 requests/hour
   - Mitigation: Cache repo list in session, reuse pagination helper

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Repo list load time | <3s | Time to display repos |
| Selection success rate | >99% | Successful saves / attempts |
| Page usability | >80% | User can find and select repos |

---

## Security Considerations

1. **Admin Only**: Repository selection requires team admin role
2. **Team Scoping**: Only show repos from team's connected org
3. **Validation**: Verify repo belongs to connected org before tracking
4. **Audit Trail**: Log repo selection changes (optional)

---

## Testing Strategy

### Unit Tests
- GitHub API repo fetching with mocked responses
- Pagination handling for large orgs
- TrackedRepository create/delete logic

### Integration Tests
- Full repo listing flow
- Toggle tracking flow
- Bulk selection flow
- HTMX partial updates

### Manual Testing Checklist
1. Navigate to repos page from integrations home
2. See list of org repos with tracked status
3. Toggle individual repo tracking
4. Use bulk select/deselect
5. Search and filter repos
6. Verify TrackedRepository records created

---

## File Structure

```
apps/integrations/
├── services/
│   └── github_oauth.py           # ⬆️ EXTEND - Add repo fetching
├── views.py                      # ⬆️ EXTEND - Add repo views
├── urls.py                       # ⬆️ EXTEND - Add repo URLs
└── templates/
    └── integrations/
        ├── github_repos.html           # ❌ CREATE
        └── components/
            └── repo_card.html          # ❌ CREATE
```

---

## Timeline Considerations

**Critical Path:**
1. GitHub API function must be first (blocks views)
2. List view blocks selection views
3. Templates can parallel view development

**Estimated Total Effort:** Small-Medium (1-2 days of focused work)

**Parallelization:** Template styling can happen while views are being tested
