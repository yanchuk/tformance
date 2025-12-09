# Django Views Guide

## Table of Contents
1. [Function-Based Views](#function-based-views)
2. [Decorators](#decorators)
3. [Request Handling](#request-handling)
4. [Response Patterns](#response-patterns)
5. [HTMX Integration](#htmx-integration)
6. [Error Handling](#error-handling)

## Function-Based Views

Per CLAUDE.md, use function-based views by default.

### Basic Pattern

```python
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from apps.teams.decorators import login_and_team_required

@login_and_team_required
def project_list(request, team_slug):
    """List all projects for the team."""
    projects = Project.objects.for_team(request.team).select_related("created_by")
    return render(request, "projects/list.html", {
        "projects": projects,
    })

@login_and_team_required
def project_detail(request, team_slug, project_id):
    """Show project details."""
    project = get_object_or_404(
        Project.objects.for_team(request.team),
        id=project_id
    )
    return render(request, "projects/detail.html", {
        "project": project,
    })
```

### Create/Update Pattern

```python
@login_and_team_required
def project_create(request, team_slug):
    """Create a new project."""
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.team = request.team
            project.created_by = request.user
            project.save()
            messages.success(request, "Project created successfully.")
            return redirect("projects:detail", team_slug=team_slug, project_id=project.id)
    else:
        form = ProjectForm()

    return render(request, "projects/create.html", {"form": form})

@login_and_team_required
def project_update(request, team_slug, project_id):
    """Update an existing project."""
    project = get_object_or_404(
        Project.objects.for_team(request.team),
        id=project_id
    )

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, "Project updated.")
            return redirect("projects:detail", team_slug=team_slug, project_id=project.id)
    else:
        form = ProjectForm(instance=project)

    return render(request, "projects/update.html", {
        "form": form,
        "project": project,
    })
```

### Delete Pattern

```python
@login_and_team_required
def project_delete(request, team_slug, project_id):
    """Delete a project."""
    project = get_object_or_404(
        Project.objects.for_team(request.team),
        id=project_id
    )

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("projects:list", team_slug=team_slug)

    return render(request, "projects/delete_confirm.html", {
        "project": project,
    })
```

## Decorators

### Authentication Decorators

```python
from apps.teams.decorators import login_and_team_required, team_admin_required

# Requires login + team membership
@login_and_team_required
def member_view(request, team_slug):
    pass

# Requires login + team admin role
@team_admin_required
def admin_view(request, team_slug):
    pass
```

### What Decorators Provide

```python
@login_and_team_required
def my_view(request, team_slug):
    # Available after decorator:
    request.team        # The Team object
    request.user        # The authenticated user
    team_slug           # The team's slug from URL
```

### Combining Decorators

```python
from django.views.decorators.http import require_http_methods

@login_and_team_required
@require_http_methods(["GET", "POST"])
def my_view(request, team_slug):
    pass
```

## Request Handling

### GET Parameters

```python
@login_and_team_required
def project_list(request, team_slug):
    # Query parameters
    search = request.GET.get("search", "")
    status = request.GET.get("status", "all")
    page = request.GET.get("page", 1)

    projects = Project.objects.for_team(request.team)

    if search:
        projects = projects.filter(name__icontains=search)

    if status != "all":
        projects = projects.filter(status=status)

    return render(request, "projects/list.html", {
        "projects": projects,
        "search": search,
        "status": status,
    })
```

### POST Data

```python
@login_and_team_required
def project_create(request, team_slug):
    if request.method == "POST":
        # Form data
        name = request.POST.get("name")
        description = request.POST.get("description", "")

        # Validation
        if not name:
            messages.error(request, "Name is required.")
            return redirect("projects:create", team_slug=team_slug)

        # Create
        project = Project.objects.create(
            team=request.team,
            name=name,
            description=description,
            created_by=request.user,
        )
        return redirect("projects:detail", team_slug=team_slug, project_id=project.id)

    return render(request, "projects/create.html")
```

### JSON Data (API-like)

```python
import json
from django.http import JsonResponse

@login_and_team_required
def api_project_update(request, team_slug, project_id):
    if request.method == "POST":
        data = json.loads(request.body)
        project = get_object_or_404(
            Project.objects.for_team(request.team),
            id=project_id
        )
        project.name = data.get("name", project.name)
        project.save()
        return JsonResponse({"status": "ok", "id": str(project.id)})
```

## Response Patterns

### Template Response

```python
return render(request, "template.html", context)
```

### Redirect

```python
from django.shortcuts import redirect

# Named URL
return redirect("projects:list", team_slug=team_slug)

# With query string
from django.urls import reverse
url = reverse("projects:list", kwargs={"team_slug": team_slug})
return redirect(f"{url}?created=true")
```

### JSON Response

```python
from django.http import JsonResponse

return JsonResponse({"status": "ok", "data": data})
return JsonResponse({"error": "Not found"}, status=404)
```

### File Download

```python
from django.http import FileResponse

return FileResponse(open(filepath, "rb"), as_attachment=True)
```

## HTMX Integration

### Partial Template Response

```python
@login_and_team_required
def project_list_partial(request, team_slug):
    """Return just the project list (for HTMX)."""
    projects = Project.objects.for_team(request.team)
    return render(request, "projects/_list.html", {"projects": projects})
```

### HTMX Detection

```python
@login_and_team_required
def project_list(request, team_slug):
    projects = Project.objects.for_team(request.team)

    # Check if HTMX request
    if request.headers.get("HX-Request"):
        return render(request, "projects/_list.html", {"projects": projects})

    return render(request, "projects/list.html", {"projects": projects})
```

### HTMX Headers

```python
from django.http import HttpResponse

@login_and_team_required
def project_delete(request, team_slug, project_id):
    project = get_object_or_404(...)
    project.delete()

    response = HttpResponse()
    response["HX-Trigger"] = "projectDeleted"
    response["HX-Redirect"] = reverse("projects:list", kwargs={"team_slug": team_slug})
    return response
```

## Error Handling

### 404 Pattern

```python
from django.http import Http404

@login_and_team_required
def project_detail(request, team_slug, project_id):
    try:
        project = Project.objects.for_team(request.team).get(id=project_id)
    except Project.DoesNotExist:
        raise Http404("Project not found")

    # Or use shortcut:
    project = get_object_or_404(
        Project.objects.for_team(request.team),
        id=project_id
    )
```

### Form Validation Errors

```python
@login_and_team_required
def project_create(request, team_slug):
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            # ... save
            pass
        else:
            # Form errors will be displayed in template
            messages.error(request, "Please correct the errors below.")
    else:
        form = ProjectForm()

    return render(request, "projects/create.html", {"form": form})
```

### Permission Denied

```python
from django.core.exceptions import PermissionDenied

@login_and_team_required
def sensitive_action(request, team_slug):
    if not request.user.is_team_admin(request.team):
        raise PermissionDenied("Admin access required")
    # ...
```
