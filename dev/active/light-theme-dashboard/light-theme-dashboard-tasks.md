# Light Theme Dashboard - Task Checklist

**Last Updated:** 2025-12-20 (Session 3)

Use this checklist to track implementation progress. Mark tasks with `[x]` when complete.

---

## Phase 1: Theme Foundation ✅ COMPLETE

- [x] **1.1** Create "tformance-light" DaisyUI theme in `site-tailwind.css`
  - [x] Define base colors (base-100, base-200, base-300, base-content)
  - [x] Define primary/secondary/accent colors
  - [x] Define status colors (success, warning, error, info)
  - [x] Test theme compiles without errors

- [x] **1.2** Add light-mode design system classes in `design-system.css`
  - [x] Update `.app-card` for theme awareness
  - [x] Update `.app-btn-*` variants
  - [x] Update `.app-stat-*` variants
  - [x] Update `.app-sidebar-*` variants
  - [x] Update text utility classes

- [x] **1.3** Define Chart.js color palette for light theme
  - [x] Create theme-aware color configuration
  - [x] Test chart readability on light background

---

## Phase 2: Base Templates ✅ COMPLETE

- [x] **2.1** Update `app_base.html` to use light theme
  - [x] Add `data-theme="tformance-light"` to html element
  - [x] Verify all app pages inherit light theme

- [x] **2.2** Verify marketing pages stay dark
  - [x] Confirm `base.html` still uses `tformance` theme
  - [x] Test homepage renders unchanged

---

## Phase 3: Navigation Components ✅ COMPLETE (via design system)

- [x] **3.1** Update sidebar navigation (`app_nav.html`)
  - [x] Update background color (via design system)
  - [x] Update text colors (via design system)
  - [x] Update border colors (via design system)
  - [x] Test dropdown functionality

- [x] **3.2** Update top navigation bar (`top_nav_app.html`)
  - [x] Update background color
  - [x] Update text colors
  - [x] Test user menu

- [x] **3.3** Update menu items (`app_nav_menu_items.html`)
  - [x] Update default state colors
  - [x] Update hover state colors
  - [x] Update active state colors
  - [x] Verify icons visible

---

## Phase 4: Dashboard Home ✅ COMPLETE

- [x] **4.1** Update `app_home.html`
  - [x] Update page background (via base template)
  - [x] Update card backgrounds (via design system)
  - [x] Update text colors (via design system)
  - [x] Update badge colors (DaisyUI theme-aware)
  - [x] Test all three states (has data, waiting, setup)

- [x] **4.2** Update `quick_stats.html`
  - [x] Update stat card backgrounds
  - [x] Update stat value colors
  - [x] Update stat description colors
  - [x] Update change indicator colors

- [x] **4.3** Update `recent_activity.html`
  - [x] Update card background
  - [x] Update activity item styling
  - [x] Update timestamp colors
  - [x] Update icon backgrounds

- [x] **4.4** Update setup components
  - [x] Update `setup_wizard.html` (already theme-aware)
  - [x] Update `setup_prompt.html` (already theme-aware)
  - [x] Update `empty_state.html` (fixed text-neutral colors)

---

## Phase 5: Metrics Dashboard ✅ COMPLETE

- [x] **5.1** Update `team_dashboard.html` (mostly working via design system)
  - [x] Update main container styling
  - [x] Update card containers
  - [x] Update section headers
  - [x] Update alert styling (DaisyUI theme-aware)

- [x] **5.2** Update `key_metrics_cards.html`
  - [x] Update card backgrounds
  - [x] Update metric values
  - [x] Update trend indicators

- [x] **5.3** Update chart partials (fixed empty state text colors)
  - [x] `cycle_time_chart.html` - Fixed text-neutral-300
  - [x] `review_time_chart.html` - Fixed text-neutral-300
  - [x] `pr_size_chart.html` - Fixed text-neutral-300
  - [x] `review_distribution_chart.html` - Fixed text-neutral-300/400
  - [x] `ai_adoption_chart.html` - Fixed text-neutral-300
  - [x] `ai_quality_chart.html` - Fixed text-neutral-300
  - [x] `copilot_trend_chart.html` - Fixed text-neutral-300

- [x] **5.4** Update table partials (fixed empty state text colors)
  - [x] `leaderboard_table.html` - Fixed text-neutral-300/400
  - [x] `recent_prs_table.html` - Fixed text-neutral-300/400
  - [x] `reviewer_workload_table.html` - Fixed text-neutral-300
  - [x] `team_breakdown_table.html` - Fixed text-neutral-300
  - [x] `unlinked_prs_table.html` - Fixed text-neutral-400
  - [x] `copilot_members_table.html` - Fixed text-neutral-300

- [x] **5.5** Update `cto_overview.html`
  - [x] Update page styling (working)
  - [x] Update card layouts
  - [x] Test all visualizations (basic check done)

