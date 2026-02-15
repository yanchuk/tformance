# Teams System Guide

## Table of Contents
1. [Overview](#overview)
2. [Team Context](#team-context)
3. [BaseTeamModel](#baseteammodel)
4. [for_team Manager](#for_team-manager)
5. [Team Membership](#team-membership)
6. [Permissions](#permissions)

## Overview

The Teams system provides multi-tenancy for tformance. Each Team is like a virtual tenant - most data belongs to a team and is isolated from other teams.

**Key Concepts:**
- Team = virtual tenant (company/organization)
- Most models extend `BaseTeamModel`
- Use `for_team` manager for queries
- Views use team decorators

## Team Context

### How Team Context is Set

Team context is set automatically via middleware and decorators:

```python
# In views - decorator sets request.team
@login_and_team_required
def my_view(request, team_slug):
    team = request.team  # Team object is available

# In templates
{{ request.team.name }}
```

### Getting Team in Different Contexts

```python
# In views
@login_and_team_required
def my_view(request, team_slug):
    team = request.team

# In Celery tasks
from apps.teams.models import Team
team = Team.objects.get(id=team_id)

# In services/utilities
from apps.teams.context import get_current_team
team = get_current_team()  # May be None
```

## BaseTeamModel

### When to Use

Use `BaseTeamModel` for any model that belongs to a team:

```python
from apps.teams.models import BaseTeamModel

class Project(BaseTeamModel):
    name = models.CharField(max_length=255)
    # team field is inherited automatically

class GitHubIntegration(BaseTeamModel):
    access_token = models.CharField(max_length=255)
    # team field is inherited automatically
```

### When NOT to Use

Use `BaseModel` for truly global data:

```python
from apps.utils.models import BaseModel

class GlobalSetting(BaseModel):
    """Settings that apply to the entire application."""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
```

### What BaseTeamModel Provides

```python
class BaseTeamModel(BaseModel):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)

    objects = TeamScopedManager()  # Provides for_team()

    class Meta:
        abstract = True
```

## for_team Manager

### Basic Usage

Always use `for_team()` for team-scoped queries:

```python
# Correct
projects = Project.objects.for_team(team)

# Also correct - chaining
projects = Project.objects.for_team(team).filter(is_active=True)

# Wrong - bypasses team scoping
projects = Project.objects.filter(team=team)
```

### Why for_team?

1. **Consistency** - One pattern for all team queries
2. **Safety** - Can add additional filtering in the future
3. **Clarity** - Makes team-scoping explicit

### Complex Queries

```python
# With select_related
projects = Project.objects.for_team(team).select_related("created_by")

# With prefetch_related
projects = Project.objects.for_team(team).prefetch_related("tasks")

# With annotations
from django.db.models import Count

projects = Project.objects.for_team(team).annotate(
    task_count=Count("tasks")
)

# Filtering
active_projects = Project.objects.for_team(team).filter(
    is_active=True,
    created_at__gte=last_month
)
```

### In Views

```python
@login_and_team_required
def project_list(request, team_slug):
    # request.team is set by decorator
    projects = Project.objects.for_team(request.team)
    return render(request, "projects/list.html", {"projects": projects})
```

### In Celery Tasks

```python
@shared_task
def process_team_data(team_id):
    from apps.teams.models import Team
    from .models import Project

    team = Team.objects.get(id=team_id)
    projects = Project.objects.for_team(team)
    # Process projects...
```

## Team Membership

### Adding Users to Teams

```python
from apps.teams.models import Team, Membership

# Add member
Membership.objects.create(
    team=team,
    user=user,
    role="member"  # or "admin"
)

# Or using helper
team.members.add(user, through_defaults={"role": "member"})
```

### Checking Membership

```python
# Check if user is member
if team.is_member(user):
    # User can access team

# Check if user is admin
if team.is_admin(user):
    # User can manage team

# Get user's teams
user_teams = Team.objects.filter(members=user)
```

### Membership Roles

```python
class Membership(models.Model):
    ROLE_CHOICES = [
        ("member", "Member"),
        ("admin", "Admin"),
    ]

    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
```

## Permissions

### View Decorators

```python
from apps.teams.decorators import login_and_team_required, team_admin_required

# Any team member can access
@login_and_team_required
def member_view(request, team_slug):
    pass

# Only team admins can access
@team_admin_required
def admin_view(request, team_slug):
    pass
```

### Checking Permissions in Views

```python
@login_and_team_required
def some_view(request, team_slug):
    # Check if admin
    if request.team.is_admin(request.user):
        # Show admin options
        pass

    # Check specific permission
    if not request.user.can_edit_project(project):
        raise PermissionDenied()
```

### Object-Level Permissions

```python
class Project(BaseTeamModel):
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    def can_edit(self, user):
        """Check if user can edit this project."""
        # Creator can always edit
        if self.created_by == user:
            return True
        # Team admins can edit
        if self.team.is_admin(user):
            return True
        return False

    def can_delete(self, user):
        """Only team admins can delete."""
        return self.team.is_admin(user)
```

### In Templates

```html
{% if request.team.is_admin(request.user) %}
  <a href="{% url 'team:settings' team_slug=request.team.slug %}">
    Team Settings
  </a>
{% endif %}

{% if project.can_edit(request.user) %}
  <button>Edit Project</button>
{% endif %}
```
