# Database Security & Performance Audit - Implementation Plan

**Last Updated:** 2025-01-05
**Status:** Ready for Implementation
**Branch:** `feature/db-perf-security-audit`
**Worktree:** `../tformance-db-audit`

---

## Executive Summary

Comprehensive audit and remediation of Django/PostgreSQL codebase covering security vulnerabilities, N+1 query patterns, Celery task performance, and database optimization. All changes follow strict TDD (Red-Green-Refactor) workflow.

### Scope

| Category | Issues Found | Priority |
|----------|-------------|----------|
| Security | 4 | 2 HIGH, 2 MEDIUM |
| View/Query Performance | 6 | 1 HIGH, 4 MEDIUM, 1 LOW |
| Celery Tasks | 5 | 2 HIGH, 3 MEDIUM |
| **Total** | **15** | ~8 hours |

### Key Decisions

1. **TDD Approach**: Write failing tests first for each fix
2. **Worktree Isolation**: All changes in separate worktree
3. **Incremental Commits**: One commit per fix with tests
4. **No Index Changes**: Skip GIN index analysis (no active users yet)

---

## Current State Analysis

### Security Findings

| ID | Issue | File | Severity |
|----|-------|------|----------|
| S1 | `int()` without try/except | `apps/integrations/views/github.py:148` | HIGH |
| S2 | Unsafe int conversion | `apps/integrations/webhooks/slack_interactions.py:109,163` | HIGH |
| S3 | Security headers verification | `apps/utils/middleware.py` | MEDIUM |
| S4 | Survey token entropy | `apps/surveys/models.py` | MEDIUM |

### Performance Findings

| ID | Issue | File | Impact |
|----|-------|------|--------|
| P1 | Survey prefetch bypass | `apps/metrics/services/dashboard/pr_metrics.py:55-73` | Dashboard N+1 |
| P2 | Full object load in AI categorization | `apps/metrics/services/dashboard/ai_metrics.py:256-265` | Analytics slow |
| P3 | Multiple count queries | `apps/metrics/services/dashboard/_helpers.py:57-70` | Extra DB calls |
| P4 | Team velocity full load | `apps/metrics/services/dashboard/team_metrics.py:222-244` | Team breakdown slow |
| P5 | Repository list not cached | `apps/metrics/views/analytics_views.py:22-30` | Page load delay |
| P6 | Inconsistent .only() usage | Various dashboard services | Minor overhead |

### Celery Task Findings

| ID | Issue | File | Impact |
|----|-------|------|--------|
| C1 | N+1 in LLM batch | `apps/metrics/tasks.py:307` | Query per PR |
| C2 | Infinite self-requeue risk | `apps/integrations/_task_modules/metrics.py:238-245` | Resource drain |
| C3 | Serial team processing | `apps/metrics/tasks.py:437-482` | Task timeout |
| C4 | Silent subscription errors | `apps/subscriptions/tasks.py:9-17` | Unnoticed failures |
| C5 | Task dispatch loops | `apps/integrations/_task_modules/github_sync.py:538-545` | Broker overhead |

---

## Implementation Phases

### Phase 0: Setup (15 min)

Create worktree and branch for isolated development:

```bash
# Create worktree
cd /Users/yanchuk/Documents/GitHub/tformance
git worktree add ../tformance-db-audit -b feature/db-perf-security-audit

# Switch to worktree
cd ../tformance-db-audit

# Verify setup
make test  # Ensure all tests pass before changes
```

### Phase 1: Security Fixes (1 hour)

**Priority:** HIGH - Fix input validation vulnerabilities

#### 1.1 Fix S1: GitHub View Integer Validation
- **File:** `apps/integrations/views/github.py:148`
- **TDD Flow:**
  1. RED: Write test for invalid organization_id handling
  2. GREEN: Add try/except with form validation
  3. REFACTOR: Extract validation helper if needed

#### 1.2 Fix S2: Slack Webhook Integer Validation
- **File:** `apps/integrations/webhooks/slack_interactions.py:109,163`
- **TDD Flow:**
  1. RED: Write test for invalid survey_id handling
  2. GREEN: Add try/except with proper error response
  3. REFACTOR: Consider shared validation decorator

#### 1.3 Verify S3: Security Headers Middleware
- **File:** `apps/utils/middleware.py`
- **Action:** Audit existing headers, add missing ones

#### 1.4 Verify S4: Survey Token Entropy
- **File:** `apps/surveys/models.py`
- **Action:** Confirm UUID4 or secrets.token_urlsafe(32) usage

### Phase 2: Critical Performance Fixes (2 hours)

**Priority:** HIGH - Fix N+1 queries affecting dashboard

#### 2.1 Fix P1: Survey Prefetch Bypass
- **File:** `apps/metrics/services/dashboard/pr_metrics.py:55-73`
- **Current Problem:**
  ```python
  # Line 55: Correct prefetch
  prs = prs.prefetch_related("survey", "survey__reviews")

  # Lines 66-69: BYPASSES prefetch by iterating reviews
  reviews = survey.reviews.all()
  total_rating = sum(r.quality_rating for r in reviews...)
  ```