- [x] **5.6** Update `revert_rate_card.html` (DaisyUI theme-aware)
- [x] **5.7** Update `copilot_metrics_card.html` (DaisyUI theme-aware)
- [x] **5.8** Update `filters.html` (DaisyUI theme-aware)

---

## Phase 6: Integration Pages ✅ COMPLETE

- [x] **6.1** Update integration home (`home.html`)
  - [x] Replace all text-slate-* with text-base-content/*
  - [x] Replace bg-elevated with bg-base-300
  - [x] Update icon colors

- [x] **6.2** Update Jira integration pages
  - [x] `jira_projects_list.html` - Extends app_base.html (inherits light theme)
  - [x] `jira_select_site.html` - Standalone (not in app context)

- [x] **6.3** Update Slack settings
  - [x] `slack_settings.html` - Extends app_base.html (inherits light theme)

---

## Phase 7: Polish & Testing ⏳ PENDING

- [ ] **7.1** Accessibility audit
  - [ ] Run contrast checker on all text
  - [ ] Verify all text meets 4.5:1 ratio
  - [ ] Check focus states are visible
  - [ ] Test with screen reader

- [ ] **7.2** Visual QA
  - [x] Screenshot all pages (basic check done)
  - [ ] Compare with design goals
  - [ ] Check for visual inconsistencies
  - [ ] Verify responsive behavior

- [ ] **7.3** Cross-browser testing
  - [ ] Test in Chrome
  - [ ] Test in Firefox
  - [ ] Test in Safari
  - [ ] Fix any rendering issues

- [ ] **7.4** Final cleanup
  - [ ] Remove unused dark-only classes
  - [ ] Update CLAUDE.md design system section
  - [ ] Update dev/visual-improvement-plan.md

---

## Progress Summary

| Phase | Status | Tasks Done |
|-------|--------|------------|
| Phase 1 | ✅ Complete | 3/3 |
| Phase 2 | ✅ Complete | 2/2 |
| Phase 3 | ✅ Complete | 3/3 |
| Phase 4 | ✅ Complete | 4/4 |
| Phase 5 | ✅ Complete | 8/8 |
| Phase 6 | ✅ Complete | 3/3 |
| Phase 7 | ⏳ Pending | 0/4 |
| **Total** | **~85%** | **~23/27** |

---

## Notes

### Session 2 Progress (2025-12-20)

1. **Created tformance-light theme** in `site-tailwind.css`
   - Warm off-white background (#FAFAF8)
   - Kept coral orange primary (#F97316) for brand consistency
   - Status colors adjusted for light background contrast

2. **Made design-system.css fully theme-aware**
   - Replaced all hardcoded colors with DaisyUI theme variables
   - `bg-surface` → `bg-base-200`
   - `bg-deep` → `bg-base-100`
   - `bg-elevated` → `bg-base-300`
   - `text-neutral-*` → `text-base-content/*`
   - This automatically fixed navigation, cards, buttons, tables, etc.

3. **Fixed integrations/home.html template**
   - Replaced all `text-slate-*` with `text-base-content/*`
   - Updated icon backgrounds to `bg-base-300`
   - Integration cards now properly light-themed

4. **Commits Made:**
   - `7b82105` - Add tformance-light theme for internal dashboard
   - `90f60cf` - Make design system theme-aware for light/dark support

### What's Working Well
- Dashboard home page looks clean and professional
- Analytics/CTO overview page working
- Integration cards now match light theme
- Navigation sidebar properly themed
- All DaisyUI components automatically adapt

### Known Issues / Remaining Work
- Chart.js colors may need light-theme optimization
- Some table partials may have hardcoded colors
- Jira/Slack settings pages not yet reviewed
- Need full accessibility audit
- Setup wizard components not tested

### Session 3 Progress (2025-12-20)

1. **Made Chart.js theme-aware**
   - Updated `chart-theme.js` to detect light vs dark theme
   - Grid lines, axis text, tooltips now adapt to theme
   - Data colors (coral, teal, purple) remain consistent

2. **Fixed all chart/table partials**
   - Replaced `text-neutral-300/400` with `text-base-content/60/50`
   - 13 partial templates updated

3. **Fixed `empty_state.html` component**
   - Replaced hardcoded neutral colors with theme-aware classes

4. **Reviewed Jira/Slack/setup pages**
   - `setup_wizard.html` - Already theme-aware
   - `setup_prompt.html` - Already theme-aware
   - Jira/Slack settings pages inherit from `app_base.html`

5. **Commits Made:**
   - `2a8075e` - Fix hardcoded colors in chart/table partials
   - `405c6cd` - Add light theme support to Chart.js
   - `2ae425e` - Update light theme dashboard documentation
   - `11c85d0` - Fix hardcoded colors in empty_state.html

### Remaining Work (Phase 7)
- Full accessibility audit (contrast ratios, focus states)
- Cross-browser testing (Chrome, Firefox, Safari)
- Update CLAUDE.md design system section

