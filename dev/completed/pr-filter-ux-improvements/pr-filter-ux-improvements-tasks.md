# PR List Filter UX Improvements - Tasks

**Last Updated:** 2025-12-24
**Status:** ALL PHASES COMPLETE

## Phase 1: Button Color Fix (Effort: S) ✅ COMPLETE

### 1.1 Update Light Theme Primary Content Color
- [x] Open `assets/styles/site-tailwind.css`
- [x] Find `tformance-light` theme definition (line 81-119)
- [x] Change `--color-primary-content: oklch(0.15 0 0)` to `oklch(1 0 0)` (white)
- [x] Save and verify dev server reloads styles

### 1.2 Verify Button Appearance
- [x] Navigate to PR list page in browser
- [x] Toggle to light theme (system/manual)
- [x] Check "Apply Filters" button is now white text on orange
- [x] Check "Export CSV" outline button still looks correct

### 1.3 Contrast Verification
- [x] White (#FFFFFF) on orange (#F97316) meets APCA standards
- [x] Note: APCA research shows this is perceptually superior

### 1.4 Visual Check - Both Themes
- [x] Dark theme: Primary buttons have white text (unchanged)
- [x] Light theme: Primary buttons now have white text (fixed)
- [x] Screenshot saved: `.playwright-mcp/pr-filter-dirty-state-dark.png`

---

## Phase 2: Filter Dirty State Indicator (Effort: M) ✅ COMPLETE

### 2.1 Add Alpine.js State to Form
- [x] Open `templates/metrics/pull_requests/list.html`
- [x] Add `x-data` to filter panel div with initial/current states
- [x] Track: `repo`, `author`, `ai`, `state`, `date_from`, `date_to`
- [x] Add `isDirty` getter comparing all properties

### 2.2 Bind Form Controls to Alpine State
- [x] Add `x-model="current.repo"` to Repository select
- [x] Add `x-model="current.author"` to Author select
- [x] Add `x-model="current.ai"` to AI Assisted select
- [x] Add `x-model="current.state"` to State select
- [x] Add `x-model="current.date_from"` to Date From input
- [x] Add `x-model="current.date_to"` to Date To input

### 2.3 Style Apply Button Based on Dirty State
- [x] Added `:class="{ 'ring-2 ring-warning/60 ring-offset-2 ring-offset-base-200': isDirty }"`
- [x] Added `x-show="!isDirty"` for "Apply Filters" text
- [x] Added `x-show="isDirty" x-cloak` for "Apply Changes" text

### 2.4 Reset Dirty State After HTMX Submit
- [x] Added `@htmx:after-request.window="resetDirty()"` to filter panel
- [x] `resetDirty()` sets `initial = { ...current }`

### 2.5 Handle Clear Button
- [x] Clear button is `<a>` tag - navigates away and resets page
- [x] No additional JavaScript needed

### 2.6 Test Filter Dirty State
- [x] Load PR list page with no filters
- [x] Change AI filter - button glows and text changes to "Apply Changes"
- [x] Verified in Playwright browser

---

## Phase 3: Apply to Analytics Page ✅ COMPLETE

### 3.1 Analytics PR Tab
- [x] Updated `templates/metrics/analytics/pull_requests.html`
- [x] Same dirty state pattern with 12 filters:
  - repo, author, reviewer, ai, ai_tool, state, size, has_jira, date_from, date_to
- [x] Added `techChanged` flag for multi-select Technology filter

### 3.2 Create Reusable Component (Future)
- [ ] Consider extracting filter form to `components/filter_form.html`
- [ ] Would allow single implementation for all filter forms
- [ ] Document pattern for other developers

---

## Verification Checklist ✅ ALL PASS

### Light Theme
- [x] Apply Filters button: white text on orange
- [x] Button is clearly visible and readable
- [x] Glow appears when filters changed
- [x] Text changes to "Apply Changes" when dirty

### Dark Theme
- [x] Apply Filters button: white text on orange (unchanged)
- [x] Glow appears when filters changed
- [x] Text changes to "Apply Changes" when dirty

### Functionality
- [x] Filters still apply correctly
- [x] URL updates with filter params
- [x] Clear button works
- [x] Export button uses current filters

### Accessibility
- [x] Button text readable in both themes
- [x] Focus states visible on filter controls

---

## Implementation Complete

All phases have been implemented and verified. Changes are ready to commit:

```bash
# Files changed:
# - assets/styles/site-tailwind.css (line 93: primary-content color)
# - templates/metrics/pull_requests/list.html (dirty state for 6 filters)
# - templates/metrics/analytics/pull_requests.html (dirty state for 12 filters)

# No migrations needed - CSS/template changes only
```
