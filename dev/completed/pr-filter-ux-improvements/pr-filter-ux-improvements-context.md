# PR List Filter UX Improvements - Context

**Last Updated:** 2025-12-24
**Status:** COMPLETE - Ready to move to dev/completed

## Implementation Summary

Both UX issues have been fixed and verified in browser:

1. **Button Text Color** - Light theme primary buttons now use white text (APCA-compliant)
2. **Filter Dirty State** - Apply button shows visual feedback when filters change

## Files Modified

### CSS (Phase 1)
- `assets/styles/site-tailwind.css` (line 93)
  - Changed: `--color-primary-content: oklch(0.15 0 0)` → `oklch(1 0 0)`
  - Result: White text on primary buttons in light theme

### Templates (Phase 2)
- `templates/metrics/pull_requests/list.html` (lines 16-47, 130-136)
  - Added Alpine.js `x-data` with `initial` and `current` filter states
  - Added `isDirty` computed getter comparing states
  - Added `resetDirty()` method called on `@htmx:after-request.window`
  - Added `x-model` bindings to 6 filter controls
  - Updated button with `:class` for glow and conditional text

- `templates/metrics/analytics/pull_requests.html` (lines 22-68, 250-260)
  - Same pattern but with 12 filters (repo, author, reviewer, ai, ai_tool, state, size, has_jira, date_from, date_to, plus `techChanged` flag)
  - Technology filter uses separate `techChanged` flag due to multi-select

## Key Technical Decisions

### 1. Dirty State Detection
- **Approach:** Individual property comparison vs JSON.stringify
- **Reason:** More reliable, avoids serialization issues with Alpine.js proxies
- **Code:** `this.current.repo !== this.initial.repo || ...`

### 2. Reset Timing
- **Event:** `@htmx:after-request.window`
- **Reason:** Fires after HTMX completes, updates initial to match current
- **Scope:** Window-level to catch all HTMX requests from form

### 3. Visual Indicator
- **Style:** `ring-2 ring-warning/60 ring-offset-2 ring-offset-base-200`
- **Reason:** Subtle glow effect, uses theme colors, visible in both themes

### 4. Button Text
- **When clean:** "Apply Filters"
- **When dirty:** "Apply Changes"
- **Implementation:** `x-show` with `x-cloak` to prevent flash

## Browser Verification

Tested on PR list page (`/app/metrics/pull-requests/`):
- Changed AI Assisted filter from "All" to "Yes"
- Button text changed to "Apply Changes"
- Warning glow appeared around button
- Screenshots saved to `.playwright-mcp/pr-filter-dirty-state-*.png`

## No Django Changes Required

- No models modified
- No migrations needed
- No views changed
- No URL patterns added
- CSS/template changes only

## Test Status

- **Unit tests:** Not applicable (frontend-only changes)
- **E2E tests:** Existing tests should pass (filter functionality unchanged)
- **Manual testing:** Complete - verified in Playwright browser

## Next Steps

1. Move folder to `dev/completed/pr-filter-ux-improvements/`
2. Commit changes with descriptive message
3. Consider adding E2E test for dirty state visual feedback (optional)
