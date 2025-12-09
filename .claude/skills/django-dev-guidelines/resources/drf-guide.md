# Django REST Framework Guide

## Table of Contents
1. [Serializers](#serializers)
2. [ViewSets](#viewsets)
3. [Permissions](#permissions)
4. [URL Configuration](#url-configuration)
5. [Error Handling](#error-handling)
6. [Pagination](#pagination)

## Serializers

### Basic Serializer

```python
from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
```

### Nested Serializer

```python
class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = ["id", "title", "status"]

class ProjectDetailSerializer(serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    created_by = serializers.StringRelatedField()

    class Meta:
        model = Project
        fields = ["id", "name", "description", "tasks", "created_by", "created_at"]
```

### Validation

```python
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description"]

    def validate_name(self, value):
        """Validate the name field."""
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters.")
        return value

    def validate(self, data):
        """Object-level validation."""
        if data.get("start_date") and data.get("end_date"):
            if data["start_date"] > data["end_date"]:
                raise serializers.ValidationError("End date must be after start date.")
        return data
```

### Create/Update Override

```python
class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "name", "description"]

    def create(self, validated_data):
        """Set team and created_by on creation."""
        request = self.context.get("request")
        validated_data["team"] = request.team
        validated_data["created_by"] = request.user
        return super().create(validated_data)
```

## ViewSets

### Basic ViewSet

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Project
from .serializers import ProjectSerializer

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Return projects for the current team."""
        return Project.objects.for_team(self.request.team)

    def perform_create(self, serializer):
        """Set team and created_by on creation."""
        serializer.save(
            team=self.request.team,
            created_by=self.request.user
        )
```

### Read-Only ViewSet

```python
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

class MetricsViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API for metrics."""
    serializer_class = MetricsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Metrics.objects.for_team(self.request.team)
```

### Custom Actions

```python
from rest_framework.decorators import action
from rest_framework.response import Response

class ProjectViewSet(viewsets.ModelViewSet):
    # ...

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate a project."""
        project = self.get_object()
        project.activate()
        return Response({"status": "activated"})

    @action(detail=False, methods=["get"])
    def active(self, request):
        """List only active projects."""
        projects = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)
```

## Permissions

### Custom Team Permission

```python
from rest_framework import permissions

class IsTeamMember(permissions.BasePermission):
    """Check if user is a member of the team."""

    def has_permission(self, request, view):
        # Assumes team is set on request by middleware
        if not hasattr(request, "team"):
            return False
        return request.team.is_member(request.user)

class IsTeamAdmin(permissions.BasePermission):
    """Check if user is an admin of the team."""

    def has_permission(self, request, view):
        if not hasattr(request, "team"):
            return False
        return request.team.is_admin(request.user)
```

### Using Permissions

```python
class ProjectViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsTeamMember]

    def get_permissions(self):
        """Different permissions for different actions."""
        if self.action in ["destroy", "update"]:
            return [IsAuthenticated(), IsTeamAdmin()]
        return [IsAuthenticated(), IsTeamMember()]
```

## URL Configuration

### Router Setup

```python
# apps/api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProjectViewSet, MetricsViewSet

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"metrics", MetricsViewSet, basename="metrics")

urlpatterns = [
    path("v1/", include(router.urls)),
]

# Main urls.py
urlpatterns = [
    path("api/", include("apps.api.urls")),
]
```

### Team-Scoped API URLs

```python
# For team-scoped APIs
# apps/api/urls.py
team_urlpatterns = [
    path("", include(router.urls)),
]

# Results in: /a/<team_slug>/api/v1/projects/
```

## Error Handling

### Custom Exception Handler

```python
# apps/api/exceptions.py
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        # Unhandled exception
        return Response(
            {"error": "Internal server error"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # Add error code
    if isinstance(response.data, dict):
        response.data["status_code"] = response.status_code

    return response
```

### In Settings

```python
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "apps.api.exceptions.custom_exception_handler",
}
```

## Pagination

### Configure Pagination

```python
# settings.py
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}
```

### Custom Pagination

```python
from rest_framework.pagination import PageNumberPagination

class LargeResultsPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = "page_size"
    max_page_size = 1000

class ProjectViewSet(viewsets.ModelViewSet):
    pagination_class = LargeResultsPagination
```

### Cursor Pagination (for large datasets)

```python
from rest_framework.pagination import CursorPagination

class MetricsCursorPagination(CursorPagination):
    page_size = 100
    ordering = "-created_at"

class MetricsViewSet(viewsets.ReadOnlyModelViewSet):
    pagination_class = MetricsCursorPagination
```
