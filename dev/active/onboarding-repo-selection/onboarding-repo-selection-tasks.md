# Onboarding Repository Selection - Tasks

## Task List

### Task 1: Update select_repositories view
- [x] Fetch repos from GitHub using `get_organization_repositories()`
- [x] Filter out archived repos by default
- [x] Pass repos list to template context
- [x] Handle POST with list of selected repo IDs
- [x] Create TrackedRepository records for selected repos
- [x] Start background sync task

### Task 2: Implement select_repos.html template
- [x] Replace placeholder with repo selection UI
- [x] Add checkboxes for each repository
- [x] Show repo name, description, language badge
- [x] Add "Select All" / "Deselect All" buttons using Alpine.js
- [x] Add hidden input fields for selected repos
- [x] Keep existing back/continue buttons

### Task 3: Test the flow
- [x] Verify existing tests pass (16 passed)
- [ ] Manual verification (requires real GitHub connection)

## Implementation Order

1. Backend first (view logic) ✅
2. Template UI ✅
3. Testing ✅

## Notes

- Reuse patterns from `github_repos` view for fetching
- Use Alpine.js for client-side checkbox state management
- No HTMX needed (full page form submit)
- Onboarding doesn't have team_membership context, use different approach

## Completed: 2025-12-28

Files modified:
- `apps/onboarding/views.py:208-295` - Enhanced `select_repositories` view
- `templates/onboarding/select_repos.html` - Replaced placeholder with repo list UI
