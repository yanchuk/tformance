# Analytics Restructure - Context

**Last Updated:** 2025-12-23 (Session 2 - Final)
**Current Phase:** Phase 1 COMPLETE ✅, Ready for Phase 2
**Last Commit:** `908cc28` - "Add Pull Requests data explorer page"
**Branch:** `github-graphql-api`

---

## Implementation Status

### Phase 1: Pull Requests Page - COMPLETE ✅

**What was built:**
1. **Service Layer** - `apps/metrics/services/pr_list_service.py`
   - `get_prs_queryset(team, filters)` - Full filtering with 10 filter options
   - `get_pr_stats(queryset)` - Aggregate statistics (count, avg cycle/review time, additions/deletions, AI count)
   - `get_filter_options(team)` - Dynamic dropdown values
   - PR_SIZE_BUCKETS constant

2. **Views** - `apps/metrics/views/pr_list_views.py`
   - `pr_list()` - Main page with filters, stats, paginated table
   - `pr_list_table()` - HTMX partial for table updates
   - `pr_list_export()` - CSV streaming export
   - Helper functions: `_get_pr_list_context()`, `_get_filters_from_request()`

3. **Templates**
   - `templates/metrics/pull_requests/list.html` - Full page with DaisyUI components
   - `templates/metrics/pull_requests/partials/table.html` - Table with pagination

4. **URLs** - Added to `apps/metrics/urls.py`:
   - `/pull-requests/` → `pr_list`
   - `/pull-requests/table/` → `pr_list_table`
   - `/pull-requests/export/` → `pr_list_export`

5. **Model Enhancement**
   - Added `github_url` property to PullRequest model (`apps/metrics/models/github.py:200-203`)

6. **Template Tags**
   - Created `apps/metrics/templatetags/pr_list_tags.py` - pagination URL helper (from refactoring)

**Test Coverage:**
- 36 service tests in `apps/metrics/tests/test_pr_list_service.py`
- 19 view tests in `apps/metrics/tests/test_pr_list_views.py`
- All 55 tests passing

---

## Key Files Reference

### Created This Session

| File | Purpose | Tests |
|------|---------|-------|
| `apps/metrics/services/pr_list_service.py` | PR filtering, stats, options | 36 |
| `apps/metrics/views/pr_list_views.py` | List, table partial, CSV export | 19 |
| `apps/metrics/tests/test_pr_list_service.py` | Service unit tests | - |
| `apps/metrics/tests/test_pr_list_views.py` | View integration tests | - |
| `templates/metrics/pull_requests/list.html` | Main PR list page | - |
| `templates/metrics/pull_requests/partials/table.html` | HTMX table partial | - |
| `apps/metrics/templatetags/pr_list_tags.py` | Pagination URL helper | - |

### Modified This Session

| File | Change |
|------|--------|
| `apps/metrics/urls.py` | Added 3 URL patterns (lines 51-53) |
| `apps/metrics/views/__init__.py` | Added pr_list exports (line 33) |
| `apps/metrics/models/github.py` | Added `github_url` property (lines 200-203) |

### Existing Files (unchanged, for reference)

| File | Purpose | Lines |
|------|---------|-------|
| `templates/metrics/cto_overview.html` | Main analytics page (monolithic) | 507 |
| `apps/metrics/views/dashboard_views.py` | Dashboard page views | 79 |
| `apps/metrics/views/chart_views.py` | HTMX chart endpoints | 447 |
| `apps/metrics/services/dashboard_service.py` | Data aggregation logic | ~800 |

---

## Key Decisions Made This Session

### D8: for_team Manager Not Used
**Decision:** Use `PullRequest.objects.filter(team=team)` instead of `for_team` manager
**Rationale:** The `for_team` manager requires global team context (`set_current_team()`) which isn't set in views. Direct filtering is simpler.
**Impact:** Added `# noqa: TEAM001` comment to suppress linting

### D9: F() Expressions for Size Filtering
**Decision:** Use Django F() expressions instead of deprecated `.extra()` for size bucket filtering
**Rationale:** `.extra()` is deprecated in Django 4.x
**Code Pattern:**
```python
qs = qs.annotate(total_lines=F("additions") + F("deletions"))
qs = qs.filter(total_lines__gte=min_lines)
```

### D10: StreamingHttpResponse for CSV Export
**Decision:** Use `StreamingHttpResponse` for CSV to handle large datasets efficiently
**Rationale:** Avoids memory issues with 10,000+ PRs
**Impact:** Tests must use `response.streaming_content` not `response.content`

