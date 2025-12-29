# Async GitHub Member Sync - Implementation Plan

**Last Updated: 2025-12-29**

## Executive Summary

Convert two synchronous GitHub member sync operations to async Celery tasks to improve UX and prevent request timeouts. The operations currently block HTTP responses while fetching members from the GitHub API.

### Scope

| Operation | Location | Current | Target |
|-----------|----------|---------|--------|
| Manual member sync | `github.py:191-235` | Blocks 10-30s | Async with HTMX polling |
| Post-connection sync | `helpers.py:152-172` | Blocks onboarding | Async background job |

### Key Finding

**A Celery task already exists!** `sync_github_members_task` in `tasks.py:492-539` handles async member sync. The GitHubIntegration model already has `sync_status` and `last_sync_at` fields.

We only need to:
1. Wire up views to queue the existing task
2. Add member-specific sync status fields to GitHubIntegration
3. Create HTMX partial for progress display
4. Update templates with polling

---

## Current State Analysis

### Operation 1: `github_members_sync` View

**Location**: `apps/integrations/views/github.py:191-235`

```python
# CURRENT (synchronous - BLOCKS)
@team_admin_required
def github_members_sync(request):
    integration = GitHubIntegration.objects.get(team=team)
    result = member_sync.sync_github_members(  # <-- BLOCKS
        team, integration.credential.access_token, integration.organization_slug
    )
    messages.success(request, f"Synced: {result['created']} created...")
    return redirect("integrations:github_members")
```

**Problems**:
- Blocks request for 10-30 seconds (large orgs)
- No progress feedback
- Can timeout on Heroku (30s limit)

### Operation 2: `_sync_github_members_after_connection`

**Location**: `apps/integrations/views/helpers.py:152-172`

```python
# CURRENT (synchronous - BLOCKS)
def _sync_github_members_after_connection(team, access_token, org_slug):
    result = member_sync.sync_github_members(team, access_token, org_slug)  # <-- BLOCKS
    return result["created"]
```

**Called from**: `github_select_org` view after user selects organization during onboarding.

**Problems**:
- Delays onboarding flow
- User sees no feedback during sync

### Existing Infrastructure (Reusable)

**Celery Task**: `apps/integrations/tasks.py:492-539`
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_github_members_task(self, integration_id: int) -> dict:
    """Sync GitHub organization members for a team."""
    integration = GitHubIntegration.objects.get(id=integration_id)
    result = _sync_members_with_graphql_or_rest(integration, integration.organization_slug)
    return result
```

**Model Fields**: `GitHubIntegration` already has:
- `sync_status` (pending/syncing/complete/error)
- `last_sync_at` (timestamp)

**Issue**: These fields are used for repo sync, not member sync. Need separate fields.

---

## Proposed Future State

### Operation 1: Async Manual Sync with HTMX Progress

```python
# PROPOSED
@team_admin_required
def github_members_sync(request):
    integration = GitHubIntegration.objects.get(team=team)

    # Set status immediately
    integration.member_sync_status = "syncing"
    integration.member_sync_started_at = timezone.now()
    integration.save(update_fields=["member_sync_status", "member_sync_started_at"])

    # Queue async task (non-blocking)
    sync_github_members_task.delay(integration.id)

    # Return progress partial for HTMX swap
    return render(request, "integrations/partials/member_sync_progress.html", {"integration": integration})
```

### Operation 2: Background Sync After Connection

```python
# PROPOSED
def _sync_github_members_after_connection(team, access_token, org_slug):
    integration = GitHubIntegration.objects.get(team=team)

    # Queue async task (non-blocking)
    sync_github_members_task.delay(integration.id)

    # Return immediately - sync happens in background
    return 0  # Member count unknown until sync completes
```

---

## Implementation Phases

### Phase 1: Model Changes (Effort: S)

Add member-specific sync status fields to `GitHubIntegration`:

```python
# apps/integrations/models.py
class GitHubIntegration(BaseTeamModel):
    # Existing fields for repo sync
    sync_status = ...
    last_sync_at = ...

    # NEW: Member-specific sync fields
    member_sync_status = models.CharField(
        max_length=20,
        choices=SYNC_STATUS_CHOICES,
        default=SYNC_STATUS_PENDING,
        verbose_name="Member sync status",
    )
    member_sync_started_at = models.DateTimeField(null=True, blank=True)
    member_sync_completed_at = models.DateTimeField(null=True, blank=True)
    member_sync_error = models.TextField(blank=True)
    member_sync_result = models.JSONField(null=True, blank=True)  # Store counts
```

### Phase 2: Update Celery Task (Effort: S)

Modify `sync_github_members_task` to update member sync status fields:

```python
# apps/integrations/tasks.py
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_github_members_task(self, integration_id: int) -> dict:
    integration = GitHubIntegration.objects.get(id=integration_id)

    # Set syncing status
    integration.member_sync_status = GitHubIntegration.SYNC_STATUS_SYNCING
    integration.member_sync_started_at = timezone.now()
    integration.member_sync_error = ""
    integration.save(update_fields=["member_sync_status", "member_sync_started_at", "member_sync_error"])

    try:
        result = _sync_members_with_graphql_or_rest(integration, integration.organization_slug)

        # Update success status
        integration.member_sync_status = GitHubIntegration.SYNC_STATUS_COMPLETE
        integration.member_sync_completed_at = timezone.now()
        integration.member_sync_result = result
        integration.save(update_fields=["member_sync_status", "member_sync_completed_at", "member_sync_result"])

        return result
    except Exception as exc:
        integration.member_sync_status = GitHubIntegration.SYNC_STATUS_ERROR
        integration.member_sync_error = str(exc)
        integration.save(update_fields=["member_sync_status", "member_sync_error"])
        raise
