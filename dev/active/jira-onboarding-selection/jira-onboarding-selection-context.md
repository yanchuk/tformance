# Context: Jira Project Selection in Onboarding

**Last Updated: 2025-12-28**

## Key Files to Modify

| File | Changes |
|------|---------|
| `apps/onboarding/views.py` | Enable `connect_jira`, add `select_jira_projects` view |
| `apps/onboarding/urls.py` | Add URL for `select_jira_projects` |
| `templates/onboarding/connect_jira.html` | Enable button, remove "Coming Soon" |
| `apps/auth/oauth_state.py` | Add `FLOW_TYPE_JIRA_ONBOARDING` constant |
| `apps/auth/views.py` | Add `jira_callback` for unified auth handling |

## Key Files to Create

| File | Purpose |
|------|---------|
| `templates/onboarding/select_jira_projects.html` | Project selection UI |
| `apps/onboarding/tests/test_jira_onboarding.py` | Test coverage |

## Key Files to Reference (Patterns)

| File | Pattern |
|------|---------|
| `apps/onboarding/views.py:select_organization` | How org selection works |
| `apps/integrations/views/jira.py:jira_projects_list` | How to fetch projects |
| `apps/integrations/views/jira.py:jira_project_toggle` | How to track/untrack |
| `apps/integrations/services/jira_client.py` | Jira API client |
| `templates/onboarding/select_repos.html` | Template pattern |
| `apps/auth/views.py:github_callback` | Unified callback pattern |

## Existing Models

### JiraIntegration (`apps/integrations/models.py:283`)
```python
class JiraIntegration(BaseTeamModel):
    cloud_id = models.CharField(max_length=255)
    site_name = models.CharField(max_length=255)
    site_url = models.URLField()
    sync_status = models.CharField(choices=SYNC_STATUS_CHOICES)
    last_synced_at = models.DateTimeField(null=True)
```

### TrackedJiraProject (`apps/integrations/models.py:346`)
```python
class TrackedJiraProject(BaseTeamModel):
    jira_integration = models.ForeignKey(JiraIntegration)
    jira_project_id = models.CharField(max_length=255)
    jira_project_key = models.CharField(max_length=50)
    name = models.CharField(max_length=255)
    project_type = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
```

## Existing Services

### jira_client.py - Key Functions
```python
def get_jira_client(credential: IntegrationCredential) -> JIRA:
    """Create authenticated JIRA client."""

def get_accessible_projects(credential: IntegrationCredential) -> list[dict]:
    """Fetch all accessible projects. Returns list of dicts with:
    - id, key, name, projectTypeKey, style (optional)
    """
```

### jira_oauth.py - Key Functions
```python
def get_authorization_url(team_id: int, redirect_uri: str) -> str:
    """Build Atlassian OAuth authorization URL."""

def exchange_code_for_token(code: str, redirect_uri: str) -> dict:
    """Exchange auth code for access/refresh tokens."""

def get_accessible_resources(access_token: str) -> list[dict]:
    """Fetch Jira cloud sites accessible to user."""

def ensure_valid_jira_token(credential: IntegrationCredential) -> str:
    """Auto-refresh expired tokens. Returns valid access token."""
```

## OAuth Flow Sequence

### Current (Integrations)
```
1. User clicks "Connect Jira" in integrations settings
2. jira_connect() creates state with team_id, redirects to Atlassian
3. Atlassian redirects to jira_callback with code
4. jira_callback() exchanges code, creates JiraIntegration
5. Redirects to integrations home
```

### Target (Onboarding)
```
1. User clicks "Connect Jira" in onboarding step 5
2. onboarding.connect_jira() creates state with FLOW_TYPE_JIRA_ONBOARDING
3. Atlassian redirects to unified jira_callback
4. auth.jira_callback() exchanges code, creates JiraIntegration
5. Detects onboarding flow → redirects to select_jira_projects
6. select_jira_projects GET → fetches and displays projects
7. select_jira_projects POST → creates TrackedJiraProject records
8. Redirects to connect_slack (step 6)
```

## Session Data Structure

After Jira OAuth, store in session:
```python
request.session["jira_onboarding"] = {
    "credential_id": credential.id,
    "jira_integration_id": integration.id,
    "site_name": "acme.atlassian.net",
}
```

## URL Routes

### Current (`apps/integrations/urls.py`)
```python
path("jira/connect/", views.jira_connect, name="jira_connect"),
path("jira/callback/", views.jira_callback, name="jira_callback"),
path("jira/projects/", views.jira_projects_list, name="jira_projects_list"),
path("jira/projects/toggle/", views.jira_project_toggle, name="jira_project_toggle"),
```

### New (`apps/onboarding/urls.py`)
```python
path("jira/projects/", views.select_jira_projects, name="select_jira_projects"),
```

### New (`apps/auth/urls.py`)
```python
path("jira/callback/", views.jira_callback, name="jira_callback"),
```

## Template Pattern

Follow `select_repos.html` structure:
```html
{% extends "onboarding/base.html" %}

{% block content %}
<div class="card app-card">
  <div class="card-body">
    <h2>Select Jira Projects</h2>
    <p>Which projects should tformance track?</p>

    <form method="post" x-data="{ selectAll: false }">
      {% csrf_token %}

      <!-- Select All checkbox -->
      <label class="flex items-center gap-2 mb-4">
        <input type="checkbox" x-model="selectAll" @click="...">
        <span>Select All</span>
      </label>

      <!-- Project list -->
      {% for project in projects %}
      <label class="flex items-center gap-3 p-3 rounded-lg hover:bg-base-200">
        <input type="checkbox" name="projects" value="{{ project.id }}"
               :checked="selectAll">
        <div>
          <div class="font-medium">{{ project.key }} - {{ project.name }}</div>
          <div class="text-sm opacity-70">{{ project.projectTypeKey }}</div>
        </div>
      </label>
      {% endfor %}

      <div class="flex justify-between mt-6">
        <a href="{% url 'onboarding:connect_jira' %}" class="btn">← Back</a>
        <button type="submit" class="btn btn-primary">Continue →</button>
      </div>
    </form>
  </div>
</div>
{% endblock %}
```

## Dependencies

- `jira` Python package (already installed)
- Jira OAuth credentials in settings (JIRA_CLIENT_ID, JIRA_CLIENT_SECRET)
- Alpine.js for "Select All" (already in project)

## Related PRD Sections

From `prd/ONBOARDING.md`:
> Step 4: Connect Jira (Optional)
> - Show benefits: story points, sprint velocity, cycle time
> - OAuth button
> - Skip option
>
> After OAuth: Select Jira Projects
> - Checkbox list of projects
> - Behind the scenes: Match Jira users to GitHub users by email
