# Visual Stages 5 & 9: Task Checklist

**Last Updated:** 2025-12-20
**Status:** ✅ COMPLETE
**Branch:** visual-dashboard

---

## Phase 1: Pre-flight Checks

- [x] Verify Stage 1-2 completed: `accent-primary`, `accent-tertiary`, `accent-error` tokens exist
- [x] Verify dev server running: `curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/`
- [x] Verify CSS builds: `npm run build`

---

## Phase 2: cto_overview.html - Section Icons

**File:** `templates/metrics/cto_overview.html`

- [x] **2.1** Line 63: Update GitHub Copilot divider icon from `text-violet-400` to `text-accent-primary`
- [x] **2.2** Line 87: Update Acceptance Rate Trend icon from `text-violet-400` to `text-accent-primary`
- [x] **2.3** Line 108: Update Copilot Usage by Member icon from `text-violet-400` to `text-accent-primary`
- [x] **2.4** Line 130: Update Cycle Time Trend icon from `text-primary` to `text-accent-primary`
- [x] **2.5** Line 151: Update Review Time Trend icon from `text-secondary` to `text-accent-primary`
- [x] **2.6** Line 176: Update PR Size Distribution icon from `text-accent` to `text-accent-primary`
- [x] **2.7** Line 228: Update Reviewer Workload icon from `text-info` to `text-accent-primary`

**Keep unchanged (semantic colors):**
- Line 195: Quality Indicators icon - keep `text-warning` ✓
- Line 247: PRs Missing Jira Links icon - keep `text-error` ✓

---

## Phase 3: Metric Card Partials

### 3.1 key_metrics_cards.html

**File:** `templates/metrics/partials/key_metrics_cards.html`

- [x] **3.1.1** Line 6: PRs Merged - keep `text-primary` (maps to accent-primary via DaisyUI theme)
- [x] **3.1.2** Line 26: Avg Cycle Time - keep `text-secondary` (maps to accent-secondary via theme)
- [x] **3.1.3** Line 35: Avg Quality - keep `text-accent` (maps to accent-tertiary via theme)
- [x] **3.1.4** Line 44: AI-Assisted - keep `text-info` (maps to accent-info via theme)
- [x] **3.1.5** Lines 11-13: Update positive change from `text-success` to `text-accent-tertiary`
- [x] **3.1.6** Lines 11-13: Update negative change from `text-error` to `text-accent-error`

### 3.2 copilot_metrics_card.html

**File:** `templates/metrics/partials/copilot_metrics_card.html`

- [x] **3.2.1** Review stat value colors - keep DaisyUI semantic classes (inherit from theme)

### 3.3 revert_rate_card.html

**File:** `templates/metrics/partials/revert_rate_card.html`

- [x] **3.3.1** Review badge colors - keep DaisyUI badge classes (inherit from theme)

---

## Phase 4: Empty State Component

**File:** `templates/web/components/empty_state.html`

- [x] **4.1** Line 17: Update icon container from `text-slate-600` to warm pattern:
  ```html
  <div class="{% if compact %}w-10 h-10{% else %}w-12 h-12{% endif %} mx-auto mb-4 rounded-full bg-accent-primary/10 flex items-center justify-center">
  ```
- [x] **4.2** Line 18: Update SVG class to `w-6 h-6 text-accent-primary` (or `w-5 h-5` for compact)
- [x] **4.3** Line 48: Update title from `text-slate-300` to `text-neutral-300`
- [x] **4.4** Line 54: Update description from `text-slate-400` to `text-neutral-400`
- [x] **4.5** Verify CTA button uses `app-btn-primary` class (line 61)

---

## Phase 5: Chart Empty States

### 5.1 ai_adoption_chart.html

**File:** `templates/metrics/partials/ai_adoption_chart.html`

- [x] **5.1.1** Lines 7-12: Update empty state pattern:
  - Add `rounded-full bg-accent-primary/10 flex items-center justify-center` to icon container
  - Update icon to `text-accent-primary`
  - Update text colors to `text-neutral-300` / `text-neutral-400`

### 5.2 copilot_trend_chart.html

**File:** `templates/metrics/partials/copilot_trend_chart.html`

- [x] **5.2.1** Lines 7-12: Update empty state pattern (same as 5.1.1)

### 5.3 Other Chart Partials (check for empty states)

- [x] **5.3.1** Check `ai_quality_chart.html` for empty state - UPDATED
- [x] **5.3.2** Check `cycle_time_chart.html` for empty state - UPDATED
- [x] **5.3.3** Check `review_time_chart.html` for empty state - UPDATED
- [x] **5.3.4** Check `pr_size_chart.html` for empty state - UPDATED
- [x] **5.3.5** Check `review_distribution_chart.html` for empty state - UPDATED

---

## Phase 6: Table Empty States

### 6.1 copilot_members_table.html

**File:** `templates/metrics/partials/copilot_members_table.html`

- [x] **6.1.1** Lines 43-48: Update empty state:
  - Add icon container with `rounded-full bg-accent-primary/10`
  - Update icon to `w-6 h-6 text-accent-primary`
  - Update text colors

### 6.2 leaderboard_table.html

**File:** `templates/metrics/partials/leaderboard_table.html`

- [x] **6.2.1** Lines 51-57: Update empty state pattern

### 6.3 team_breakdown_table.html

**File:** `templates/metrics/partials/team_breakdown_table.html`

- [x] **6.3.1** Lines 42-47: Update empty state pattern

### 6.4 reviewer_workload_table.html

**File:** `templates/metrics/partials/reviewer_workload_table.html`

- [x] **6.4.1** Lines 38-43: Update empty state pattern

### 6.5 unlinked_prs_table.html (Success State)

**File:** `templates/metrics/partials/unlinked_prs_table.html`

- [x] **6.5.1** Lines 29-35: Update success empty state:
  - Add icon container with `rounded-full bg-accent-tertiary/10`
  - Updated icon to `text-accent-tertiary`
  - Keep success message styling

### 6.6 recent_prs_table.html

**File:** `templates/metrics/partials/recent_prs_table.html`

- [x] **6.6.1** Check if file has empty state and update if needed - UPDATED

---

## Phase 7: Validation

- [x] **7.1** Run CSS build: `npm run build` ✓
- [x] **7.2** Run dashboard e2e tests: `make e2e-dashboard` ✓ (34/34 tests pass)
- [x] **7.3** Visual verification checklist:
  - [x] Dashboard loads correctly
  - [x] Section icons are coral orange
  - [x] Metric cards use warm colors
  - [x] Empty states have warm icon backgrounds
  - [x] Positive metrics show teal
  - [x] Negative metrics show soft red
  - [x] All HTMX partials load correctly
  - [x] No console errors
  - [x] No layout breaks

---

## Completion Summary

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Pre-flight | ✅ Complete | Dev server running, build works |
| Phase 2: cto_overview.html | ✅ Complete | 7 section icons updated |
| Phase 3: Metric Partials | ✅ Complete | Change indicators updated |
| Phase 4: Empty State Component | ✅ Complete | Warm icon pattern applied |
| Phase 5: Chart Empty States | ✅ Complete | 7 charts updated |
| Phase 6: Table Empty States | ✅ Complete | 6 tables updated |
| Phase 7: Validation | ✅ Complete | 34/34 e2e tests pass |

**Legend:**
- ⬜ Not Started
- 🔄 In Progress
- ✅ Complete
- ⏸️ Blocked

---

## Implementation Complete

**Date:** 2025-12-20

**Summary:** Visual Stages 5 and 9 successfully implemented. All dashboard section icons and empty states now use the warm Sunset Dashboard color palette.
