# Onboarding Repository Selection - Implementation Plan

## Overview

Implement repository selection for Onboarding Step 2, allowing users to select which repositories to track during initial setup. Users can select individual repos or use "Select All" functionality.

## Current State

- `select_repositories` view exists in `apps/onboarding/views.py` (lines 208-252)
- Template `templates/onboarding/select_repos.html` shows placeholder "Coming soon" message
- `get_organization_repositories()` service already exists in `apps/integrations/services/github_oauth.py`
- Existing repo selection UI pattern in `apps/integrations/templates/integrations/github_repos.html`
- `TrackedRepository` model stores tracked repos

## Implementation Approach

### Phase 1: Backend View Enhancement

1. Update `select_repositories` view to:
   - Fetch repos from GitHub API using `get_organization_repositories()`
   - Pass repos list to template context
   - Handle POST to create `TrackedRepository` records for selected repos

### Phase 2: Template Implementation

2. Update `select_repos.html` template to:
   - Display checkbox list of repositories
   - Add "Select All" / "Deselect All" buttons
   - Show repo metadata (name, description, language, private badge)
   - Filter archived repos by default

### Phase 3: Bulk Selection Endpoint

3. Create new endpoint for batch repo selection:
   - Accept list of selected repo IDs
   - Create `TrackedRepository` records in bulk
   - Start background sync task

## Files to Modify

| File | Change |
|------|--------|
| `apps/onboarding/views.py` | Enhance `select_repositories` view |
| `templates/onboarding/select_repos.html` | Replace placeholder with repo list UI |
| `apps/onboarding/urls.py` | Add toggle endpoint if needed |

## Technical Details

### Repository Data Structure
```python
{
    "id": 12345,
    "full_name": "org/repo-name",
    "name": "repo-name",
    "description": "Description...",
    "language": "Python",
    "private": False,
    "updated_at": "2025-01-01T00:00:00Z",
    "archived": False,
}
```

### TrackedRepository Creation
```python
TrackedRepository.objects.create(
    team=team,
    integration=integration,
    github_repo_id=repo["id"],
    full_name=repo["full_name"],
    is_active=True,
)
```

## Success Criteria

- [ ] User sees list of organization repos with checkboxes
- [ ] "Select All" button works
- [ ] User can select individual repos
- [ ] POST creates TrackedRepository records for selected repos
- [ ] Background sync starts after selection
- [ ] Archived repos excluded by default
