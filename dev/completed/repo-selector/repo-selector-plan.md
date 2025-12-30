# Repository Selector - Implementation Plan

**Last Updated: 2024-12-30**

## Executive Summary

Add a repository selector to Analytics pages allowing users to filter all metrics by repository. Mirrors the existing date range selector pattern for consistency.

**Implementation Approach:** Strict TDD (Red-Green-Refactor) for all Python code.

### Key Decisions
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Selection type | Single-select + "All" | Simpler UX, clearer data interpretation |
| Team member display | Only show contributors | No confusing zeros for inactive members |
| State persistence | Via Alpine.js store | Consistent with existing date range pattern |
| URL structure | `?repo=owner/repo` (omit for all) | Clean URLs, backward compatible |

---

## Current State Analysis

### Existing Architecture
- **Date range selector**: Uses `$store.dateRange` Alpine store + `date-range-picker.js` component
- **Analytics views**: `_get_analytics_context()` builds common context for all tabs
- **Chart views**: ~30 endpoints fetching data via `dashboard_service` functions
- **Service layer**: All functions take `(team, start_date, end_date)` - no repo filter

### Repository Data Model
```python
# apps/metrics/models/github.py
class PullRequest(BaseTeamModel):
    github_repo = models.CharField(max_length=255)  # "owner/repo" format
```

### Existing Filter Infrastructure
```python
# apps/metrics/services/pr_list_service.py:321
def get_filter_options(team: Team) -> dict:
    repos = list(prs.values_list("github_repo", flat=True).distinct())
    # Already returns repos list - reuse this
```

---

## Proposed Future State

### User Flow
```
User lands on Analytics
       ↓
Sees filters: [Time Range: 30d] [Repository: All Repositories ▼]
       ↓
Clicks Repository dropdown
       ↓
Selects "acme/backend"
       ↓
URL updates: ?days=30&repo=acme/backend
       ↓
All charts reload with filtered data
       ↓
Clicks "AI Adoption" tab → selection persists
       ↓
Clicks "View PRs" → PR page opens with ?repo=acme/backend
```

### Architecture Changes

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Alpine.js Store          │  Components                              │
│  - $store.repoFilter      │  - repo-selector.js                     │
│    - selectedRepo         │  - repo_selector.html                   │
│    - repos[]              │                                          │
│    - setRepo()            │                                          │
│    - syncFromUrl()        │                                          │
├─────────────────────────────────────────────────────────────────────┤
│                            VIEWS                                     │
├─────────────────────────────────────────────────────────────────────┤
│  analytics_views.py       │  chart_views.py                         │
│  - _get_analytics_context │  - _get_repo_filter(request)            │
│    + selected_repo        │  - All chart views pass repo param       │
│    + repos[]              │                                          │
├─────────────────────────────────────────────────────────────────────┤
│                         SERVICE LAYER                                │
├─────────────────────────────────────────────────────────────────────┤
│  dashboard_service.py                                                │
│  - _apply_repo_filter(qs, repo) helper                              │
│  - All 30+ functions: add repo: str | None = None param             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases (TDD)

### Phase 1: Service Layer Foundation [Effort: L]
**Goal:** Add repo filtering to all dashboard_service functions using strict TDD.

**TDD Cycle per function:**
1. 🔴 RED: Write test asserting filtered results when `repo` param passed
2. 🟢 GREEN: Add `repo` param, apply filter
3. 🔵 REFACTOR: Extract common filter logic to helper

**Batch Strategy:** Group similar functions to minimize context switching:
- Batch 1: Core metrics (key_metrics, sparklines, cycle_time, review_time)
- Batch 2: AI functions (ai_adoption, ai_quality, ai_detected, ai_tools)
- Batch 3: Team functions (team_breakdown, leaderboard, reviewer_workload)
- Batch 4: Trend functions (all monthly/weekly trend functions)
- Batch 5: Remaining (copilot, survey, deployment, cicd)

### Phase 2: View Layer Updates [Effort: M]
**Goal:** Pass repo param from requests to service layer.

**TDD Cycle:**
1. 🔴 RED: Test that view returns filtered data when `?repo=x` in request
2. 🟢 GREEN: Add `_get_repo_filter()` helper, pass to service
3. 🔵 REFACTOR: Ensure consistent pattern across all views

### Phase 3: Alpine.js Store & Component [Effort: S]
**Goal:** Create frontend state management and UI component.

**No TDD (JavaScript)** - Manual testing + E2E coverage

### Phase 4: Template Integration [Effort: S]
**Goal:** Wire up component to analytics pages.

### Phase 5: Crosslinks & Navigation [Effort: S]
**Goal:** Update all "View PRs" links to include repo filter.

### Phase 6: E2E Testing [Effort: M]
**Goal:** Comprehensive browser testing of full flow.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Service function signature changes break callers | Medium | High | Update all callers in same PR |
| Performance degradation with repo filter | Low | Medium | Repo filter uses indexed column |
| Alpine store conflicts with date range | Low | Medium | Test store isolation |
| HTMX navigation loses repo param | Medium | Medium | Thorough E2E testing |
| Parallel pr-sidebar-move conflicts | Medium | Low | Coordinate crosslink updates |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | 100% of repo filter logic | pytest --cov |
| Performance | <500ms chart reload | Browser DevTools |
| UX | Filter in <3 clicks | Manual testing |
| Reliability | 0 JS console errors | E2E tests |

---

## Dependencies

### Internal
- `apps/metrics/services/pr_list_service.py:get_filter_options()` - Reuse for repo list
- `assets/javascript/alpine.js` - Existing store pattern to follow
- `templates/metrics/partials/date_range_picker.html` - UI pattern to follow

### External
- None

### Parallel Work
- `pr-sidebar-move` task - May affect crosslink locations; coordinate on merge

---

## Resources Required

- **Developer time:** ~3-4 days estimated
- **Review time:** ~0.5 days
- **QA time:** ~0.5 days (E2E focus)

---

## Rollback Plan

If issues discovered post-deployment:
1. Repo selector is purely additive - can be hidden via template change
2. Service functions default `repo=None` - no change to existing behavior
3. URL param ignored if not handled - backward compatible
