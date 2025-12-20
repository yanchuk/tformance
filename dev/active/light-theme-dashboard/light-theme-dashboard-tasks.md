# Light Theme Dashboard - Task Checklist

**Last Updated:** 2025-12-20

Use this checklist to track implementation progress. Mark tasks with `[x]` when complete.

---

## Phase 1: Theme Foundation

- [ ] **1.1** Create "tformance-light" DaisyUI theme in `site-tailwind.css`
  - [ ] Define base colors (base-100, base-200, base-300, base-content)
  - [ ] Define primary/secondary/accent colors
  - [ ] Define status colors (success, warning, error, info)
  - [ ] Test theme compiles without errors

- [ ] **1.2** Add light-mode design system classes in `design-system.css`
  - [ ] Update `.app-card` for theme awareness
  - [ ] Update `.app-btn-*` variants
  - [ ] Update `.app-stat-*` variants
  - [ ] Update `.app-sidebar-*` variants
  - [ ] Update text utility classes

- [ ] **1.3** Define Chart.js color palette for light theme
  - [ ] Create theme-aware color configuration
  - [ ] Test chart readability on light background

---

## Phase 2: Base Templates

- [ ] **2.1** Update `app_base.html` to use light theme
  - [ ] Add `data-theme="tformance-light"` to html element
  - [ ] Verify all app pages inherit light theme

- [ ] **2.2** Verify marketing pages stay dark
  - [ ] Confirm `base.html` still uses `tformance` theme
  - [ ] Test homepage renders unchanged

---

## Phase 3: Navigation Components

- [ ] **3.1** Update sidebar navigation (`app_nav.html`)
  - [ ] Update background color
  - [ ] Update text colors
  - [ ] Update border colors
  - [ ] Test dropdown functionality

- [ ] **3.2** Update top navigation bar (`top_nav_app.html`)
  - [ ] Update background color
  - [ ] Update text colors
  - [ ] Test user menu

- [ ] **3.3** Update menu items (`app_nav_menu_items.html`)
  - [ ] Update default state colors
  - [ ] Update hover state colors
  - [ ] Update active state colors
  - [ ] Verify icons visible

---

## Phase 4: Dashboard Home

- [ ] **4.1** Update `app_home.html`
  - [ ] Update page background
  - [ ] Update card backgrounds
  - [ ] Update text colors
  - [ ] Update badge colors
  - [ ] Test all three states (has data, waiting, setup)

- [ ] **4.2** Update `quick_stats.html`
  - [ ] Update stat card backgrounds
  - [ ] Update stat value colors
  - [ ] Update stat description colors
  - [ ] Update change indicator colors

- [ ] **4.3** Update `recent_activity.html`
  - [ ] Update card background
  - [ ] Update activity item styling
  - [ ] Update timestamp colors
  - [ ] Update icon backgrounds

- [ ] **4.4** Update setup components
  - [ ] Update `setup_wizard.html`
  - [ ] Update `setup_prompt.html`
  - [ ] Update `empty_state.html`

---

## Phase 5: Metrics Dashboard

- [ ] **5.1** Update `team_dashboard.html`
  - [ ] Update main container styling
  - [ ] Update card containers
  - [ ] Update section headers
  - [ ] Update alert styling

- [ ] **5.2** Update `key_metrics_cards.html`
  - [ ] Update card backgrounds
  - [ ] Update metric values
  - [ ] Update trend indicators

- [ ] **5.3** Update chart partials
  - [ ] `cycle_time_chart.html` - Update Chart.js config
  - [ ] `review_time_chart.html` - Update Chart.js config
  - [ ] `pr_size_chart.html` - Update Chart.js config
  - [ ] `review_distribution_chart.html` - Update Chart.js config
  - [ ] `ai_adoption_chart.html` - Update Chart.js config
  - [ ] `ai_quality_chart.html` - Update Chart.js config
  - [ ] `copilot_trend_chart.html` - Update Chart.js config

- [ ] **5.4** Update table partials
  - [ ] `leaderboard_table.html`
  - [ ] `recent_prs_table.html`
  - [ ] `reviewer_workload_table.html`
  - [ ] `team_breakdown_table.html`
  - [ ] `unlinked_prs_table.html`
  - [ ] `copilot_members_table.html`

- [ ] **5.5** Update `cto_overview.html`
  - [ ] Update page styling
  - [ ] Update card layouts
  - [ ] Test all visualizations

- [ ] **5.6** Update `revert_rate_card.html`
- [ ] **5.7** Update `copilot_metrics_card.html`
- [ ] **5.8** Update `filters.html`

---

## Phase 6: Integration Pages

- [ ] **6.1** Update Jira integration pages
  - [ ] `jira_projects_list.html`
  - [ ] `jira_select_site.html`

- [ ] **6.2** Update Slack settings
  - [ ] `slack_settings.html`

---

## Phase 7: Polish & Testing

- [ ] **7.1** Accessibility audit
  - [ ] Run contrast checker on all text
  - [ ] Verify all text meets 4.5:1 ratio
  - [ ] Check focus states are visible
  - [ ] Test with screen reader

- [ ] **7.2** Visual QA
  - [ ] Screenshot all pages
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
| Phase 1 | Not Started | 0/3 |
| Phase 2 | Not Started | 0/2 |
| Phase 3 | Not Started | 0/3 |
| Phase 4 | Not Started | 0/4 |
| Phase 5 | Not Started | 0/8 |
| Phase 6 | Not Started | 0/2 |
| Phase 7 | Not Started | 0/4 |
| **Total** | **Not Started** | **0/26** |

---

## Notes

_Add implementation notes here as work progresses_

-
