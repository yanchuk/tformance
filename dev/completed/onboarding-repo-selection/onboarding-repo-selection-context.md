# Onboarding Repository Selection - Context

## Key Files

### Views
- `apps/onboarding/views.py:208-252` - `select_repositories` view (needs enhancement)
- `apps/integrations/views/github.py:284-339` - `github_repos` view (reference pattern)

### Templates
- `templates/onboarding/select_repos.html` - Current placeholder template
- `templates/onboarding/base.html` - Onboarding layout with step indicator
- `apps/integrations/templates/integrations/github_repos.html` - Reference repo list
- `apps/integrations/templates/integrations/components/repo_card.html` - Reference repo row

### Services
- `apps/integrations/services/github_oauth.py:get_organization_repositories()` - Fetches repos from GitHub

### Models
- `apps/integrations/models.py:TrackedRepository` - Stores tracked repositories
- `apps/integrations/models.py:GitHubIntegration` - GitHub connection with org info

### URLs
- `apps/onboarding/urls.py` - Onboarding routes

## Existing Patterns

### Repo Fetching (from github_repos view)
```python
from apps.integrations.services import github_oauth

repos = github_oauth.get_organization_repositories(
    integration.credential.access_token,
    integration.organization_slug
)
```

### TrackedRepository Creation (from github_repo_toggle view)
```python
TrackedRepository.objects.create(
    team=team,
    integration=integration,
    github_repo_id=repo_id,
    full_name=full_name,
    is_active=True,
)
```

### Background Sync (from select_repositories view)
```python
from apps.integrations.tasks import sync_historical_data_task

repo_ids = list(TrackedRepository.objects.filter(team=team).values_list("id", flat=True))
task = sync_historical_data_task.delay(team.id, repo_ids)
request.session["sync_task_id"] = task.id
```

## UI Patterns

### Onboarding Template Structure
- Extends `onboarding/base.html`
- Uses `{% block onboarding_content %}`
- Max width: `max-w-md mx-auto` for content
- Step indicator passed via `step` context variable

### Design System Classes
- Cards: `app-card`
- Buttons: `app-btn-primary`, `app-btn-ghost`
- Alerts: `app-alert`, `app-alert-info`
- Badges: `app-badge`, `app-badge-success`

### Checkbox Selection Pattern (Alpine.js)
```html
<div x-data="{ selectedRepos: [], selectAll: false }">
  <button @click="selectAll = !selectAll; selectedRepos = selectAll ? allRepoIds : []">
    Select All
  </button>
  <input type="checkbox" :checked="selectedRepos.includes(repoId)" @change="...">
</div>
```

## Dependencies

- `apps.integrations.models.GitHubIntegration` - Must exist for team
- `apps.integrations.services.github_oauth` - For API calls
- `apps.integrations.tasks.sync_historical_data_task` - For background sync
