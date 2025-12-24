# PR List Size Column & Author Ellipsis - Tasks

**Last Updated:** 2025-12-24

## Phase 1: Add Size Bucket Template Filters [S] - COMPLETE

### 1.1 Write Failing Tests (TDD Red)
- [x] Test `pr_size_bucket` filter returns correct bucket for each range
- [x] Test `pr_size_bucket` handles edge cases (0, 10, 11, 50, 51, etc.)
- [x] Test invalid inputs return empty string

### 1.2 Implement Filters (TDD Green)
- [x] Add `pr_size_bucket(additions, deletions)` filter
- [x] Handle None/negative inputs gracefully

### 1.3 Refactor (TDD Refactor)
- [x] Extract `calculate_pr_size_bucket()` to service layer for reuse
- [x] Template filter delegates to service function

## Phase 2: Update Size Column in Table [S] - COMPLETE

### 2.1 Update Column Header
- [x] Change header text from "Lines" to "Size"
- [x] Keep sorting functionality (sort=lines)
- [x] Center-align header

### 2.2 Update Column Cell
- [x] Replace `+N -M` display with size badge (badge-ghost)
- [x] Add `title` attribute with `+{{ pr.additions }}/-{{ pr.deletions }}`
- [x] Add `cursor-help` class for tooltip indicator

## Phase 3: Fix Author Column Ellipsis [S] - COMPLETE

### 3.1 Add Truncation to Regular Authors
- [x] Add `max-w-[100px]` to author container
- [x] Add flex container with `truncate` on name span
- [x] Add `title` attribute with full display name
- [x] Ensure "Self" badge displays with `flex-shrink-0`

### 3.2 Add Truncation to Bot Authors
- [x] Apply same truncation pattern to bot author display
- [x] Ensure "Bot" badge displays with `flex-shrink-0`

## Verification - COMPLETE

- [x] All 48 template tag tests pass
- [x] All 34 PR list view tests pass (82 total tests)
- [x] Size column shows XS/S/M/L/XL badges
- [x] Hovering on size badge shows exact line counts
- [x] Author names truncate with ellipsis

## Files Modified

1. `apps/metrics/services/pr_list_service.py` - Added `calculate_pr_size_bucket()` function
2. `apps/metrics/templatetags/pr_list_tags.py` - Added `pr_size_bucket` filter
3. `apps/metrics/tests/test_pr_list_tags.py` - Added 22 tests for new filter
4. `templates/metrics/pull_requests/partials/table.html` - Updated Size & Author columns