```

### Phase 3: Views & Templates (Effort: M)

#### 3.1 Update `github_members_sync` view

```python
# apps/integrations/views/github.py
@team_admin_required
def github_members_sync(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    team = request.team
    integration = get_object_or_404(GitHubIntegration, team=team)

    # Set status to syncing immediately
    integration.member_sync_status = GitHubIntegration.SYNC_STATUS_SYNCING
    integration.member_sync_started_at = timezone.now()
    integration.save(update_fields=["member_sync_status", "member_sync_started_at"])

    # Queue async task
    sync_github_members_task.delay(integration.id)

    # Return progress partial for HTMX
    return render(request, "integrations/partials/member_sync_progress.html", {"integration": integration})
```

#### 3.2 Create progress polling endpoint

```python
# apps/integrations/views/github.py
@login_and_team_required
def github_members_sync_progress(request):
    """Return member sync progress partial for HTMX polling."""
    integration = get_object_or_404(GitHubIntegration, team=request.team)
    return render(request, "integrations/partials/member_sync_progress.html", {"integration": integration})
```

#### 3.3 Create progress partial template

```html
<!-- integrations/partials/member_sync_progress.html -->
{% load i18n %}
<div id="member-sync-status" class="flex items-center gap-2"
     {% if integration.member_sync_status == 'syncing' %}
       hx-get="{% url 'integrations:github_members_sync_progress' %}"
       hx-trigger="every 3s"
       hx-swap="outerHTML"
     {% endif %}>
  {% if integration.member_sync_status == 'syncing' %}
    <span class="loading loading-spinner loading-sm"></span>
    <span class="text-sm text-base-content/70">{% translate "Syncing members..." %}</span>
  {% elif integration.member_sync_status == 'complete' %}
    <span class="app-badge app-badge-success">{% translate "Sync complete" %}</span>
    {% if integration.member_sync_result %}
      <span class="text-sm text-base-content/70">
        {{ integration.member_sync_result.created }} created,
        {{ integration.member_sync_result.updated }} updated
      </span>
    {% endif %}
  {% elif integration.member_sync_status == 'error' %}
    <span class="app-badge app-badge-error">{% translate "Sync failed" %}</span>
  {% else %}
    <span class="app-badge app-badge-default">{% translate "Ready" %}</span>
  {% endif %}
</div>
```

#### 3.4 Update members page template

```html
<!-- integrations/github_members.html (Sync Now button) -->
<button
  hx-post="{% url 'integrations:github_members_sync' %}"
  hx-target="#member-sync-status"
  hx-swap="outerHTML"
  class="app-btn-primary app-btn-sm"
>
  <svg class="w-4 h-4">...</svg>
  {% translate "Sync Now" %}
</button>
```

### Phase 4: Update Helper Function (Effort: S)

```python
# apps/integrations/views/helpers.py
def _sync_github_members_after_connection(team, access_token, org_slug):
    """Queue async member sync after connecting an integration."""
    from apps.integrations.tasks import sync_github_members_task

    try:
        integration = GitHubIntegration.objects.get(team=team)
        sync_github_members_task.delay(integration.id)
        return 0  # Sync happens in background
    except GitHubIntegration.DoesNotExist:
        return 0
```

Update the message in `github_select_org` view:
```python
# Before
messages.success(request, f"Connected to {organization_slug}. Imported {member_count} members.")

# After
messages.success(request, f"Connected to {organization_slug}. Members syncing in background.")
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Task fails silently | Medium | Medium | Add Sentry alerts, retry logic (already exists) |
| User refreshes during sync | Low | Low | HTMX polling handles this gracefully |
| Existing tests break | High | Low | Update tests to mock `.delay()` |
| Migration conflicts | Low | Medium | Create migration early, merge to main |

---

## Success Metrics

1. **No blocking requests** - Members page loads in <500ms
2. **Progress visibility** - User sees spinner/status during sync
3. **Heroku timeout eliminated** - No 30s timeout errors on member sync
4. **Tests pass** - All existing tests updated and passing
5. **TDD compliance** - Red-Green-Refactor followed for new code

---

## File Changes Summary

| File | Changes |
|------|---------|
| `apps/integrations/models.py` | Add 5 member sync status fields |
| `apps/integrations/migrations/` | New migration for fields |
| `apps/integrations/tasks.py` | Update task to set member sync status |
| `apps/integrations/views/github.py` | Queue task + add progress endpoint |
| `apps/integrations/views/helpers.py` | Queue task instead of sync |
| `apps/integrations/urls.py` | Add progress URL |
| `apps/integrations/templates/.../member_sync_progress.html` | New partial |
| `apps/integrations/templates/.../github_members.html` | HTMX button |
| `apps/integrations/tests/test_views.py` | Update sync tests |
| `apps/integrations/tests/test_tasks.py` | Test task status updates |
