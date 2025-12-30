# Code Structure Cleanup - Context

**Last Updated:** 2024-12-30

## Key Files

### Files to Modify

| File | Purpose | Current Lines |
|------|---------|---------------|
| `apps/metrics/services/dashboard_service.py` | Dashboard data aggregation | 2,307 |
| `apps/integrations/tasks.py` | Celery task definitions | 2,197 |
| `apps/auth/views.py` | Auth views with TODO | 838 |
| `apps/metrics/services/survey_service.py` | Survey logic with TODO | 6,447 |

### Files to Create

| File | Purpose |
|------|---------|
| `apps/metrics/constants.py` | PR size constants |
| `apps/metrics/services/dashboard/__init__.py` | Module exports |
| `apps/metrics/services/dashboard/_helpers.py` | Private helpers |
| `apps/metrics/services/dashboard/key_metrics.py` | Key metrics functions |
| `apps/metrics/services/dashboard/ai_metrics.py` | AI-related metrics |
| `apps/metrics/services/dashboard/team_metrics.py` | Team breakdown |
| `apps/metrics/services/dashboard/review_metrics.py` | Review stats |
| `apps/metrics/services/dashboard/pr_metrics.py` | PR metrics |
| `apps/metrics/services/dashboard/deployment_metrics.py` | Deployment metrics |
| `apps/integrations/tasks/__init__.py` | Task exports |
| `apps/integrations/tasks/github_sync.py` | GitHub sync tasks |
| `apps/integrations/tasks/jira_sync.py` | Jira sync tasks |
| `apps/integrations/tasks/slack.py` | Slack tasks |
| `apps/integrations/tasks/copilot.py` | Copilot tasks |
| `apps/integrations/tasks/metrics.py` | Aggregation tasks |
| `apps/integrations/tasks/pr_data.py` | PR data tasks |

### Reference Files

| File | Relevance |
|------|-----------|
| `apps/metrics/models/team.py` | TeamMember.avatar_url, .initials properties |
| `apps/integrations/constants.py` | Existing constants pattern |
| `apps/metrics/services/pr_list_service.py` | May also use PR size constants |

## Current Duplication Details

### Avatar/Initials Helper Functions

**In `dashboard_service.py` (lines 99-130):**
```python
def _compute_initials(name: str) -> str:
    """Compute 2-letter initials from a display name."""
    if not name:
        return "??"
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[1][0]}".upper()
    return name[:2].upper()

def _avatar_url_from_github_id(github_id: str | None) -> str:
    """Construct GitHub avatar URL from user ID."""
    if not github_id:
        return ""
    if github_id.isdigit():
        return f"https://avatars.githubusercontent.com/u/{github_id}?s=80"
    return f"https://avatars.githubusercontent.com/{github_id}?s=80"
```

**In `TeamMember` model (lines 103-122):**
```python
@property
def avatar_url(self) -> str:
    if self.github_id:
        return f"https://avatars.githubusercontent.com/u/{self.github_id}?s=80"
    return ""

@property
def initials(self) -> str:
    if self.display_name:
        parts = self.display_name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[1][0]}".upper()
        return self.display_name[:2].upper()
    return "??"
```

**Usage in dashboard_service.py:**
- Line 409-410: `get_team_breakdown()` - aggregated values from annotation
- Line 465-466: `get_ai_detective_leaderboard()` - annotation values
- Line 502-503: `get_review_distribution()` - annotation values
- Line 999-1000: `get_copilot_by_member()` - annotation values

**Note:** The service functions use `.values()` aggregations with annotations like `reviewer__github_id` and `reviewer__display_name`. They don't have access to model instances, so they need helper functions to compute avatar URLs and initials from raw values. The helpers should stay but be consolidated (not duplicated from model logic).

### PR Size Constants

**Current location (dashboard_service.py lines 30-35):**
```python
PR_SIZE_XS_MAX = 10
PR_SIZE_S_MAX = 50
PR_SIZE_M_MAX = 200
PR_SIZE_L_MAX = 500
```

**Should move to:** `apps/metrics/constants.py`

### TODO Comments

1. **`apps/auth/views.py:526`**
   ```python
   # For now, use the first site (most users have one)
   # TODO: Add site selection if multiple sites
   site = sites[0]
   ```
   - Context: Jira OAuth callback when user has multiple Jira sites
   - Assessment: Edge case, can be deferred with ticket

2. **`apps/metrics/services/survey_service.py:156`**
   ```python
   # TODO: Actually send the reveal message via Slack
   # For now, just return False since we don't implement Slack sending
   return False
   ```
   - Context: Feature for sending reveal messages via Slack
   - Assessment: Feature not implemented, needs ticket or removal

## Dependencies

### Import Dependencies for Dashboard Split

The split modules will need to import from:
- `django.db.models` - QuerySet, annotations
- `django.core.cache` - cache
- `apps.metrics.models` - PullRequest, PRReview, etc.
- `apps.teams.models` - Team
- `apps.metrics.constants` - PR_SIZE_* (after moving)

### Celery Dependencies for Tasks Split

All task modules need:
- `celery` - shared_task
- `logging` - logger
- Model imports from `apps.integrations.models`, `apps.metrics.models`
- Service imports from various services

## Decisions Made

1. **Keep helper functions for annotation-based queries** - Can't use model properties when using `.values()` aggregations
2. **Use `__init__.py` re-exports** - Maintains backward compatibility
3. **Split by domain, not by size** - More maintainable than arbitrary line splits
4. **Create constants.py in metrics app** - Follows existing pattern in integrations app

## Out of Scope

- Template tag split (`pr_list_tags.py` at 858 lines) - Can be done later
- Model split (`github.py` at 1,342 lines) - Complex due to `categorize_file()`
- View file splits - Already at acceptable sizes
