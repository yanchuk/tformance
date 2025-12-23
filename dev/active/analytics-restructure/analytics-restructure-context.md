# Analytics Restructure - Context

**Last Updated:** 2025-12-23 (Session 3)
**Current Phase:** Phase 2 COMPLETE ✅, Ready for Phase 3
**Branch:** `github-graphql-api`

---

## Implementation Status

### Phase 1: Pull Requests Page - COMPLETE ✅

**What was built:**
1. **Service Layer** - `apps/metrics/services/pr_list_service.py`
   - `get_prs_queryset(team, filters)` - Full filtering with 10 filter options
   - `get_pr_stats(queryset)` - Aggregate statistics
   - `get_filter_options(team)` - Dynamic dropdown values
   - PR_SIZE_BUCKETS constant

2. **Views** - `apps/metrics/views/pr_list_views.py`
   - `pr_list()` - Main page with filters, stats, paginated table
   - `pr_list_table()` - HTMX partial for table updates
   - `pr_list_export()` - CSV streaming export

3. **Templates**
   - `templates/metrics/pull_requests/list.html` - Full page
   - `templates/metrics/pull_requests/partials/table.html` - Table with pagination

4. **URLs**: `/pull-requests/`, `/pull-requests/table/`, `/pull-requests/export/`

**Test Coverage:** 55 tests (36 service + 19 view)

### Phase 2: Analytics Overview Page - COMPLETE ✅

**What was built:**
1. **Views** - `apps/metrics/views/analytics_views.py`
   - `analytics_overview()` - Team health dashboard (admin-only)
   - `_get_analytics_context()` - Shared context helper

2. **Templates**
   - `templates/metrics/analytics/base_analytics.html` - Base with tab navigation
   - `templates/metrics/analytics/overview.html` - Health overview page

3. **URLs**: `/analytics/` → `analytics_overview`

4. **Navigation Enhancement**
   - Added quick nav buttons to `cto_overview.html` for discoverability

**Test Coverage:** 14 tests in `apps/metrics/tests/test_analytics_views.py`

**Features:**
- Tab navigation: Overview ↔ Pull Requests
- Date range filter (7d/30d/90d)
- Insights panel with AI insights
- Key metrics cards (HTMX loaded)
- Charts: AI Adoption, Cycle Time, Quality by AI, PR Size
- Quick links: All PRs, AI-Assisted PRs, Full Dashboard

---

## Key Files Reference

### Phase 2 Files Created

| File | Purpose | Tests |
|------|---------|-------|
| `apps/metrics/views/analytics_views.py` | Overview view, context helper | 14 |
| `apps/metrics/tests/test_analytics_views.py` | View tests | - |
| `templates/metrics/analytics/base_analytics.html` | Base template with tabs | - |
| `templates/metrics/analytics/overview.html` | Health overview page | - |

### Phase 2 Files Modified

| File | Change |
|------|--------|
| `apps/metrics/urls.py` | Added `/analytics/` URL pattern |
| `apps/metrics/views/__init__.py` | Added `analytics_overview` export |
| `templates/metrics/cto_overview.html` | Added nav buttons to new pages |

---

## Key Decisions

### D12: Tab Navigation in Base Template
**Decision:** Put tab navigation in `base_analytics.html` rather than individual pages
**Rationale:** DRY - all analytics pages need the same tabs
**Impact:** Each page extends `base_analytics.html` and fills `analytics_content` block

### D13: Reuse Existing HTMX Partials
**Decision:** Reuse existing chart partials (ai_adoption_chart, cycle_time_chart, etc.)
**Rationale:** No need to duplicate chart logic - just call existing endpoints
**Impact:** Overview page uses `hx-get` to load existing partials

### D14: Admin-Only Analytics Overview
**Decision:** Use `@team_admin_required` decorator (same as cto_overview)
**Rationale:** Analytics pages show team-wide data, appropriate for admins
**Impact:** Returns 404 for non-admin team members (consistent with existing behavior)

---

## Navigation Flow

```
Sidebar "Analytics"
    └── dashboard_redirect
        ├── (admin) → cto_overview
        │               ├── [Health Overview] → analytics_overview
        │               └── [Pull Requests] → pr_list
        └── (member) → team_dashboard

New Analytics (via tabs):
    analytics_overview ←→ pr_list
         (Overview)        (Pull Requests)
```

---

## Commands to Run on Restart

```bash
# Verify Phase 2 tests pass
.venv/bin/pytest apps/metrics/tests/test_analytics_views.py -v

# Run full metrics test suite
.venv/bin/pytest apps/metrics/tests/ -q

# Start dev server
make dev
# Visit: http://localhost:8000/app/metrics/analytics/
```

---

## Next Steps (Phase 3: AI Adoption Page)

1. Add `analytics_ai_adoption()` view to `analytics_views.py`
2. Create `templates/metrics/analytics/ai_adoption.html`
3. Add new service function `get_ai_vs_non_ai_comparison(team, start, end)`
4. Add URL pattern `/analytics/ai-adoption/`
5. Update tabs in `base_analytics.html`
6. Follow TDD workflow

---

## Related Documentation

- `prd/DASHBOARDS.md` - Original dashboard spec
- `prd/PRD-MVP.md` - ICP questions, pain points
- `CLAUDE.md` - Coding guidelines