- **TDD Flow:**
  1. RED: Write test asserting query count < N with assertNumQueries
  2. GREEN: Use annotation for avg rating OR access prefetched data correctly
  3. REFACTOR: Extract to helper method

#### 2.2 Fix C1: LLM Batch N+1
- **File:** `apps/metrics/tasks.py:307`
- **Current Problem:**
  ```python
  # Despite prefetch_related("reviews__reviewer") at line 285
  reviewers = list(set(r.reviewer.display_name for r in pr.reviews.all()...))
  ```
- **TDD Flow:**
  1. RED: Write test asserting constant query count regardless of PR count
  2. GREEN: Access prefetched reviews without triggering new query
  3. REFACTOR: Consider caching reviewer names

#### 2.3 Fix C2: Requeue Depth Limit
- **File:** `apps/integrations/_task_modules/metrics.py:238-245`
- **Current Problem:**
  ```python
  if remaining_prs > 0:
      self.apply_async(args=[team_id], countdown=2)  # No depth limit!
  ```
- **TDD Flow:**
  1. RED: Write test for max requeue depth enforcement
  2. GREEN: Add depth counter in kwargs, check before requeue
  3. REFACTOR: Add alerting for stuck batches

### Phase 3: Medium Priority Optimizations (3 hours)

#### 3.1 Fix P2: AI Categorization Object Load
- **File:** `apps/metrics/services/dashboard/ai_metrics.py:256-265`
- **Fix:** Add `.only("id", "llm_summary", "ai_tools_detected")`

#### 3.2 Fix P3: Single Aggregation Query
- **File:** `apps/metrics/services/dashboard/_helpers.py:57-70`
- **Fix:** Replace two count queries with:
  ```python
  stats = surveys.aggregate(
      total=Count('id'),
      ai_count=Count('id', filter=Q(author_ai_assisted=True))
  )
  ```

#### 3.3 Fix C3: Parallelize Weekly Insights
- **File:** `apps/metrics/tasks.py:437-482`
- **Fix:** Dispatch individual team insight tasks instead of serial loop

#### 3.4 Fix C4: Subscription Error Handling
- **File:** `apps/subscriptions/tasks.py:9-17`
- **Fix:** Raise exception instead of returning error dict

### Phase 4: Lower Priority Improvements (2 hours)

#### 4.1 Fix P4: Team Velocity Optimization
- **File:** `apps/metrics/services/dashboard/team_metrics.py:222-244`
- **Fix:** Use `.values()` or `.only()` for specific fields

#### 4.2 Fix P5: Repository List Caching
- **File:** `apps/metrics/views/analytics_views.py:22-30`
- **Fix:** Add `@cache_page(300)` or memoization

#### 4.3 Fix C5: Batch Task Dispatch
- **File:** `apps/integrations/_task_modules/github_sync.py:538-545,648-655`
- **Fix:** Consider `celery.group()` for batch operations

---

## TDD Workflow Per Fix

For each issue, follow this strict workflow:

### 1. RED Phase
```bash
# Create test file or add to existing
# Write test that describes expected behavior
# Run test - MUST FAIL
.venv/bin/pytest path/to/test_file.py::TestClassName::test_method -v
```

### 2. GREEN Phase
```bash
# Write MINIMUM code to pass test
# No extra features
.venv/bin/pytest path/to/test_file.py::TestClassName::test_method -v
# MUST PASS
```

### 3. REFACTOR Phase
```bash
# Clean up while keeping tests green
# Run full test suite
make test
# Commit with descriptive message
git commit -m "fix(security): add int validation to github view

- Add try/except for organization_id parsing
- Return redirect with error message on invalid input
- Add test coverage for edge cases

Fixes: S1"
```

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Test coverage gaps | Medium | High | Write tests FIRST (TDD) |
| Breaking existing queries | Medium | High | Use assertNumQueries in tests |
| Celery task changes causing issues | Low | Medium | Test with Celery eager mode |
| Cache invalidation bugs | Low | Medium | Add explicit cache clear in tests |

---

## Success Metrics

- [ ] All 15 issues have test coverage
- [ ] No increase in test execution time > 10%
- [ ] Dashboard page load improved (measure before/after)
- [ ] No new security vulnerabilities introduced
- [ ] All commits follow conventional commit format
- [ ] PR passes CI/CD pipeline

---

## Worktree Commands

```bash
# Create worktree
git worktree add ../tformance-db-audit -b feature/db-perf-security-audit

# List worktrees
git worktree list

# Remove when done (after merge)
git worktree remove ../tformance-db-audit
```

---

## Post-Implementation

1. **Create PR** with summary of all changes
2. **Run full test suite** on CI
3. **Manual QA** of dashboard performance
4. **Merge to main** after approval
5. **Remove worktree** after merge
6. **Move dev-docs to completed**
