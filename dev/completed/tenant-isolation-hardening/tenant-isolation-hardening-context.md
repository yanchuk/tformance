# Tenant Isolation Hardening - Context Document

**Last Updated:** 2025-12-13
**Status:** Phase 1 COMPLETE - Linting Rule Implemented

---

## Critical Files

### Core Architecture
| File | Purpose | Lines |
|------|---------|-------|
| `apps/teams/models.py` | BaseTeamModel, TeamScopedManager | 94-131 |
| `apps/teams/context.py` | `get_current_team()`, `set_current_team()` | All |
| `tformance/settings.py` | `STRICT_TEAM_CONTEXT = not DEBUG` | 665-668 |

### Models Using BaseTeamModel
| File | Models |
|------|--------|
| `apps/metrics/models.py` | TeamMember, PullRequest, PRReview, Commit, JiraIssue, AIUsageDaily, PRSurvey, PRSurveyReview, WeeklyMetrics |
| `apps/integrations/models.py` | IntegrationCredential, GitHubIntegration, TrackedRepository, JiraIntegration, TrackedJiraProject, SlackIntegration |

### Files to Audit for `.objects.` Usage
**Production Code (High Priority):**
- `apps/metrics/processors.py`
- `apps/metrics/services/survey_tokens.py`
- `apps/metrics/services/survey_service.py`
- `apps/metrics/services/dashboard_service.py`
- `apps/integrations/views.py`
- `apps/integrations/tasks.py`
- `apps/integrations/services/github_sync.py`
- `apps/integrations/services/jira_sync.py`
- `apps/integrations/services/member_sync.py`
- `apps/integrations/webhooks/slack_interactions.py`

**Test Code (Lower Priority):**
- `apps/metrics/tests/*.py`
- `apps/integrations/tests/*.py`

---

## Key Decisions

### 1. Linting vs Runtime Enforcement
**Decision:** Implement linting rule first, then consider manager swap
**Rationale:**
- Non-breaking change
- Catches issues at development time
- Can be progressively tightened
- Runtime enforcement already exists via `STRICT_TEAM_CONTEXT`

### 2. Manager Naming Convention
**If manager swap is implemented:**
- `objects` → renamed to `unscoped` (explicit opt-in for unfiltered)
- `for_team` → becomes default `objects`
- Or: keep both, just swap which is `_default_manager`

### 3. Admin Access Pattern
**Decision:** Admin must use explicit `unscoped` manager
**Rationale:**
- Django Admin needs unfiltered access for superusers
- Superuser access is already properly gated
- Configure via `ModelAdmin.get_queryset()`

### 4. Test Code Handling
**Decision:** Tests can use `.objects.` with `# noqa: TEAM001`
**Rationale:**
- Tests legitimately need to create/verify data across teams
- Security isolation tests specifically need unfiltered access
- Suppression comment makes intent explicit

---

## Existing Security Controls

### Already Implemented
1. **`STRICT_TEAM_CONTEXT = not DEBUG`** - Raises exception when `for_team` used without context
2. **`@login_and_team_required` decorator** - Ensures team context in views
3. **`@team_admin_required` decorator** - Admin-only operations
4. **Cross-team isolation tests** - `apps/metrics/tests/test_security_isolation.py`

### Gap
- Nothing prevents `Model.objects.filter()` usage (bypasses all above)

---

## Code Patterns

### Current (Unsafe)
```python
# Views/Services - IDOR risk if team not filtered
pr = PullRequest.objects.get(id=pr_id)  # Could return any team's PR!
```

### Safe Patterns
```python
# Pattern 1: Explicit team filter
pr = PullRequest.objects.get(id=pr_id, team=team)

# Pattern 2: Use scoped manager (requires team context)
pr = PullRequest.for_team.get(id=pr_id)

# Pattern 3: Filter from request context
pr = PullRequest.objects.filter(team=request.team).get(id=pr_id)
```

### After Manager Swap (Future)
```python
# Default manager is team-scoped
pr = PullRequest.objects.get(id=pr_id)  # Auto-filtered to current team

# Explicit unfiltered access for admin
all_prs = PullRequest.unscoped.all()  # Must opt-in
```

---

## Linting Rule Specification

### Rule ID: `TEAM001`

**Pattern to detect:**
```python
# Flag these patterns on BaseTeamModel subclasses:
Model.objects.filter(...)
Model.objects.get(...)
Model.objects.all()
Model.objects.exclude(...)
Model.objects.create(...)  # OK - always includes team FK
```

**Allowed patterns:**
```python
Model.objects.filter(team=...)      # Explicit team filter
Model.objects.get(team=..., ...)    # Explicit team filter
Model.for_team.filter(...)          # Scoped manager
Model.unscoped.all()                # Explicit unscoped (future)
```

**Suppression:**
```python
# noqa: TEAM001 - Intentional unscoped access for [reason]
```

---

## Dependencies

| Dependency | Status | Notes |
|------------|--------|-------|
| `STRICT_TEAM_CONTEXT` | ✅ Implemented | `tformance/settings.py:665-668` |
| ruff linter | ✅ Available | Already configured in project |
| Cross-team tests | ✅ Implemented | `test_security_isolation.py` |
| Django Admin | ✅ Works | Needs `unscoped` manager after swap |

---

## Testing Strategy

### Unit Tests for Linter
- Test detection of `.objects.` patterns
- Test allowlist for explicit team filters
- Test `# noqa` suppression works

### Integration Tests
- Run linter on codebase, verify expected violations
- Test that fixes don't break functionality
- Verify admin still works after manager swap

### Security Tests
- Add more cross-team isolation tests
- Test all API endpoints for IDOR
- Test webhook handlers for tenant leakage

---

## Rollback Plan

### Linting Rule
- Remove from CI configuration
- Remove pre-commit hook
- No code changes needed

### Manager Swap
- Revert `BaseTeamModel` changes
- No data migration needed (schema unchanged)
- May need to update code that used `unscoped`
