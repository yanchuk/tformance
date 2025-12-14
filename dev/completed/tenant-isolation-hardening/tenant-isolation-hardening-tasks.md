# Tenant Isolation Hardening - Tasks

**Last Updated:** 2025-12-13
**Status:** Phase 1 COMPLETE - Linting Rule Implemented

---

## Phase 1: Linting Rule

### Section 1.1: Create Custom Linter
- [x] Research ruff custom rule implementation (AST visitor pattern)
- [x] Create `scripts/lint_team_isolation.py` with TEAM001 rule
- [x] Detect `.objects.` access on BaseTeamModel subclasses
- [x] Allow patterns with explicit `team=` filter
- [x] Allow `for_team` manager usage
- [x] Support `# noqa: TEAM001` suppression
- [x] Write unit tests for linter (20 tests)

### Section 1.2: CI Integration
- [x] Add linting rule to pre-commit config
- [ ] Add to CI pipeline (GitHub Actions) - optional
- [x] Configure baseline for existing violations (20 noqa comments added)
- [x] Document suppression pattern in CLAUDE.md

---

## Phase 2: Code Audit & Migration

### Section 2.1: Audit Production Code
Files to review for `.objects.` usage:

**High Priority (Views/Services):**
- [ ] `apps/metrics/processors.py`
- [ ] `apps/metrics/services/survey_tokens.py`
- [ ] `apps/metrics/services/survey_service.py`
- [ ] `apps/metrics/services/dashboard_service.py`
- [ ] `apps/integrations/views.py`
- [ ] `apps/integrations/tasks.py`
- [ ] `apps/integrations/services/github_sync.py`
- [ ] `apps/integrations/services/jira_sync.py`
- [ ] `apps/integrations/services/member_sync.py`
- [ ] `apps/integrations/webhooks/slack_interactions.py`

**Medium Priority (Webhooks/Tasks):**
- [ ] `apps/web/views.py` (webhook handlers)
- [ ] `apps/integrations/webhooks/*.py`

### Section 2.2: Fix Identified Issues
- [ ] Replace `Model.objects.filter()` with `Model.objects.filter(team=team)`
- [ ] Or use `Model.for_team.filter()` where team context available
- [ ] Add cross-team isolation tests for fixed paths
- [ ] Verify all tests pass after fixes

---

## Phase 3: Manager Swap (Optional)

### Section 3.1: Update BaseTeamModel
- [ ] Rename `objects` to `unscoped`
- [ ] Make `for_team` the default `objects` manager
- [ ] Update `_default_manager` configuration
- [ ] Add migration if needed (schema unchanged, but Meta changes)

### Section 3.2: Update Admin Configuration
- [ ] Configure `ModelAdmin.get_queryset()` to use `unscoped`
- [ ] Test admin interface for all affected models
- [ ] Verify superuser can see all teams' data

### Section 3.3: Update Code References
- [ ] Search for remaining `.objects.` usages
- [ ] Update to `.unscoped.` for legitimate unfiltered access
- [ ] Add `# Intentional unscoped access` comments
- [ ] Run full test suite

---

## Phase 4: Documentation & Testing

### Section 4.1: Documentation
- [ ] Document `for_team` vs `objects` patterns in CLAUDE.md
- [ ] Add PR checklist item for team-scoped queries
- [ ] Update onboarding docs for new developers

### Section 4.2: Security Testing
- [ ] Add more cross-team isolation tests
- [ ] Test all API endpoints for IDOR
- [ ] Test webhook handlers for tenant leakage
- [ ] Verify admin isolation in multi-tenant scenarios

---

## Verification Checklist

Before marking complete:
- [ ] All tests pass: `make test ARGS='--keepdb'`
- [ ] Linting rule catches new violations
- [ ] No regressions in existing functionality
- [ ] Admin interface works for superusers
- [ ] Cross-team data access impossible for regular users

---

## Quick Reference

### Safe Patterns
```python
# Pattern 1: Explicit team filter
pr = PullRequest.objects.get(id=pr_id, team=team)

# Pattern 2: Use scoped manager
pr = PullRequest.for_team.get(id=pr_id)

# Pattern 3: Filter from request
pr = PullRequest.objects.filter(team=request.team).get(id=pr_id)
```

### Unsafe Pattern
```python
# DANGEROUS - Returns any team's PR!
pr = PullRequest.objects.get(id=pr_id)
```

### Test Suppression
```python
# noqa: TEAM001 - Test needs unfiltered access for setup
PullRequest.objects.create(team=other_team, ...)
```
