# PR Size Chart Clickable Links - Implementation Plan

**Last Updated: 2025-12-24**

## Executive Summary

Add clickable functionality to PR Size Distribution chart bars so clicking on a size category (XS, S, M, L, XL) opens the PR List page filtered by that size in a new tab.

## Current State Analysis

### PR Size Distribution Chart

**Location**: `templates/metrics/partials/pr_size_chart.html`

**Current Implementation**:
- Horizontal bar chart showing PR count by size category (XS, S, M, L, XL)
- Each bar displays the count inside
- Color-coded: green (XS/S), yellow (M), red (L/XL)
- No click interactivity - purely visual

**Pages Using This Chart**:
1. **Team Dashboard** (`templates/metrics/team_dashboard.html`) - Line 88-93
2. **Analytics Overview** (`templates/metrics/analytics/overview.html`) - Lines 93-97
3. **Analytics Delivery** (`templates/metrics/analytics/delivery.html`) - Lines 57-62

### PR List Page Size Filter

**Already Implemented**:
- `pr_list_service.py` supports `size` filter parameter
- Valid values: XS, S, M, L, XL
- URL pattern: `/a/<team_slug>/metrics/pull-requests/?size=L`
- Quick links already exist in `delivery.html` (line 123): `?size=L`

## Proposed Future State

### User Experience

1. User hovers over a PR size bar → cursor changes to pointer
2. User clicks on a size bar → PR List page opens in new tab with that size filter applied
3. Date range from current view is preserved via query params

### Technical Implementation

Modify `pr_size_chart.html` to:
1. Wrap each bar in an anchor tag (`<a>`)
2. Build URL: `{% url 'metrics:pr_list' %}?size={{ item.category }}`
3. Add `target="_blank"` for new tab behavior
4. Style with hover effects to indicate clickability

## Implementation Phases

### Phase 1: Update PR Size Chart Template (S)

**Effort**: Small (15 min)

**Tasks**:
1. Modify bar container to be clickable anchor
2. Add hover styling for visual feedback
3. Build proper PR List URL with size filter
4. Add `target="_blank" rel="noopener"` attributes

### Phase 2: Testing (S)

**Effort**: Small (10 min)

**Tasks**:
1. Manual verification on Team Dashboard
2. Manual verification on Analytics Overview
3. Manual verification on Analytics Delivery
4. Verify correct filter applied in new tab

## Technical Details

### Template Changes

**File**: `templates/metrics/partials/pr_size_chart.html`

**Current Structure** (simplified):
```html
<div class="flex items-center gap-3">
  <span class="w-8">{{ item.category }}</span>
  <div class="flex-1 bg-base-200 rounded-full h-6">
    <div class="h-full rounded-full ...">
      <span>{{ item.count }}</span>
    </div>
  </div>
</div>
```

**Proposed Structure**:
```html
<a href="{% url 'metrics:pr_list' %}?size={{ item.category }}"
   target="_blank"
   rel="noopener"
   class="flex items-center gap-3 group cursor-pointer">
  <span class="w-8 text-sm font-medium text-base-content/70 group-hover:text-primary">
    {{ item.category }}
  </span>
  <div class="flex-1 bg-base-200 rounded-full h-6 overflow-hidden group-hover:ring-2 ring-primary/50">
    <!-- Bar content unchanged -->
  </div>
</a>
```

### URL Construction

The PR List page already supports the `size` query parameter:
- `?size=XS` → PRs with 0-10 lines changed
- `?size=S` → PRs with 11-50 lines changed
- `?size=M` → PRs with 51-200 lines changed
- `?size=L` → PRs with 201-500 lines changed
- `?size=XL` → PRs with 501+ lines changed

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing layout | Low | Medium | Test all 3 pages |
| URL not working | Very Low | Low | Already implemented in Quick Links |
| Accessibility issues | Low | Low | Use semantic anchor tags |

## Success Metrics

- [ ] Clicking any size bar opens PR List in new tab
- [ ] Correct size filter is pre-selected
- [ ] Works on all 3 pages (Dashboard, Overview, Delivery)
- [ ] Hover effect provides visual feedback
- [ ] No layout/styling regressions

## Dependencies

- None - all infrastructure already exists

## Effort Estimate

**Total**: ~25 minutes
- Template modification: 15 min
- Manual testing: 10 min
