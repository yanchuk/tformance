# Dashboard Consolidation - Task Checklist

**Last Updated:** 2025-01-25

## Progress Tracking

| Phase | Status | Progress |
|-------|--------|----------|
| Phase A: Update Tests | ✅ Complete | 4/4 |
| Phase B: Code Changes | ✅ Complete | 5/5 |
| Phase C: Documentation | ✅ Complete | 7/7 |
| Phase D: Verification | 🟡 In Progress | 3/5 |

---

## Phase A: Update Tests (FIRST - Prevents CI Breakage)

### A.1 E2E Tests
- [x] **Task A.1.1** Update `tests/e2e/insights.spec.ts` (~16 refs)
  - Find: `/app/metrics/overview/` → Replace: `/app/metrics/analytics/`
  - ✅ Completed: All references updated
  - Effort: M

- [x] **Task A.1.2** Update remaining E2E test files
  - Files: `copilot.spec.ts`, `feedback.spec.ts`, `llm-feedback.spec.ts`, `analytics.spec.ts`, `dashboard.spec.ts`, `error-states.spec.ts`, `interactive.spec.ts`, `fixtures/test-fixtures.ts`
  - ✅ Completed: All 9 files updated
  - Effort: M

### A.2 Python Tests
- [x] **Task A.2.1** Update `apps/metrics/tests/test_dashboard_views.py`
  - ✅ Renamed `TestCTOOverview` → `TestCTOOverviewRedirect`
  - ✅ Changed tests to expect 302 redirect instead of 200
  - ✅ Updated `TestDashboardAccessControl` to use analytics_overview
  - Effort: S

- [x] **Task A.2.2** Update `apps/metrics/tests/test_copilot_graceful_degradation.py`
  - ✅ Updated all test methods to use analytics_ai_adoption
  - ✅ Changed content assertions to match ai_adoption.html template
  - Effort: S

---

## Phase B: Code Changes

### B.1 View Changes
- [x] **Task B.1.1** Convert `cto_overview()` to redirect
  - File: `apps/metrics/views/dashboard_views.py`
  - ✅ Replaced function body with redirect to analytics_overview
  - ✅ Kept @team_admin_required decorator
  - Effort: S

### B.2 Template Changes - Navigation Links
- [x] **Task B.2.1** Remove "Full Dashboard" link from `overview.html`
  - File: `templates/metrics/analytics/overview.html`
  - ✅ Removed redundant link
  - Effort: S

- [x] **Task B.2.2** Remove "Full Dashboard" links from other analytics templates
  - Files: `quality.html`, `team.html`
  - ✅ Removed links from both files
  - Effort: S

### B.3 Template Changes - DX Feature Integration
- [x] **Task B.3.1** Add Team Health Indicators to `overview.html`
  - File: `templates/metrics/analytics/overview.html`
  - ✅ Added HTMX card loading `metrics:cards_team_health`
  - Effort: S

- [x] **Task B.3.2** Add Copilot Engagement to `ai_adoption.html`
  - File: `templates/metrics/analytics/ai_adoption.html`
  - ✅ Added inside `{% if copilot_enabled %}` block
  - Effort: S

### B.4 Cleanup
- [x] **Task B.4.1** Delete `cto_overview.html` template
  - File: `templates/metrics/cto_overview.html`
  - ✅ Deleted (was 624 lines)
  - Effort: S

---

## Phase C: Documentation Cleanup

### C.1 Claude Skills (HIGH PRIORITY)
- [x] **Task C.1.1** Fix team slug URLs in `SKILL.md`
  - File: `.claude/skills/django-dev-guidelines/SKILL.md`
  - ✅ Updated `/a/<team_slug>/` → `/app/`
  - Effort: S

- [x] **Task C.1.2** Fix team slug URLs in `drf-guide.md`
  - File: `.claude/skills/django-dev-guidelines/resources/drf-guide.md`
  - ✅ Updated API URL pattern
  - Effort: S

- [x] **Task C.1.3** Fix team slug URLs in `documentation-architect.md`
  - File: `.claude/agents/documentation-architect.md`
  - ✅ Updated URL pattern examples
  - Effort: S

