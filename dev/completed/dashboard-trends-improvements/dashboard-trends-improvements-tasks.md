# Dashboard & Trends Improvements - Tasks

**Last Updated:** 2025-12-26

## Phase 1: Dashboard Icon Removal + Card Fixes (Effort: S) ✅ COMPLETED

### 1.1 Remove stat-figure icons from quick_stats.html
- [x] Remove all `<div class="stat-figure ...">` sections (4 total)
- [x] Verify layout looks clean without icons

### 1.2 Fix key_metrics_cards.html sparklines and card sizing
- [x] Add explicit `p-4` padding to stat cards
- [x] Add responsive text sizing `text-2xl lg:text-3xl truncate` to stat-value
- [x] Fix sparkline container with `-mx-4 px-1` (edge-to-edge with breathing room)
- [x] Add `text-xs` to stat-title and stat-desc for compact layout

---

## Phase 1b: Time Range Filter Position Consistency (Effort: S) 🔴 NEW

**Issue**: Time range filter position is inconsistent:
- Delivery page: BELOW tabs, left-aligned
- PR List page: RIGHT of tabs, upper corner

### Tasks:
- [ ] Decide on consistent position (recommend: below tabs)
- [ ] Update `base_analytics.html` to move time range below tabs
- [ ] Update PR list page to match
- [ ] Test navigation between pages doesn't "jump" filter position

**Files to modify:**
- `templates/metrics/analytics/base_analytics.html`
- `templates/metrics/pull_requests/list.html`

---

## Phase 1c: Card Text Overflow Fix (Effort: S) 🔴 NEW

**Issue**: At narrow viewport widths (~800px), card values overflow:
- "14.4h" displays as "14.4|" (cut off)

### Tasks:
- [ ] Change responsive sizing: `text-xl sm:text-2xl lg:text-3xl` (more aggressive)
- [ ] Test at viewports: 768px, 1024px, 1280px
- [ ] Consider using `font-size: clamp()` for smoother scaling
- [ ] Create Playwright E2E test for card overflow

**Files to modify:**
- `templates/metrics/partials/key_metrics_cards.html`

---

## Phase 1d: Bar Chart Data Labels (Effort: M) 🔴 NEW

**Issue**: Bar charts require hover to see values. Values should be visible without interaction.

### Tasks:
- [ ] Check if `chartjs-plugin-datalabels` is installed
- [ ] If not, install: `npm install chartjs-plugin-datalabels`
- [ ] Register plugin in chart configuration
- [ ] Enable datalabels for bar charts (AI Adoption Trend, Cycle Time Trend)
- [ ] Configure label position (top of bar), color, font size
- [ ] Test that labels don't overlap at various data ranges

**Files to modify:**
- `package.json` (if installing plugin)
- `assets/javascript/app.js` or chart config files
- Chart template partials that render bar charts

**Chart.js datalabels example:**
```javascript
plugins: {
  datalabels: {
    anchor: 'end',
    align: 'top',
    color: '#666',
    font: { weight: 'bold', size: 11 }
  }
}
```

---

## Phase 2: Trends Page Width Fix (Effort: S)

### 2.1 Analyze width inconsistency
- [ ] Compare Trends page vs other analytics tabs
- [ ] Identify CSS causing width jump

### 2.2 Apply fix
- [ ] Add consistent container width classes
- [ ] Match other analytics page layouts

### 2.3 Create Playwright E2E test
- [ ] Write test in `tests/e2e/trends.spec.ts`
- [ ] Verify width consistency across tabs

---

## Phase 3: Multi-Metric Comparison (Effort: M)

- [ ] Replace single select with checkbox group
- [ ] Update chart to handle multiple datasets
- [ ] Add legend for metric identification

---

## Phase 4: PR Type Breakdown Trends (Effort: M)

- [ ] Create `get_pr_type_breakdown()` service function
- [ ] Query `llm_summary.summary.type` field
- [ ] Create stacked bar chart visualization
- [ ] Add to Trends page

---

## Phase 5: Technology Breakdown Trends (Effort: M)

- [ ] Create `get_tech_category_breakdown()` service function
- [ ] Query `llm_summary.tech.categories` field
- [ ] Create stacked area/pie chart
- [ ] Add to Trends page

---

## Phase 6: ICP Data Review (Effort: S)

- [ ] Document CTO data needs
- [ ] Map to existing metrics
- [ ] Prioritize future enhancements

---

## Priority Order (Recommended)

1. **Phase 1c** - Card overflow (high visibility bug)
2. **Phase 1b** - Time range position (UX consistency)
3. **Phase 1d** - Chart data labels (UX improvement)
4. **Phase 2** - Trends width fix
5. **Phase 3-6** - Feature additions

---

## Testing Commands

```bash
# Unit tests
make test ARGS='apps.metrics.tests'

# E2E tests (after writing)
npx playwright test tests/e2e/analytics.spec.ts

# Specific viewport test
npx playwright test --viewport-size=768,1024
```

---

## Definition of Done

- [ ] All phases completed
- [ ] No card overflow at 768px+ viewports
- [ ] Time range position consistent across pages
- [ ] Chart values visible without hover
- [ ] E2E tests passing
- [ ] No regressions in existing functionality
