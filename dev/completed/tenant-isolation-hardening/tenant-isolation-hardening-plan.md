# Tenant Isolation Hardening Plan

**Last Updated:** 2025-12-13
**Priority:** HIGH (Security)
**Estimated Total Effort:** 2-3 days

---

## Executive Summary

The current multi-tenant architecture uses application-layer isolation via `BaseTeamModel` with two managers:
- `objects` (default) - unfiltered, exposes all tenants
- `for_team` - filtered to current team context

While `STRICT_TEAM_CONTEXT=True` in production raises an exception when `for_team` is used without team context, **nothing prevents accidental use of `objects` manager**, which bypasses tenant isolation entirely and can lead to IDOR vulnerabilities.

This plan implements two complementary approaches:
1. **Linting rule** - Detect `.objects.` usage on BaseTeamModel subclasses at development time
2. **Manager swap** - Make `for_team` the default manager, requiring explicit opt-in for unscoped access

---

## Current State Analysis

### Architecture
```
BaseTeamModel (abstract)
├── objects = models.Manager()      # DEFAULT - bypasses isolation
└── for_team = TeamScopedManager()  # Must be explicitly used
```

### Affected Models (16 total)
| App | Models |
|-----|--------|
| metrics | TeamMember, PullRequest, PRReview, Commit, JiraIssue, AIUsageDaily, PRSurvey, PRSurveyReview, WeeklyMetrics (9) |
| integrations | IntegrationCredential, GitHubIntegration, TrackedRepository, JiraIntegration, TrackedJiraProject, SlackIntegration (6) |
| teams_example | Player (1) |

### Current Usage Patterns
Files using `.objects.` on team models (production code):
- `apps/metrics/processors.py`
- `apps/metrics/services/*.py`
- `apps/integrations/views.py`
- `apps/integrations/tasks.py`
- `apps/integrations/services/*.py`

### Risk Assessment
- **HIGH**: Any view/service using `Model.objects.filter()` without explicit `team=team` filter leaks data
- **MEDIUM**: Admin interface requires unfiltered access (must preserve this)
- **LOW**: Tests legitimately use `.objects.` for setup/assertions

---

## Proposed Future State

### Option A: Linting Rule (Recommended First)
- Add ruff/flake8 custom rule to flag `.objects.` on BaseTeamModel subclasses
- Non-breaking, catches issues at development time
- Can be bypassed with `# noqa: TEAM001` for legitimate uses

### Option B: Manager Swap (Recommended Second)
- Make `for_team` the default manager
- Add `unscoped = models.Manager()` for admin/legitimate unfiltered access
- Breaking change - requires migration of existing code

### Combined Approach
1. Deploy linting rule first (catches new issues)
2. Audit and fix existing code
3. Swap managers (makes `for_team` default)
4. Update admin configuration

---

## Implementation Phases

### Phase 1: Linting Rule (1 day)

#### Section 1.1: Create Custom Linter
Create a ruff plugin or pre-commit hook that:
- Parses Python files for `.objects.` access patterns
- Cross-references against BaseTeamModel subclasses
- Flags violations with clear error message

#### Section 1.2: CI Integration
- Add linting rule to CI pipeline
- Configure baseline for existing violations
- Document suppression pattern for legitimate uses

### Phase 2: Code Audit & Migration (1 day)

#### Section 2.1: Audit Production Code
- Review all `.objects.` usages in views/services
- Categorize as: (a) needs fix, (b) legitimate use, (c) test code
- Document required changes

#### Section 2.2: Fix Identified Issues
- Replace `Model.objects.filter()` with `Model.objects.filter(team=team)`
- Or use `Model.for_team.filter()` where team context is available
- Add tests for fixed code paths

### Phase 3: Manager Swap (Optional, 0.5 day)

#### Section 3.1: Update BaseTeamModel
- Rename `objects` to `unscoped`
- Make `for_team` the default (named `objects`)
- Add backward compatibility alias if needed

#### Section 3.2: Update Admin Configuration
- Configure admin classes to use `unscoped` manager
- Verify admin functionality preserved

---

## Risk Assessment and Mitigation

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Linting rule too aggressive | Medium | Low | Allow `# noqa` suppression, document valid patterns |
| Breaking existing functionality | High | Medium | Comprehensive test coverage, phased rollout |
| Admin interface breaks | High | Medium | Configure admin to use explicit `unscoped` manager |
| Performance regression | Low | Low | `for_team` adds one WHERE clause - negligible |
| Developer friction | Medium | Medium | Clear documentation, IDE integration hints |

---

## Success Metrics

1. **Zero IDOR vulnerabilities** - No cross-tenant data access possible
2. **100% lint compliance** - All new code passes tenant isolation checks
3. **Test coverage** - All team-scoped models have isolation tests
4. **Developer experience** - Clear error messages, documented patterns

---

## Dependencies

- **STRICT_TEAM_CONTEXT** setting (already implemented)
- **Cross-team isolation tests** (`apps/metrics/tests/test_security_isolation.py`)
- **ruff** linter (already in use)

---

## Implementation Order

```
Week 1:
├── Day 1: Create linting rule + CI integration
├── Day 2: Audit existing code + fix critical issues
└── Day 3: Manager swap (if approved) + documentation

Future:
└── Consider Postgres RLS for defense-in-depth
```
