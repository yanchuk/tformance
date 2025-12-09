---
name: django-dev-guidelines
description: Django development patterns for tformance project. Use when creating views, models, serializers, APIs, Celery tasks, or working with Teams. Covers BaseModel/BaseTeamModel, function-based views, DRF patterns, team-scoped queries, and project-specific conventions.
---

# Django Development Guidelines

## Purpose

Establish consistency and best practices for Django development in the tformance project - an AI Impact Analytics Platform.

## When to Use This Skill

Automatically activates when working on:
- Creating or modifying models, views, serializers
- Building API endpoints with DRF
- Implementing team-scoped functionality
- Creating Celery background tasks
- Working with the Teams system
- Database queries and optimization

## Quick Start Checklist

### New Feature Checklist
- [ ] **Model**: Extend BaseModel or BaseTeamModel
- [ ] **View**: Function-based with proper decorators
- [ ] **URLs**: Add to team_urlpatterns or urlpatterns
- [ ] **Tests**: Write tests first (TDD)
- [ ] **Templates**: Use HTMX/Alpine patterns

### New Django App Checklist
- [ ] Create with `make uv run 'pegasus startapp <app_name>'`
- [ ] Add to INSTALLED_APPS
- [ ] Create `urls.py` with urlpatterns and team_urlpatterns
- [ ] Create `tests/` directory with `__init__.py`

## Architecture Overview

### Project Structure
```
tformance/              # Project settings
apps/                   # Django apps
├── api/                # API endpoints
├── teams/              # Team management
├── users/              # User management
├── subscriptions/      # Billing
├── utils/              # Shared utilities
└── web/                # Public pages
templates/              # Django templates
assets/                 # Frontend assets (Vite)
```

### Key Principle: Team-Scoped Data

Most data belongs to a Team. Use BaseTeamModel for team-owned data.

## Core Patterns

### 1. Models

```python
# Team-scoped model (most common)
from apps.teams.models import BaseTeamModel

class GitHubSync(BaseTeamModel):
    repository = models.CharField(max_length=255)
    last_synced = models.DateTimeField(null=True)

    class Meta:
        verbose_name = "GitHub Sync"

# Non-team model (rare)
from apps.utils.models import BaseModel

class GlobalSetting(BaseModel):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
```

### 2. Views

```python
from django.shortcuts import render
from apps.teams.decorators import login_and_team_required, team_admin_required

# Standard team view
@login_and_team_required
def dashboard(request, team_slug):
    team = request.team  # Automatically set by decorator
    data = MyModel.objects.for_team(team)
    return render(request, "myapp/dashboard.html", {"data": data})

# Admin-only view
@team_admin_required
def settings(request, team_slug):
    # Only team admins can access
    pass
```

### 3. URLs

```python
# apps/myapp/urls.py
from django.urls import path
from . import views

app_name = "myapp"

# Non-team URLs (rare)
urlpatterns = []

# Team-scoped URLs (common)
# These become: /a/<team_slug>/myapp/...
team_urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("settings/", views.settings, name="settings"),
]
```

### 4. Queries

```python
# Always use for_team for team-scoped queries
items = MyModel.objects.for_team(team)

# Optimize with select_related/prefetch_related
items = MyModel.objects.for_team(team).select_related("user")
```

## Anti-Patterns to Avoid

❌ Class-based views (unless using DRF)
❌ Direct `objects.filter(team=team)` instead of `for_team`
❌ Business logic in views (extract to services)
❌ Missing team context in team-scoped views
❌ N+1 queries (use select_related/prefetch_related)
❌ Files over 200-300 lines

## Resource Files

For detailed information on specific topics:

### [resources/models-guide.md](resources/models-guide.md)
Complete guide to Django models:
- BaseModel vs BaseTeamModel
- Field patterns and constraints
- Model methods and properties
- Manager patterns

### [resources/views-guide.md](resources/views-guide.md)
View implementation patterns:
- Function-based view structure
- Decorators and permissions
- Request handling
- Response patterns

### [resources/drf-guide.md](resources/drf-guide.md)
Django REST Framework patterns:
- ViewSets and Serializers
- Authentication and permissions
- API versioning
- Error handling

### [resources/celery-guide.md](resources/celery-guide.md)
Background task patterns:
- Task structure
- Scheduling
- Error handling
- Monitoring

### [resources/teams-guide.md](resources/teams-guide.md)
Team system deep dive:
- Team context
- for_team manager
- Team membership
- Permissions

## Quick Reference

### Imports
```python
# Models
from apps.utils.models import BaseModel
from apps.teams.models import BaseTeamModel, Team
from apps.users.models import CustomUser

# Views
from apps.teams.decorators import login_and_team_required, team_admin_required

# DRF
from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
```

### URL Pattern Format
- Team URLs: `/a/<team_slug>/<app>/<path>/`
- API URLs: `/api/<version>/<resource>/`

### Test Commands
```bash
make test                              # All tests
make test ARGS='apps.myapp.tests'      # App tests
make test ARGS='apps.myapp.tests.test_views::TestMyView'  # Specific
```

---

**Skill Status**: COMPLETE
**Line Count**: < 500
**Progressive Disclosure**: Resource files for detailed information
