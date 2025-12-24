# Analytics UI Fixes - Plan

**Last Updated:** 2025-12-24
**Status:** PLANNING
**Branch:** TBD

---

## Executive Summary

Fix three critical UI issues in the recently implemented Analytics pages:
1. Double rendering on Pull Requests page (HTMX target mismatch)
2. Missing tab navigation on Pull Requests page (wrong base template)
3. Low contrast on inactive tabs (accessibility issue)

**Estimated Effort:** M (Half day)
**Priority:** High - Affects user experience and accessibility

---

## Current State Analysis

### Issue 1: Double Rendering on PR List Page

**Symptoms:**
- Filter panel and stats appear twice on the page
- Visible in user-provided screenshot

**Root Cause:**
```html
<!-- list.html line 17-20 -->
<form hx-get="{% url 'metrics:pr_list' %}"
      hx-target="#pr-table-container"  <!-- Targets small container -->
      hx-swap="innerHTML"
      hx-push-url="true">
```

```python
# pr_list_views.py line 91-96
if request.headers.get("HX-Request"):
    return TemplateResponse(
        request,
        "metrics/pull_requests/list.html#page-content",  # Returns FULL partial
        context,
    )
```

**Problem:** Form targets `#pr-table-container` (just table), but view returns `#page-content` (filters + stats + table). The full content gets injected into the small container.

### Issue 2: Missing Tabs on PR List Page

**Symptoms:**
- No tab navigation (Overview, AI Adoption, etc.) on PR list page
- Clicking "Pull Requests" tab from Analytics breaks navigation context

**Root Cause:**
```html
<!-- list.html line 1 -->
{% extends "web/app/app_base.html" %}  <!-- Wrong base! -->
```

Should extend `base_analytics.html` to get tab navigation.

### Issue 3: Tab Contrast (Accessibility)

**Symptoms:**
- Inactive tabs have low contrast against background
- May fail WCAG AA 4.5:1 contrast requirement

**Root Cause:**
DaisyUI `tabs-boxed` default styling uses light text for inactive tabs on `bg-base-200`.

---

## Proposed Solution

### Phase 1: Fix Double Rendering (Priority: Critical)

**Option A (Recommended):** Change form target to match partial
- Change `hx-target="#pr-table-container"` → `hx-target="#page-content"`
- Change `hx-swap="innerHTML"` → `hx-swap="outerHTML"`
- Keeps URL push working correctly

**Option B:** Create dedicated filter endpoint
- Form uses `pr_list_table` URL for table-only updates
- Separate endpoint for full page refresh
- More complex, breaks `hx-push-url`

### Phase 2: Add Tabs to PR List Page (Priority: High)

**Approach:** Create new PR list template extending analytics base
1. Create `templates/metrics/analytics/pull_requests.html`
2. Extend `base_analytics.html`
3. Include PR list content in `{% block analytics_content %}`
4. Update view to use new template
5. Keep old `list.html` as standalone fallback (or remove)

**URL Structure:**
- `/app/metrics/analytics/` - Overview (has tabs)
- `/app/metrics/analytics/pull-requests/` - PR list with tabs (NEW)
- `/app/metrics/pull-requests/` - Standalone PR list (keep or redirect)

### Phase 3: Fix Tab Contrast (Priority: Medium)

**Approach:** Add custom CSS for inactive tabs
```css
/* In design-system.css */
.tabs-boxed .tab:not(.tab-active) {
  color: var(--bc);  /* base-content */
  opacity: 0.8;
}
```

Ensure 4.5:1 contrast ratio minimum.

---

## Implementation Phases

### Phase 1: Fix Double Rendering
**Effort:** S (1-2 hours)

1. Update `list.html` form HTMX attributes
2. Update partial wrapper to have correct ID
3. Test filter/pagination interactions
4. Verify no duplicate content

### Phase 2: Add Tabs to PR List
**Effort:** M (2-4 hours)

1. Create new `analytics/pull_requests.html` template
2. Update `analytics_views.py` or add new view
3. Update URL patterns
4. Update tab links in `base_analytics.html`
5. Add E2E tests for navigation
6. Decide: redirect old URL or keep both

### Phase 3: Fix Tab Contrast
**Effort:** S (1 hour)

1. Measure current contrast ratios
2. Add CSS override in `design-system.css`
3. Run Playwright accessibility tests
4. Verify WCAG AA compliance

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing E2E tests | Medium | Run full test suite after each change |
| URL changes break bookmarks | Low | Implement redirects if needed |
| Accessibility fix changes theme | Low | Only modify opacity, not colors |
| HTMX swap issues | Medium | Test thoroughly in browser |

---

## Success Metrics

- [ ] No double rendering on PR list page
- [ ] Tabs visible on PR list page
- [ ] Tab navigation works between all analytics pages
- [ ] Inactive tab contrast >= 4.5:1
- [ ] All existing E2E tests pass
- [ ] Playwright accessibility tests pass

---

## Dependencies

- `templates/metrics/analytics/base_analytics.html`
- `templates/metrics/pull_requests/list.html`
- `apps/metrics/views/pr_list_views.py`
- `apps/metrics/views/analytics_views.py`
- `assets/styles/app/tailwind/design-system.css`
- `tests/e2e/analytics.spec.ts`
