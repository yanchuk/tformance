# Dashboard & Trends Improvements - Context

**Last Updated:** 2025-12-26

## Current Implementation State

### Phase 1 - COMPLETED
- ✅ Removed 4 stat-figure icons from `quick_stats.html`
- ✅ Fixed `key_metrics_cards.html` - added padding, responsive text, sparkline alignment

### Phase 1b-1d - NEW ISSUES FROM SCREENSHOTS (PENDING)
Issues identified from user screenshots:

1. **Time Range Filter Position Inconsistency**
   - Delivery page: Time range is BELOW tabs (left-aligned)
   - PR List page: Time range is RIGHT of tabs (upper corner)
   - Need: Consistent position across all analytics pages

2. **Card Text Overflow at Narrow Widths**
   - Screenshot shows "14.4h" getting cut off as "14.4|" at ~800px width
   - Current `text-2xl lg:text-3xl` isn't aggressive enough
   - Need: More aggressive responsive sizing or auto-scaling

3. **Bar Charts Need Data Labels**
   - Current charts (AI Adoption Trend, Cycle Time Trend) require hover to see values
   - Need: Display values directly on/above bars without hover
   - Affects: Chart.js datalabels plugin configuration

## Key Files

### Analytics Layout
- `templates/metrics/analytics/base_analytics.html` - Has tabs + time range (RIGHT position)
- `templates/metrics/analytics/delivery.html` - Shows time range BELOW tabs
- `templates/metrics/pull_requests/list.html` - PR list page layout

### Key Metrics Cards
- `templates/metrics/partials/key_metrics_cards.html` - Modified with responsive sizing
- `templates/web/components/quick_stats.html` - Modified (icons removed)

### Charts
- `assets/javascript/dashboard/sparkline.js` - Sparkline rendering
- `templates/metrics/partials/chart_*.html` - Individual chart templates
- Chart.js config needs datalabels plugin for showing values on bars

## Key Decisions Made This Session

1. **Icon Removal**: Removed entire `stat-figure` divs, not just hidden
2. **Sparkline Edge-to-Edge**: Using `-mx-4 px-1` to extend sparklines to card edges
3. **Responsive Text**: Using `text-2xl lg:text-3xl truncate` but needs more aggressive sizing

## Files Modified This Session

| File | Changes |
|------|---------|
| `templates/web/components/quick_stats.html` | Removed 4 SVG icon divs |
| `templates/metrics/partials/key_metrics_cards.html` | Added p-4, responsive text, sparkline margin fixes |
| `dev/active/dashboard-trends-improvements/*` | Created planning docs |

## Blockers/Issues Discovered

1. **Playwright Network Issues**: MCP Playwright times out connecting to localhost:8000
   - Server is running (curl returns 200)
   - May need to close/reopen browser or check proxy settings

2. **Card Width Still Insufficient**: Even with `text-2xl lg:text-3xl`, values overflow at narrow widths
   - Need to test with actual Playwright at specific viewport widths
   - May need `text-xl md:text-2xl lg:text-3xl` or smaller base size

## Next Immediate Steps

1. **Fix Time Range Position**: Make consistent across all pages
   - Option A: Always below tabs (like Delivery page)
   - Option B: Always right of tabs (like PR List)
   - Recommend: Below tabs - more room, clearer hierarchy

2. **Fix Card Overflow**: More aggressive responsive sizing
   ```html
   <!-- Current -->
   <div class="stat-value text-2xl lg:text-3xl truncate">
   <!-- Proposed -->
   <div class="stat-value text-xl sm:text-2xl lg:text-3xl truncate">
   ```

3. **Add Chart Data Labels**: Enable Chart.js datalabels plugin
   - Install: `chartjs-plugin-datalabels` if not present
   - Configure in chart options

4. **E2E Test**: Once Playwright works, test at viewport widths:
   - 1280px (laptop)
   - 1024px (tablet landscape)
   - 768px (tablet portrait)
   - Check card overflow at each

## URL Patterns

```
/app/metrics/analytics/?days=30           # Overview (redirects)
/app/metrics/analytics/delivery/?days=30  # Delivery Metrics
/app/metrics/analytics/pull-requests/     # PR List page
```

## Django-Specific Progress

- **Models**: No changes
- **Views**: No changes
- **URLs**: No changes
- **Templates**: 2 modified (quick_stats.html, key_metrics_cards.html)
- **Migrations**: Not needed
- **Tests**: No new tests yet (E2E planned for Phase 2)

## Uncommitted Changes (as of session end)

```
M templates/metrics/partials/key_metrics_cards.html  # Card fixes
M templates/web/components/quick_stats.html          # Icon removal
?? dev/active/dashboard-trends-improvements/         # This task docs
```

**Note**: `ai_bot_reviews_card.html` and `copilot_metrics_card.html` also show as modified but were NOT changed in this session - they were pre-existing changes.

## Commands to Run on Resume

```bash
# Verify server running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/

# Check uncommitted changes
git status --short

# View diff of our changes
git diff templates/web/components/quick_stats.html
git diff templates/metrics/partials/key_metrics_cards.html

# Run tests to ensure no regressions
make test ARGS='apps.metrics.tests'

# Build frontend assets if needed
make npm-dev

# Test the analytics page visually
# Navigate to: http://localhost:8000/app/metrics/analytics/?days=30
```

## Resume Instructions

To continue this work:

1. Read `dev/active/dashboard-trends-improvements/dashboard-trends-improvements-tasks.md`
2. Start with **Phase 1c** (card overflow) - highest priority
3. Test with Playwright at narrow viewports (768px-1024px)
4. Then proceed to Phase 1b, 1d in order
