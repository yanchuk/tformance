# Celery Background Tasks Guide

## Table of Contents
1. [Task Structure](#task-structure)
2. [Task Types](#task-types)
3. [Scheduling](#scheduling)
4. [Error Handling](#error-handling)
5. [Best Practices](#best-practices)

## Task Structure

### Basic Task

```python
# apps/myapp/tasks.py
from celery import shared_task

@shared_task
def process_data(data_id):
    """Process data in the background."""
    from .models import Data  # Import inside to avoid circular imports

    data = Data.objects.get(id=data_id)
    # Do processing...
    data.processed = True
    data.save()
```

### Calling Tasks

```python
# Async (returns immediately)
process_data.delay(data.id)

# With options
process_data.apply_async(
    args=[data.id],
    countdown=60,  # Delay 60 seconds
    expires=3600,  # Expire after 1 hour
)

# Sync (for testing)
process_data(data.id)
```

## Task Types

### Simple Task (No Return)

```python
@shared_task
def send_notification(user_id, message):
    """Send a notification to a user."""
    from apps.users.models import CustomUser

    user = CustomUser.objects.get(id=user_id)
    # Send notification...
```

### Task with Return Value

```python
@shared_task
def calculate_metrics(team_id):
    """Calculate team metrics and return result."""
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    metrics = {
        "total_commits": calculate_commits(team),
        "total_prs": calculate_prs(team),
    }
    return metrics

# Getting result (if needed)
result = calculate_metrics.delay(team.id)
metrics = result.get(timeout=30)  # Wait up to 30 seconds
```

### Task with Retry

```python
@shared_task(
    bind=True,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3}
)
def sync_github_data(self, team_id):
    """Sync data from GitHub API."""
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)
    try:
        # Call GitHub API...
        pass
    except RateLimitError:
        # Retry after rate limit resets
        raise self.retry(countdown=60)
```

## Scheduling

### Periodic Tasks (Celery Beat)

```python
# tformance/celery.py or settings
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Run daily at 2 AM UTC
    "daily-github-sync": {
        "task": "apps.integrations.tasks.sync_all_github_data",
        "schedule": crontab(hour=2, minute=0),
    },

    # Run every hour
    "hourly-metrics-update": {
        "task": "apps.metrics.tasks.update_metrics",
        "schedule": crontab(minute=0),
    },

    # Run every 15 minutes
    "frequent-check": {
        "task": "apps.monitoring.tasks.check_status",
        "schedule": crontab(minute="*/15"),
    },
}
```

### Dynamic Scheduling

```python
@shared_task
def schedule_team_sync(team_id):
    """Schedule sync based on team settings."""
    from apps.teams.models import Team

    team = Team.objects.get(id=team_id)

    if team.sync_frequency == "hourly":
        sync_github_data.apply_async(args=[team_id], countdown=3600)
    elif team.sync_frequency == "daily":
        sync_github_data.apply_async(args=[team_id], countdown=86400)
```

## Error Handling

### Handling Failures

```python
@shared_task(bind=True)
def risky_task(self, data_id):
    """Task with error handling."""
    try:
        # Do work...
        pass
    except SomeExpectedException as e:
        # Log and continue
        logger.warning(f"Expected error: {e}")
    except Exception as e:
        # Log unexpected error
        logger.error(f"Unexpected error in risky_task: {e}")
        raise  # Re-raise to mark task as failed
```

### Task Callbacks

```python
from celery import chain

@shared_task
def on_success(result, task_id, team_id):
    """Called when sync succeeds."""
    from apps.teams.models import Team
    team = Team.objects.get(id=team_id)
    team.last_sync_status = "success"
    team.save()

@shared_task
def on_failure(task_id, exc, traceback, team_id):
    """Called when sync fails."""
    from apps.teams.models import Team
    team = Team.objects.get(id=team_id)
    team.last_sync_status = "failed"
    team.last_sync_error = str(exc)
    team.save()

# Usage with callbacks
sync_github_data.apply_async(
    args=[team.id],
    link=on_success.s(team.id),
    link_error=on_failure.s(team.id),
)
```

## Best Practices

### 1. Keep Tasks Simple

```python
# Good: Simple task that does one thing
@shared_task
def send_email(user_id, template, context):
    """Send a single email."""
    # ...

# Bad: Complex task with too much logic
@shared_task
def process_everything(team_id):
    """Does too many things."""
    # Sync GitHub
    # Sync Jira
    # Calculate metrics
    # Send emails
    # Update dashboards
    # ...
```

### 2. Use IDs, Not Objects

```python
# Good: Pass IDs
@shared_task
def process_project(project_id):
    project = Project.objects.get(id=project_id)
    # ...

# Bad: Passing objects (can't be serialized)
@shared_task
def process_project(project):  # Won't work!
    # ...
```

### 3. Idempotent Tasks

```python
@shared_task
def sync_repository(repo_id, sync_id):
    """Idempotent sync - safe to retry."""
    from .models import Repository, SyncLog

    # Check if already synced
    if SyncLog.objects.filter(sync_id=sync_id, status="completed").exists():
        return  # Already done

    repo = Repository.objects.get(id=repo_id)
    # Do sync...

    SyncLog.objects.create(sync_id=sync_id, status="completed")
```

### 4. Task Timeouts

```python
@shared_task(time_limit=300, soft_time_limit=240)
def long_running_task(data_id):
    """Task with 5-minute hard limit, 4-minute soft limit."""
    try:
        # Do work...
        pass
    except SoftTimeLimitExceeded:
        # Clean up and exit gracefully
        logger.warning("Task taking too long, exiting gracefully")
        return
```

### 5. Batch Processing

```python
@shared_task
def process_all_teams():
    """Dispatch individual tasks for each team."""
    from apps.teams.models import Team

    team_ids = Team.objects.values_list("id", flat=True)

    for team_id in team_ids:
        process_team.delay(team_id)

@shared_task
def process_team(team_id):
    """Process a single team."""
    # ...
```

### Running Celery

```bash
# Start worker
make celery-worker

# Start beat scheduler
make celery-beat

# Or together in dev
make celery-dev
```