### D11: github_url as Model Property
**Decision:** Add computed property to model instead of constructing URL in templates/views
**Rationale:** DRY - URL construction in one place, used by template and CSV export
**Code:** `return f"https://github.com/{self.github_repo}/pull/{self.github_pr_id}"`

---

## Technical Learnings

### Test Setup Pattern
```python
# For team-scoped views, use this pattern:
self.team = TeamFactory()
self.user = UserFactory()
self.team.members.add(self.user, through_defaults={"role": ROLE_ADMIN})
self.member = TeamMemberFactory(team=self.team)
self.client.force_login(self.user)
```

### URL Reverse Without team_slug
```python
# URLs in team_urlpatterns don't need team_slug kwarg
url = reverse("metrics:pr_list")  # Correct
# NOT: reverse("metrics:pr_list", kwargs={"team_slug": ...})
```

### Factories Available
- `TeamFactory`, `UserFactory` (from `apps.integrations.factories`)
- `TeamMemberFactory`, `PullRequestFactory`, `PRReviewFactory` (from `apps.metrics.factories`)

---

## Models Reference

### PullRequest Fields for Filtering
```
id, github_pr_id, github_repo, title, author_id,
state, pr_created_at, merged_at, first_review_at,
cycle_time_hours, review_time_hours, review_rounds,
commits_after_first_review, total_comments,
additions, deletions, is_revert, is_hotfix,
is_ai_assisted, ai_tools_detected, jira_key
```

### PR Size Buckets (Implemented)
```python
PR_SIZE_BUCKETS = {
    'XS': (0, 10),      # 0-10 lines
    'S': (11, 50),      # 11-50 lines
    'M': (51, 200),     # 51-200 lines
    'L': (201, 500),    # 201-500 lines
    'XL': (501, None),  # 500+ lines
}
```

### Filter GET Params (Implemented)
```
?repo=owner/repo-name
&author=uuid
&reviewer=uuid
&ai=yes|no|all
&ai_tool=claude|copilot|cursor
&size=XS|S|M|L|XL
&state=open|merged|closed
&has_jira=yes|no
&date_from=2024-01-01
&date_to=2024-12-31
&page=1
```

---

## Dependencies (Phase 2+)

### Internal Dependencies
| Dependency | Required For | Status |
|------------|--------------|--------|
| `apps/metrics/services/dashboard_service.py` | All chart data | Exists |
| `apps/teams/decorators.py` | `@login_and_team_required`, `@team_admin_required` | Exists |
| `apps/metrics/view_utils.py` | `get_date_range_from_request()` | Exists |
| Design system CSS | Color coding | Needs additions (Phase 4) |

### New Files to Create (Phase 2+)

| File | Type | Phase |
|------|------|-------|
| `apps/metrics/views/analytics_views.py` | View | Phase 2 |
| `templates/metrics/analytics/base_analytics.html` | Template | Phase 2 |
| `templates/metrics/analytics/overview.html` | Template | Phase 2 |
| `templates/metrics/analytics/ai_adoption.html` | Template | Phase 3 |
| `templates/metrics/analytics/delivery.html` | Template | Phase 4 |
| `templates/metrics/analytics/quality.html` | Template | Phase 4 |
| `templates/metrics/analytics/team.html` | Template | Phase 5 |

---

## Commands to Run on Restart

```bash
# Verify tests pass
.venv/bin/pytest apps/metrics/tests/test_pr_list_service.py apps/metrics/tests/test_pr_list_views.py -v

# Run full metrics test suite
.venv/bin/pytest apps/metrics/tests/ -q

# Start dev server to verify page works
make dev
# Then visit: http://localhost:8000/a/<team-slug>/metrics/pull-requests/
```

---

## Next Steps (Phase 2: Overview Page)

1. Create `apps/metrics/views/analytics_views.py` with `analytics_overview(request)` view
2. Create `templates/metrics/analytics/base_analytics.html` with tab navigation
3. Create `templates/metrics/analytics/overview.html` with key widgets:
   - Key Metrics Cards (reuse existing partial)
   - Insights Panel (reuse existing partial)
   - PR Velocity Trend (weekly bar chart)
   - Quick Links to other analytics pages
4. Add URL patterns for all analytics pages
5. Follow TDD workflow

---

## Related Documentation

- `prd/DASHBOARDS.md` - Original dashboard spec
- `prd/PRD-MVP.md` - ICP questions, pain points
- `prd/DATA-MODEL.md` - Database schema
- `CLAUDE.md` - Coding guidelines
- `assets/styles/app/tailwind/design-system.css` - Design tokens
