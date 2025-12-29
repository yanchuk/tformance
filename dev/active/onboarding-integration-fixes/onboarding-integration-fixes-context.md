# Onboarding & Integration Fixes - Context

**Last Updated:** 2025-12-29

## Key Files

### Issue 1: Onboarding Flow

| File | Lines | Purpose |
|------|-------|---------|
| `apps/onboarding/views.py` | 94-97 | `select_organization` - team existence check |
| `apps/onboarding/views.py` | 174-218 | `_create_team_from_org` - creates team, redirects to repos |
| `apps/onboarding/views.py` | 221-300 | `select_repositories` - repo selection view |
| `apps/onboarding/views.py` | 429-451 | `onboarding_complete` - final step |
| `apps/web/views.py` | 47-59 | `home` - auto-redirect to dashboard |
| `apps/teams/models.py` | - | Team model (needs `onboarding_complete` field) |
| `apps/teams/middleware.py` | - | TeamsMiddleware sets `request.default_team` |
| `templates/onboarding/select_org.html` | - | Org selection template |
| `templates/onboarding/select_repos.html` | - | Repo selection template |

### Issue 2: Repo Page Styling

| File | Lines | Elements |
|------|-------|----------|
| `apps/integrations/templates/integrations/components/repo_card.html` | 4 | Repo name: `text-slate-200` |
| `apps/integrations/templates/integrations/components/repo_card.html` | 7 | Repo description: `text-slate-400` |
| `apps/integrations/templates/integrations/components/member_row.html` | 9 | Avatar initials: `text-slate-300` |
| `apps/integrations/templates/integrations/components/member_row.html` | 12 | Member name: `text-slate-200` |
| `apps/integrations/templates/integrations/components/member_row.html` | 16, 20 | Username/email: `text-slate-400` |
| `apps/integrations/templates/integrations/github_repos.html` | 10 | Back link: `text-slate-500` |
| `apps/integrations/templates/integrations/github_repos.html` | 42 | Footer counter: `text-slate-500` |
| `apps/integrations/templates/integrations/github_members.html` | 10 | Back link: `text-slate-500` |
| `apps/integrations/templates/integrations/github_members.html` | 54 | Footer counter: `text-slate-500` |

**Design System Reference:**
| File | Purpose |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | Semantic `app-*` classes |
| `assets/styles/site-tailwind.css` | DaisyUI theme colors |
| `CLAUDE.md` | Color usage guidelines |

### Issue 3: Sync Progress

| File | Lines | Purpose |
|------|-------|---------|
| `apps/integrations/views/github.py` | 461-491 | `github_repo_sync` - manual sync (SYNCHRONOUS!) |
| `apps/integrations/views/github.py` | 494-511 | `github_repo_sync_progress` - progress polling |
| `apps/integrations/templates/integrations/components/repo_card.html` | 10-15 | HTMX polling setup |
| `apps/integrations/templates/integrations/components/repo_card.html` | 70-82 | Sync button |
| `apps/integrations/templates/integrations/partials/sync_progress.html` | - | Progress display partial |
| `apps/integrations/models.py` | 240-262 | TrackedRepository progress fields |
| `apps/integrations/tasks.py` | 277-346 | `sync_repository_initial_task` - async task |
| `apps/integrations/services/onboarding_sync.py` | 28-139 | OnboardingSyncService (has progress callback) |

---

## Model Changes Required

### Team Model Addition
```python
# apps/teams/models.py
class Team(BaseModel):
    # ... existing fields ...

    # New field for tracking onboarding completion
    onboarding_complete = models.BooleanField(
        default=True,  # Default True for existing teams
        help_text="Whether the team has completed the onboarding flow"
    )
```

### Migration Strategy
```python
# Migration for onboarding_complete
operations = [
    migrations.AddField(
        model_name='team',
        name='onboarding_complete',
        field=models.BooleanField(default=True),  # Existing teams are "complete"
    ),
]
```

---

## CSS Class Mappings

| Current (Wrong) | Semantic (Correct) | DaisyUI Value |
|-----------------|-------------------|---------------|
| `text-slate-200` | `text-base-content` | `#ccc9c0` (Easy Eyes warm) |
| `text-slate-300` | `text-base-content/80` | 80% opacity |
| `text-slate-400` | `text-base-content/80` | 80% opacity |
| `text-slate-500` | `text-base-content/70` | 70% opacity |
| `text-slate-600` | `text-base-content/70` | 70% opacity |

---

## URL Reference

| URL | View | Purpose |
|-----|------|---------|
| `/onboarding/` | `onboarding_start` | Start onboarding |
| `/onboarding/org/` | `select_organization` | Choose GitHub org |
| `/onboarding/repos/` | `select_repositories` | Choose repos to track |
| `/onboarding/sync/` | `sync_progress` | Show sync progress |
| `/onboarding/complete/` | `onboarding_complete` | Success page |
| `/` | `web:home` | Landing or redirect |
| `/app/` | `web_team:home` | Team dashboard |
| `/app/integrations/github/repos/` | `github_repos_list` | Repo management |

---

## Key Decisions

### Decision 1: Onboarding State
- **Chosen**: Model-based flag (`onboarding_complete`)
- **Reason**: Persists across sessions, survives browser refresh
- **Alternative rejected**: Session-based (lost on logout)

### Decision 2: Default Value for Migration
- **Chosen**: `default=True` for existing teams
- **Reason**: Existing teams shouldn't be forced through onboarding again
- **New teams**: Set to `False` during creation, `True` on completion

### Decision 3: Manual Sync Pattern
- **Chosen**: Celery task for async sync
- **Reason**: Consistent with initial sync pattern, enables progress
- **Alternative rejected**: Keep synchronous (blocks UI, no feedback)

---

## Dependencies

### Python Packages
- All existing packages sufficient
- Celery already configured

### JavaScript/Frontend
- HTMX already configured
- No additional JS needed

### External Services
- GitHub API (existing)
- Celery/Redis for async tasks (existing)

---

## Test Coverage Requirements

### New Tests Needed

```python
# apps/onboarding/tests/test_onboarding_flow.py
class TestOnboardingFlow(TestCase):
    def test_user_with_team_but_incomplete_onboarding_can_access_repos(self):
        """User with incomplete onboarding should access select_repos."""

    def test_onboarding_complete_sets_flag(self):
        """Visiting complete page sets onboarding_complete=True."""

    def test_home_redirects_incomplete_onboarding_to_repos(self):
        """Users with incomplete onboarding redirect to onboarding, not dashboard."""

# apps/integrations/tests/test_github_sync.py
class TestManualSync(TestCase):
    def test_manual_sync_queues_celery_task(self):
        """Clicking sync button queues async task."""

    def test_sync_status_set_to_syncing(self):
        """Status updates to 'syncing' immediately."""
```

### Existing Tests to Verify
- `apps/onboarding/tests/` - Onboarding flow tests
- `apps/integrations/tests/` - Integration tests
- E2E tests for onboarding flow

---

## Environment Variables

No new environment variables required.

---

## Deployment Notes

1. **Migration order**: Run migration BEFORE deploying code
2. **Celery restart**: Required if task signatures change
3. **Cache clear**: May need to clear template cache
4. **Testing**: Test on dev2.ianchuk.com before production
