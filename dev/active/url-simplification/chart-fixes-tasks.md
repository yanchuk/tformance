# Chart Visualization Fixes - Tasks

## Completed This Session

- [x] Identify chart data format issue (date + count types)
- [x] Fix `chart_formatters.py` date format (YYYY-MM-DD)
- [x] Fix `chart_formatters.py` float conversion
- [x] Add `weeklyBarChart` function to dashboard-charts.js
- [x] Add `htmx:afterSwap` event handler to app.js
- [x] Add `destroyChartIfExists` helper function
- [x] Test chart creation manually (works via browser console)
- [x] Run all tests (361 pass)
- [x] Commit and push changes

## Remaining Tasks

- [ ] Fix chart auto-initialization on HTMX load
  - Option A: Add inline script to chart partial templates
  - Option B: Use `hx-on::after-swap` attribute on containers
  - Option C: Debug afterSwap timing with multiple swaps
- [ ] Test all time ranges (7d, 30d, 90d)
- [ ] Verify charts work with empty data (graceful fallback)

## Technical Debt

- [ ] Consider extracting chart initialization to separate module
- [ ] Add E2E tests for chart rendering (Playwright)
- [ ] Document Chart.js integration patterns for future charts
