# Visual Improvement Merge & Completion Plan

**Last Updated:** 2025-12-20

## Executive Summary

This plan covers committing, merging, and validating all visual improvement branches, then completing the remaining stages (7, 10, 11) of the Sunset Dashboard design implementation.

**Current State:**
- 4 worktrees with uncommitted/unmerged changes
- 3 feature branches with visual improvements
- Stages 1-6, 8-9 complete across branches

**Target State:**
- All branches merged to main in correct order
- Full e2e test suite passing
- Visual improvement complete (Stages 1-11)

---

## Current State Analysis

### Worktree Status

| Worktree | Branch | Status | Uncommitted Changes |
|----------|--------|--------|---------------------|
| `/tformance` | main | Clean | 1 untracked file |
| `/tformance-landing` | visual-landing | Clean | Already committed |
| `/tformance-dashboard` | visual-dashboard | Dirty | 16 modified files + docs |
| `/tformance-chrome` | visual-chrome | Dirty | 4 modified files + 2 new |

### Branch Dependencies

```
main (Stages 1-2: 45b6324)
  └── visual-landing (Stage 3-4: 906a2fd) - 1 commit ahead
  └── visual-dashboard (Stage 5, 9) - uncommitted
  └── visual-chrome (Stage 6, 8) - uncommitted
```

### Required Merge Order

1. **visual-landing** → main (no conflicts, already committed)
2. **visual-dashboard** → main (after landing, no conflicts)
3. **visual-chrome** → main (after dashboard, no conflicts)

---

## Implementation Phases

### Phase 1: Commit Pending Changes

#### 1.1 Commit visual-chrome (this worktree)
- Stage all modified and new files
- Commit with descriptive message
- Verify build passes

#### 1.2 Commit visual-dashboard
- Navigate to dashboard worktree
- Stage all modified files and docs
- Commit with descriptive message
- Verify build passes

### Phase 2: Merge to Main (Sequential)

#### 2.1 Merge visual-landing → main
- Already committed (906a2fd)
- Fast-forward merge possible
- Run e2e-smoke after merge

#### 2.2 Merge visual-dashboard → main
- Merge after landing
- Resolve any conflicts (unlikely)
- Run e2e-dashboard after merge

#### 2.3 Merge visual-chrome → main
- Merge after dashboard
- Resolve any conflicts (unlikely)
- Run full e2e suite after merge

### Phase 3: Stage 7 - Buttons & Forms (Quick Verification)

Buttons/forms were already updated in Stage 2 design-system.css. This stage is verification only.

#### 3.1 Verify Button Classes
- Check `.app-btn-primary` uses `bg-accent-primary`
- Check `.app-btn-secondary` uses warm hover states
- Check focus rings use `ring-accent-primary`

#### 3.2 Verify Form Inputs
- Check `.app-input` focus uses `border-accent-primary`
- Check form error states use `text-accent-error`
- Test auth forms visually

### Phase 4: Stage 10 - Accessibility Audit

#### 4.1 Automated Checks
- Run Lighthouse accessibility audit
- Check all color contrast ratios
- Verify focus indicators visible

#### 4.2 Manual Verification
- Test keyboard navigation
- Check reduced motion preferences
- Verify screen reader compatibility

### Phase 5: Stage 11 - Final Integration Test

#### 5.1 Full Test Suite
- Run `make test` (Django unit tests)
- Run `make e2e` (full Playwright suite)
- Visual review of all pages

#### 5.2 Documentation Cleanup
- Move completed dev docs to `dev/completed/`
- Update CLAUDE.md if needed
- Final commit on main

---

## Detailed Task Breakdown

### Phase 1 Tasks

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 1.1 | Commit visual-chrome changes | S | Clean git status, build passes |
| 1.2 | Commit visual-dashboard changes | S | Clean git status, build passes |

### Phase 2 Tasks

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 2.1 | Merge visual-landing → main | S | e2e-smoke passes |
| 2.2 | Merge visual-dashboard → main | S | e2e-dashboard passes |
| 2.3 | Merge visual-chrome → main | S | Full e2e passes |
| 2.4 | Clean up worktrees | S | Only main worktree remains |

### Phase 3 Tasks

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 3.1 | Verify button styling | S | Visual inspection passes |
| 3.2 | Verify form styling | S | Auth forms use warm colors |
| 3.3 | Run e2e-auth | S | All tests pass |

### Phase 4 Tasks

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 4.1 | Run Lighthouse audit | M | Accessibility score ≥ 90 |
| 4.2 | Verify contrast ratios | S | All WCAG AA compliant |
| 4.3 | Test keyboard navigation | S | All interactive elements focusable |

### Phase 5 Tasks

| # | Task | Effort | Acceptance Criteria |
|---|------|--------|---------------------|
| 5.1 | Run full test suite | S | All tests pass |
| 5.2 | Visual review | M | All pages use warm colors |
| 5.3 | Move docs to completed | S | dev/active cleaned up |
| 5.4 | Final commit | S | Main branch updated |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Merge conflicts | Low | Medium | Branches touch different files |
| Test failures after merge | Low | Medium | Run tests after each merge |
| Accessibility issues | Low | High | Colors pre-verified for WCAG AA |
| Worktree confusion | Medium | Low | Clear sequential process |

---

## Success Metrics

1. **All branches merged**: visual-landing, visual-dashboard, visual-chrome → main
2. **All tests pass**: `make test` and `make e2e` succeed
3. **Accessibility**: Lighthouse score ≥ 90
4. **Visual consistency**: All UI uses warm Sunset Dashboard palette
5. **Documentation complete**: All dev docs in proper location

---

## Files Summary

### Already Committed (visual-landing)
- `assets/styles/app/tailwind/landing-page.css`
- `templates/web/components/hero_terminal.html`
- `templates/web/components/features_grid.html`

### To Commit (visual-dashboard)
- `templates/metrics/cto_overview.html`
- `templates/metrics/partials/*.html` (15 files)
- `templates/web/components/empty_state.html`
- `dev/active/visual-stages-5-9/` (docs)

### To Commit (visual-chrome)
- `assets/styles/app/tailwind/design-system.css`
- `assets/javascript/dashboard/chart-theme.js` (new)
- `assets/javascript/dashboard/dashboard-charts.js`
- `assets/javascript/app.js`
- `templates/web/components/top_nav.html`
- `dev/active/visual-stages-6-8/` (docs)

---

## Commands Reference

```bash
# Commit in worktree
git add -A && git commit -m "message"

# Merge branch
git checkout main && git merge branch-name

# Run tests
npm run build
make e2e-smoke
make e2e-dashboard
make e2e

# Clean up worktree
git worktree remove /path/to/worktree
git branch -d branch-name
```
