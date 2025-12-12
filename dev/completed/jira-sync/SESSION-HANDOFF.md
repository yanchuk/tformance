# Session Handoff: Phase 3.2 Jira Sync

**Date:** 2025-12-11
**Branch:** main (uncommitted changes)
**Tests:** 776 passing

---

## Session Summary

Implemented Phase 3.2 Jira Project Sync using TDD. Completed Sections 1-5 (model, client, views, user matching, issue sync). Section 5 GREEN phase done, REFACTOR phase was interrupted.

---

## Immediate Next Steps

### 1. Complete Section 5 REFACTOR (quick)

Run the `tdd-refactorer` agent on Section 5 Issue Sync:
```
Evaluate and refactor apps/integrations/services/jira_sync.py
- Test file: apps/integrations/tests/test_jira_sync.py
- Check lint, type hints, docstrings
- Run: make test ARGS='--keepdb' && make ruff
```

### 2. Section 6: Celery Tasks (TDD)

Use TDD pattern for each task:

**6.1 sync_jira_project_task**
- Accept project_id
- Call sync_project_issues()
- Retry with exponential backoff

**6.2 sync_all_jira_projects_task**
- Query active TrackedJiraProject
- Dispatch individual tasks
- Add to Celery Beat (daily)

**6.3 sync_jira_users_task**
- Accept team_id
- Call sync_jira_users()

### 3. Section 7: UI Integration

Update `templates/integrations/home.html`:
- Add Jira section showing connection status
- Show tracked projects count
- Link to jira_projects_list view

### 4. Commit All Work

After Section 7:
```bash
git add -A
git commit -m "$(cat <<'EOF'
Implement Phase 3.2: Jira Project Sync

- Add TrackedJiraProject model for tracking synced projects
- Implement jira-python client with bearer token auth
- Add project selection views (list, toggle)
- Implement user matching by email
- Implement issue sync service with full/incremental sync
- Add 69 new tests (776 total)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Files Changed (Uncommitted)

### New Files
- `apps/integrations/services/jira_client.py` - Jira API client
- `apps/integrations/services/jira_sync.py` - Issue sync service
- `apps/integrations/services/jira_user_matching.py` - User matching
- `apps/integrations/tests/test_jira_client.py` - 13 tests
- `apps/integrations/tests/test_jira_sync.py` - 16 tests
- `apps/integrations/tests/test_jira_user_matching.py` - 12 tests
- `apps/integrations/tests/test_jira_views_projects.py` - 16 tests
- `apps/integrations/migrations/0009_trackedjiraproject.py`
- `apps/integrations/migrations/0010_rename_tracked_jira_sync_idx_*.py`
- `templates/integrations/jira_projects_list.html`

### Modified Files
- `apps/integrations/models.py` - Added TrackedJiraProject
- `apps/integrations/factories.py` - Added TrackedJiraProjectFactory
- `apps/integrations/admin.py` - Added admin for TrackedJiraProject
- `apps/integrations/tests/test_models.py` - 12 new tests
- `apps/integrations/views.py` - Added jira_projects_list, jira_project_toggle
- `apps/integrations/urls.py` - Added jira/projects/ URLs
- `pyproject.toml`, `uv.lock` - Added jira==3.10.5

---

## Key Patterns Established

### Bearer Token Auth (jira_client.py)
```python
headers = JIRA.DEFAULT_OPTIONS["headers"].copy()
headers["Authorization"] = f"Bearer {access_token}"
jira = JIRA(server=f"https://api.atlassian.com/ex/jira/{cloud_id}", options={"headers": headers})
```

### Issue Sync Pattern (jira_sync.py)
```python
def sync_project_issues(tracked_project, full_sync=False):
    since = None if full_sync else tracked_project.last_sync_at
    issues_data = get_project_issues(credential, project_key, since=since)
    for issue_data in issues_data:
        JiraIssue.objects.update_or_create(team=team, jira_id=..., defaults={...})
```

### User Matching Pattern (jira_user_matching.py)
```python
# Case-insensitive email match
TeamMember.objects.get(team=team, email__iexact=email)
```

---

## Verification Commands

```bash
# Pre-flight
make test ARGS='--keepdb'  # Expect 776 pass

# Section tests
make test ARGS='apps.integrations.tests.test_jira_sync --keepdb'

# Lint
make ruff

# Migrations (already applied)
make migrations  # Should say "No changes detected"
```

---

## Test Count Breakdown

| Section | File | Tests |
|---------|------|-------|
| 1. Model | test_models.py | 12 |
| 2. Client | test_jira_client.py | 13 |
| 3. Views | test_jira_views_projects.py | 16 |
| 4. User Matching | test_jira_user_matching.py | 12 |
| 5. Issue Sync | test_jira_sync.py | 16 |
| **Total New** | | **69** |
| **Total Suite** | | **776** |
