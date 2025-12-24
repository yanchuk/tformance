# PR Size Chart Clickable Links - Tasks

**Last Updated: 2025-12-24**
**Status: ✅ COMPLETE**

## Phase 1: Update PR Size Chart Template [S] ✅

- [x] Modify `templates/metrics/partials/pr_size_chart.html`
  - [x] Wrap bar row in `<a>` anchor tag
  - [x] Add `href="{% url 'metrics:pr_list' %}?size={{ item.category }}"`
  - [x] Add `target="_blank" rel="noopener"` attributes
  - [x] Add `group` class for coordinated hover effects
  - [x] Add `cursor-pointer` class
  - [x] Add hover styling to category label: `group-hover:text-primary`
  - [x] Add hover styling to bar container: `group-hover:ring-2 ring-primary/50`

## Phase 2: Testing [S] ✅

- [x] Verify on Team Dashboard (`/a/<team>/dashboard/`)
  - [x] Bars are visually clickable (hover cursor)
  - [x] Clicking opens PR List in new tab
  - [x] Correct size filter applied
- [x] Verify on Analytics Overview (`/a/<team>/metrics/analytics/`)
  - [x] Same behavior as Dashboard
- [x] Verify on Analytics Delivery (`/a/<team>/metrics/analytics/delivery/`)
  - [x] Same behavior as Dashboard
- [x] Test all 5 size categories work (XS, S, M, L, XL)
- [x] Verify no layout/styling regressions

## Completion Criteria ✅

- [x] All 3 pages have clickable PR size bars
- [x] Clicking opens correct filtered view in new tab
- [x] Hover effects provide clear visual feedback
- [x] No E2E test failures
