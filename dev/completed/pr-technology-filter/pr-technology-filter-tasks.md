# PR Technology Filter - Tasks

**Last Updated: 2025-12-24**
**Status: COMPLETED**

## Phase 1: Data Annotation (S effort) ✅

### 1.1 Add Technology Category Annotation
- [x] Add `tech_categories` annotation to `get_prs_queryset()` in `pr_list_service.py`
- [x] Use `ArrayAgg` to get unique file categories per PR
- [x] Handle PRs with no files (return empty list via `default=Value([])`)

### 1.2 Add Filter Option
- [x] Add `tech_categories` to `get_filter_options()` return value
- [x] Include all available categories from `PRFile.CATEGORY_CHOICES`

## Phase 2: Filter Implementation (S effort) ✅

### 2.1 Service Layer Filter
- [x] Add `tech` filter parameter to `get_prs_queryset()`
- [x] Support multi-select (list of categories)
- [x] Filter PRs that have files in ANY of the selected categories
- [x] Use `.distinct()` to avoid duplicates

### 2.2 View Integration
- [x] Extract `tech` parameter from request via `getlist("tech")`
- [x] Pass `tech` list to filters dict

### 2.3 Unit Tests
- [x] Test filter by single category
- [x] Test filter by multiple categories
- [x] Test empty filter returns all PRs
- [x] Test PRs with no files are handled correctly

## Phase 3: Template Display (S effort) ✅

### 3.1 Template Tags
- [x] Add `tech_abbrev` filter to convert category to 2-letter code
- [x] Add `tech_badge_class` filter for DaisyUI badge color
- [x] Add `tech_display_name` filter for full category name

### 3.2 Table Column
- [x] Add "Tech" column header to `table.html` (after AI, before Merged)
- [x] Display badges for each category
- [x] Limit display to top 3 badges, show "+N" for more

### 3.3 Filter UI
- [x] Add Technology filter dropdown to `pull_requests.html`
- [x] Use multi-select checkboxes via Alpine.js dropdown
- [x] Wire up HTMX for filter submission

## Phase 4: Testing (S effort) ✅

### 4.1 Unit Tests
- [x] Test `tech_abbrev` filter (10 tests)
- [x] Test `tech_badge_class` filter (7 tests)
- [x] Test `tech_display_name` filter (9 tests)
- [x] Test `get_prs_queryset` with tech filter (7 tests)
- [x] Test `get_filter_options` includes tech categories

### 4.2 E2E Tests (optional)
- [ ] Test Tech column displays badges
- [ ] Test Tech filter updates table

## Acceptance Criteria

1. **Column Display**
   - [ ] Tech column shows compact badges (FE, BE, JS, etc.)
   - [ ] Badges have distinct colors per category
   - [ ] Tooltip shows full category name on hover
   - [ ] PRs with no files show "-"

2. **Filter**
   - [ ] Filter dropdown shows all 7 categories
   - [ ] Selecting "Backend" shows only PRs with backend files
   - [ ] Multi-select works (selecting BE+FE shows both)
   - [ ] Clear filter works

3. **Performance**
   - [ ] No N+1 queries (annotation handles it)
   - [ ] Page load time not significantly affected

## Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/services/pr_list_service.py` | Add annotation and filter |
| `apps/metrics/views/pr_list_views.py` | Extract tech parameter |
| `apps/metrics/templatetags/pr_list_tags.py` | Add tech display filters |
| `templates/metrics/pull_requests/list.html` | Add Tech filter dropdown |
| `templates/metrics/pull_requests/partials/table.html` | Add Tech column |
| `apps/metrics/tests/test_pr_list_service.py` | Add filter tests |
