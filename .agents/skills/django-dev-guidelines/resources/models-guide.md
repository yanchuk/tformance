# Django Models Guide

## Table of Contents
1. [Base Classes](#base-classes)
2. [Field Patterns](#field-patterns)
3. [Model Methods](#model-methods)
4. [Manager Patterns](#manager-patterns)
5. [Relationships](#relationships)
6. [Migration Best Practices](#migration-best-practices)

## Base Classes

### BaseModel (Non-Team Data)

Use for data that doesn't belong to a team:

```python
from apps.utils.models import BaseModel

class GlobalConfig(BaseModel):
    """Configuration that applies globally."""
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)

    class Meta:
        verbose_name = "Global Configuration"
```

**BaseModel provides:**
- `id` - UUID primary key
- `created_at` - Auto-set on creation
- `updated_at` - Auto-updated on save

### BaseTeamModel (Team-Scoped Data)

Use for most models - data owned by a team:

```python
from apps.teams.models import BaseTeamModel

class Project(BaseTeamModel):
    """A project belonging to a team."""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Project"
        ordering = ["-created_at"]
```

**BaseTeamModel provides:**
- Everything from BaseModel
- `team` - ForeignKey to Team
- `for_team` manager for team-scoped queries

## Field Patterns

### Common Field Types

```python
class ExampleModel(BaseTeamModel):
    # Text fields
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=100)

    # Numbers
    count = models.IntegerField(default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Booleans
    is_active = models.BooleanField(default=True)

    # Dates
    start_date = models.DateField(null=True, blank=True)
    last_synced = models.DateTimeField(null=True, blank=True)

    # JSON
    metadata = models.JSONField(default=dict, blank=True)

    # Choices
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("active", "Active"),
        ("completed", "Completed"),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
```

### User References

```python
from apps.users.models import CustomUser

class Task(BaseTeamModel):
    # Creator - required
    created_by = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="created_tasks"
    )

    # Assignee - optional
    assigned_to = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )
```

## Model Methods

### Properties

```python
class Subscription(BaseTeamModel):
    end_date = models.DateTimeField()

    @property
    def is_expired(self):
        """Check if subscription has expired."""
        return timezone.now() > self.end_date

    @property
    def days_remaining(self):
        """Days until expiration."""
        if self.is_expired:
            return 0
        delta = self.end_date - timezone.now()
        return delta.days
```

### Instance Methods

```python
class Project(BaseTeamModel):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def activate(self):
        """Activate this project."""
        self.is_active = True
        self.save(update_fields=["is_active", "updated_at"])

    def deactivate(self):
        """Deactivate this project."""
        self.is_active = False
        self.save(update_fields=["is_active", "updated_at"])

    def __str__(self):
        return self.name
```

## Manager Patterns

### Using for_team

Always use `for_team` for team-scoped queries:

```python
# In views
@login_and_team_required
def project_list(request, team_slug):
    # Correct: uses for_team manager
    projects = Project.objects.for_team(request.team)

    # WRONG: bypasses team scoping
    # projects = Project.objects.filter(team=request.team)

    return render(request, "projects/list.html", {"projects": projects})
```

### Custom Managers

```python
class ProjectManager(models.Manager):
    def active(self):
        """Return only active projects."""
        return self.filter(is_active=True)

    def with_stats(self):
        """Annotate with statistics."""
        return self.annotate(
            task_count=Count("tasks"),
            completed_count=Count("tasks", filter=Q(tasks__status="completed"))
        )

class Project(BaseTeamModel):
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    objects = ProjectManager()

# Usage
active_projects = Project.objects.for_team(team).active()
projects_with_stats = Project.objects.for_team(team).with_stats()
```

## Relationships

### One-to-Many (ForeignKey)

```python
class Repository(BaseTeamModel):
    name = models.CharField(max_length=255)

class Commit(BaseTeamModel):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name="commits"
    )
    sha = models.CharField(max_length=40)
    message = models.TextField()

# Usage
repo = Repository.objects.get(id=repo_id)
commits = repo.commits.all()  # Uses related_name
```

### Many-to-Many

```python
class Tag(BaseTeamModel):
    name = models.CharField(max_length=50)

class Project(BaseTeamModel):
    name = models.CharField(max_length=255)
    tags = models.ManyToManyField(Tag, blank=True, related_name="projects")

# Usage
project.tags.add(tag)
project.tags.remove(tag)
project.tags.set([tag1, tag2])
tagged_projects = tag.projects.all()
```

## Migration Best Practices

### Creating Migrations

```bash
# After model changes
make migrations

# Check what will be created
make manage ARGS='showmigrations'

# Apply migrations
make migrate
```

### Safe Migration Patterns

```python
# Adding nullable field (safe)
new_field = models.CharField(max_length=100, null=True, blank=True)

# Adding field with default (safe)
count = models.IntegerField(default=0)

# Renaming field (use migrations.RenameField)
# Don't delete and recreate!

# Adding index
class Meta:
    indexes = [
        models.Index(fields=["status", "created_at"]),
    ]
```

### Data Migrations

```python
# Generated with: make manage ARGS='makemigrations --empty myapp'
from django.db import migrations

def populate_slugs(apps, schema_editor):
    Project = apps.get_model("myapp", "Project")
    for project in Project.objects.filter(slug=""):
        project.slug = slugify(project.name)
        project.save()

class Migration(migrations.Migration):
    dependencies = [
        ("myapp", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(populate_slugs, migrations.RunPython.noop),
    ]
```
