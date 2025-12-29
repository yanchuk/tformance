# Async GitHub Member Sync - Task Checklist

**Last Updated: 2025-12-29**

## TDD Workflow

Each task follows Red-Green-Refactor:
1. **RED**: Write failing test first
2. **GREEN**: Implement minimum code to pass
3. **REFACTOR**: Clean up while keeping tests green

---

## Phase 1: Model Changes

### 1.1 Add member sync status fields to GitHubIntegration
- [ ] **RED**: Write test that `GitHubIntegration` has `member_sync_status` field
- [ ] **RED**: Write test that `GitHubIntegration` has `member_sync_started_at` field
- [ ] **RED**: Write test that `GitHubIntegration` has `member_sync_completed_at` field
- [ ] **RED**: Write test that `GitHubIntegration` has `member_sync_error` field
- [ ] **RED**: Write test that `GitHubIntegration` has `member_sync_result` field
- [ ] **GREEN**: Add fields to model
- [ ] **GREEN**: Create migration
- [ ] **GREEN**: Apply migration
- [ ] **REFACTOR**: Verify all tests pass

**Acceptance Criteria**:
- [ ] Migration runs without errors
- [ ] Fields have correct defaults
- [ ] Model tests pass

---

## Phase 2: Update Celery Task

### 2.1 Update `sync_github_members_task` to set status fields
- [ ] **RED**: Test task sets `member_sync_status` to "syncing" at start
- [ ] **RED**: Test task sets `member_sync_status` to "complete" on success
- [ ] **RED**: Test task stores result in `member_sync_result`
- [ ] **RED**: Test task sets `member_sync_status` to "error" on failure
- [ ] **RED**: Test task stores error message in `member_sync_error`
- [ ] **GREEN**: Implement status updates in task
- [ ] **REFACTOR**: Extract common status update logic if needed

**Acceptance Criteria**:
- [ ] Task updates status before sync starts
- [ ] Task updates status after sync completes/fails
- [ ] Result counts stored in JSON field
- [ ] Error messages captured

---

## Phase 3: Views & Templates

### 3.1 Update `github_members_sync` view
- [ ] **RED**: Test view queues `sync_github_members_task.delay()`
- [ ] **RED**: Test view sets `member_sync_status` to "syncing"
- [ ] **RED**: Test view returns HTML partial (not redirect)
- [ ] **RED**: Test partial contains "Syncing" text
- [ ] **GREEN**: Update view to queue task and return partial
- [ ] **REFACTOR**: Remove synchronous sync call

**Acceptance Criteria**:
- [ ] View no longer blocks
- [ ] Returns HTML partial for HTMX swap
- [ ] Status set immediately before queuing task

### 3.2 Add progress polling endpoint
- [ ] **RED**: Test `github_members_sync_progress` returns 200
- [ ] **RED**: Test returns current sync status in HTML
- [ ] **RED**: Test includes HTMX polling when syncing
- [ ] **RED**: Test stops polling when complete
- [ ] **GREEN**: Create view and add URL pattern
- [ ] **REFACTOR**: Ensure consistent with repo sync progress pattern

**Acceptance Criteria**:
- [ ] Endpoint returns partial template
- [ ] HTMX polling attributes present when syncing
- [ ] No polling when complete/error

### 3.3 Create progress partial template
- [ ] Create `integrations/partials/member_sync_progress.html`
- [ ] Show spinner when syncing
- [ ] Show success badge when complete
- [ ] Show error badge when failed
- [ ] Include result counts when available

**Acceptance Criteria**:
- [ ] Template renders without errors
- [ ] HTMX attributes correct
- [ ] Styling matches design system

### 3.4 Update members page template
- [ ] Change form submit to HTMX button
- [ ] Add `hx-post`, `hx-target`, `hx-swap` attributes
- [ ] Add `#member-sync-status` target element

**Acceptance Criteria**:
- [ ] Button triggers HTMX POST
- [ ] Progress partial swapped into target
- [ ] No page reload

---

## Phase 4: Update Helper Function

### 4.1 Convert `_sync_github_members_after_connection` to async
- [ ] **RED**: Test helper queues `sync_github_members_task.delay()`
- [ ] **RED**: Test helper returns immediately (0)
- [ ] **GREEN**: Update helper to queue task
- [ ] **REFACTOR**: Update success message in `github_select_org`

**Acceptance Criteria**:
- [ ] Helper no longer blocks
- [ ] Returns 0 (sync count unknown until complete)
- [ ] Success message updated to "syncing in background"

---

## Phase 5: Update Existing Tests

### 5.1 Update `test_views.py` sync tests
- [ ] Change mock from `member_sync.sync_github_members` to `sync_github_members_task.delay`
- [ ] Update assertions for HTML partial response
- [ ] Remove redirect assertions (now returns partial)
- [ ] Update success message tests

**Acceptance Criteria**:
- [ ] All existing tests pass or updated
- [ ] No test regressions

---

## Phase 6: Final Verification

### 6.1 Run full test suite
- [ ] `make test` passes
- [ ] No regressions

### 6.2 Manual testing
- [ ] Click "Sync Now" on members page
- [ ] See spinner immediately
- [ ] See success badge when complete
- [ ] Members list updates after refresh
- [ ] Onboarding flow completes quickly
- [ ] Members appear after background sync

### 6.3 Commit and push
- [ ] Commit with descriptive message
- [ ] Push to main
- [ ] CI passes

---

## Files Modified Checklist

- [ ] `apps/integrations/models.py` - Add 5 fields
- [ ] `apps/integrations/migrations/0005_*.py` - New migration
- [ ] `apps/integrations/tasks.py` - Update task
- [ ] `apps/integrations/views/github.py` - Update view + add endpoint
- [ ] `apps/integrations/views/helpers.py` - Update helper
- [ ] `apps/integrations/urls.py` - Add URL
- [ ] `apps/integrations/templates/integrations/partials/member_sync_progress.html` - New
- [ ] `apps/integrations/templates/integrations/github_members.html` - HTMX
- [ ] `apps/integrations/tests/test_views.py` - Update tests
- [ ] `apps/integrations/tests/test_tasks.py` - Add tests (if needed)