### C.2 Dev Guides
- [x] **Task C.2.1** Fix team slug URLs in `CODE-GUIDELINES.md`
  - File: `dev/guides/CODE-GUIDELINES.md`
  - ✅ Updated URL pattern and team context description
  - Effort: S

### C.3 PRD Documents
- [x] **Task C.3.1** Update `DASHBOARDS.md`
  - File: `prd/DASHBOARDS.md`
  - ✅ Renamed CTO Overview → Analytics Overview
  - ✅ Added redirect note
  - ✅ Updated file organization
  - ✅ Updated view references
  - Effort: M

- [x] **Task C.3.2** Fix team slug URLs in `DATA-MODEL.md`
  - File: `prd/DATA-MODEL.md`
  - ✅ Updated team context description
  - Effort: S

- [x] **Task C.3.3** Fix team slug URLs in `PERSONAL-NOTES.md`
  - File: `prd/PERSONAL-NOTES.md`
  - ✅ Updated URL structure section
  - Effort: S

---

## Phase D: Verification

### D.1 Automated Tests
- [x] **Task D.1.1** Run Python test suite
  - Command: `make test`
  - ✅ 2584 tests passed (excluding TDD RED tests)
  - Effort: S

- [ ] **Task D.1.2** Run E2E test suite
  - Command: `make e2e`
  - Acceptance: All tests pass
  - Effort: M

- [ ] **Task D.1.3** Run linting
  - Command: `make ruff`
  - Acceptance: No errors
  - Effort: S

### D.2 Manual Verification
- [ ] **Task D.2.1** Verify redirect works
  - URL: `http://localhost:8000/app/metrics/overview/?team=47`
  - Expected: 302 redirect to `/app/metrics/analytics/`
  - Effort: S

- [ ] **Task D.2.2** Verify DX features visible
  - Check: Team Health card on Overview tab
  - Check: Copilot Engagement card on AI Adoption tab
  - Effort: S

---

## Quick Reference

### Search Commands
```bash
# Find remaining overview references in tests
grep -r "/app/metrics/overview" tests/e2e/

# Find cto_overview references in Python
grep -r "cto_overview" apps/metrics/tests/

# Find team slug URLs in docs
grep -r "/a/<team_slug>" --include="*.md" .
grep -r "/a/supabase" --include="*.md" .
```

### Test Commands
```bash
# Run specific test file
make test ARGS='apps.metrics.tests.test_dashboard_views'

# Run E2E with specific file
npx playwright test tests/e2e/insights.spec.ts

# Run all tests
make test && make e2e
```

---

## Summary of Changes Made

### Files Modified (9)
1. `apps/metrics/views/dashboard_views.py` - cto_overview now redirects
2. `apps/metrics/tests/test_dashboard_views.py` - Updated test class
3. `apps/metrics/tests/test_insight_dashboard.py` - Updated test class
4. `apps/metrics/tests/test_copilot_graceful_degradation.py` - Fixed assertions
5. `templates/metrics/analytics/overview.html` - Added Team Health, removed Full Dashboard link
6. `templates/metrics/analytics/quality.html` - Removed Full Dashboard link
7. `templates/metrics/analytics/team.html` - Removed Full Dashboard link
8. `templates/metrics/analytics/ai_adoption.html` - Added Copilot Engagement card

### Files Deleted (1)
1. `templates/metrics/cto_overview.html` (624 lines)

### E2E Tests Updated (9 files)
- insights.spec.ts, copilot.spec.ts, feedback.spec.ts, llm-feedback.spec.ts
- analytics.spec.ts, dashboard.spec.ts, error-states.spec.ts, interactive.spec.ts
- fixtures/test-fixtures.ts

---

## Notes

### TDD Approach
Since we're removing/modifying existing functionality:
1. ✅ Update tests first to expect new behavior
2. ✅ Run tests (they should fail)
3. ✅ Make code changes
4. ✅ Run tests (they should pass)

### Rollback Plan
If issues discovered:
1. Revert `cto_overview()` redirect
2. Re-add navigation links
3. All original functionality preserved

### Post-Implementation
- Update DX features task doc to reference analytics URLs
- Archive this task after PR merge
