# Phase 2.4: Repository Selection - Task Checklist

> Last Updated: 2025-12-10

## Overview

Total tasks: 24
Estimated effort: Small-Medium (Phase complexity: S-M)

---

## 2.4.1 GitHub API Repository Functions [Effort: S]

### New API Functions
- [ ] Add `get_organization_repositories(access_token, org_slug)` to github_oauth.py
- [ ] Reuse `_make_paginated_github_api_request()` for pagination
- [ ] Filter out archived repositories (optional flag)
- [ ] Return repo metadata (id, full_name, description, language, private, updated_at)

### Tests
- [ ] Test `get_organization_repositories` returns repo list
- [ ] Test pagination handling for large orgs (100+ repos)
- [ ] Test error handling for API failures
- [ ] Test filtering archived repos

---

## 2.4.2 Repository List View [Effort: M]

### View Implementation
- [ ] Create `github_repos` view
- [ ] Require login and team membership
- [ ] Require GitHub integration exists
- [ ] Fetch repos from GitHub API
- [ ] Mark repos as tracked (match with TrackedRepository records)
- [ ] Pass repos to template with tracking status

### URL Configuration
- [ ] Add `github/repos/` URL pattern

### Tests
- [ ] Test repos view requires login
- [ ] Test repos view requires team membership
- [ ] Test repos view requires GitHub integration
- [ ] Test repos view shows tracking status correctly

---

## 2.4.3 Repository Toggle View [Effort: S]

### View Implementation
- [ ] Create `github_repo_toggle` view (POST only)
- [ ] Require team admin role
- [ ] Toggle TrackedRepository (create if not exists, delete if exists)
- [ ] HTMX support for inline update
- [ ] Return updated repo card partial

### URL Configuration
- [ ] Add `github/repos/<int:repo_id>/toggle/` URL pattern

### Tests
- [ ] Test toggle view requires POST method
- [ ] Test toggle view requires admin role
- [ ] Test toggle creates TrackedRepository for new repo
- [ ] Test toggle deletes TrackedRepository for tracked repo
- [ ] Test toggle returns partial for HTMX

---

## 2.4.4 Repository Templates [Effort: M]

### Main Template
- [ ] Create `integrations/github_repos.html`
- [ ] Extend `web/app/app_base.html`
- [ ] Show page title and description
- [ ] Add back link to integrations home
- [ ] Show search/filter input
- [ ] Show tracked count (X of Y repos)

### Repository List
- [ ] Display repos in card/list layout
- [ ] Show repo name and description
- [ ] Show language badge
- [ ] Show private/public indicator (lock icon)
- [ ] Show last updated timestamp
- [ ] Show tracked/untracked status
- [ ] Add toggle button

### Components
- [ ] Create `integrations/components/repo_card.html` partial
- [ ] Support HTMX swap for toggle action

### Empty State
- [ ] Handle no repos case
- [ ] Show helpful message

---

## 2.4.5 Integration Dashboard Update [Effort: S]

### Home Page Updates
- [ ] Add "Repositories" link to GitHub card in home.html
- [ ] Show tracked repo count on GitHub card
- [ ] Add icon for repos link

---

## Optional Enhancements (Future)

### Bulk Selection
- [ ] (Optional) Add "Select All" / "Deselect All" buttons
- [ ] (Optional) Create `github_repos_bulk` view for bulk operations
- [ ] (Optional) Add checkbox UI for multi-select

### Search/Filter
- [ ] (Optional) Add client-side search filter (JavaScript)
- [ ] (Optional) Filter by language
- [ ] (Optional) Filter by tracked/untracked

---

## Post-Implementation

### Documentation
- [ ] Update repo-selection-tasks.md to mark complete
- [ ] Update repo-selection-context.md with implementation notes
- [ ] Update github-integration-tasks.md to mark 2.4 complete

### Cleanup
- [ ] Run ruff format and lint
- [ ] Ensure all tests pass
- [ ] Remove any debug logging

---

## Completion Criteria

Phase 2.4 is complete when:
1. [ ] Admin can view list of GitHub org repositories
2. [ ] Repos show tracked/untracked status
3. [ ] Admin can toggle tracking for individual repos
4. [ ] TrackedRepository records created/deleted correctly
5. [ ] Repos link visible on integrations home
6. [ ] All tests pass
7. [ ] Code reviewed and merged

---

## Quick Reference

### New URLs to implement:
```
/a/{team}/integrations/github/repos/                    → github_repos
/a/{team}/integrations/github/repos/{repo_id}/toggle/   → github_repo_toggle
```

### Key imports:
```python
from apps.integrations.models import GitHubIntegration, TrackedRepository
from apps.integrations.services.encryption import decrypt
from apps.integrations.services.github_oauth import GitHubOAuthError, get_organization_repositories
from apps.teams.decorators import login_and_team_required, team_admin_required
```

### TDD Reminder:
Follow Red-Green-Refactor cycle for each feature:
1. Write failing test
2. Implement minimum code to pass
3. Refactor while keeping tests green
