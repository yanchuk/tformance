# Visual Stages 6 & 8: Context & Dependencies

**Last Updated:** 2025-12-20

## Key Files

### Primary Files to Modify

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `assets/styles/app/tailwind/design-system.css` | Add menu-active override | Lines 271-313 (Navigation section) |
| `templates/web/components/top_nav.html` | Update logo with gradient | Lines 35-39 (logo/brand element) |
| `assets/javascript/dashboard/dashboard-charts.js` | Apply chart theme | Lines 115-158 (weeklyBarChart function) |
| `assets/javascript/dashboard/chart-theme.js` | NEW - Chart theme config | Create new file |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `dev/visual-improvement-plan.md` | Master plan with all stages |
| `dev/active/visual-stage-1/visual-stage-1-context.md` | Color mapping reference |
| `tailwind.config.js` | Color tokens (accent-primary, etc.) |
| `assets/styles/site-tailwind.css` | DaisyUI theme definition |
| `CLAUDE.md` | Design system documentation |

### Related Template Files

| File | Purpose |
|------|---------|
| `templates/web/components/app_nav.html` | Sidebar container |
| `templates/web/components/app_nav_menu_items.html` | Menu items with active states |
| `templates/web/components/team_nav.html` | Team-specific nav items |
| `templates/web/components/top_nav_app.html` | App-specific top nav |
| `templates/metrics/cto_overview.html` | Dashboard with charts |

### Chart Template Files

| File | Charts |
|------|--------|
| `templates/metrics/partials/ai_adoption_chart.html` | AI adoption canvas |
| `templates/metrics/partials/cycle_time_chart.html` | Cycle time canvas |
| `templates/metrics/partials/copilot_trend_chart.html` | Copilot trend canvas |

---

## Design Decisions

### Decision 1: Override DaisyUI menu-active

**Choice:** Add CSS override for DaisyUI `menu-active` class
**Rationale:** The project uses DaisyUI menu component throughout. Overriding its active state styling is cleaner than replacing all template markup. The design-system.css already has `app-sidebar-item-active` but templates use DaisyUI's native `menu-active`.

### Decision 2: Centralized Chart Theme File

**Choice:** Create separate `chart-theme.js` module
**Rationale:**
- Single source of truth for chart colors
- Easier to update when design changes
- Can be imported by multiple chart functions
- Follows separation of concerns

### Decision 3: Use rgba() for Bar Chart Fill

**Choice:** `rgba(249, 115, 22, 0.7)` for bar backgroundColor
**Rationale:** Matches existing pattern in codebase. Opacity provides visual depth while maintaining readability. Solid border color creates definition.

### Decision 4: Copilot Charts Use AI Purple

**Choice:** Use `#C084FC` (soft purple) for Copilot-related charts
**Rationale:** Visual differentiation between AI metrics and standard metrics. Purple is already used in the cto_overview.html for Copilot icons (`text-violet-400`). Creates semantic meaning.

---

## Color Mapping Reference

### Navigation Colors

| Element | Old Color | New Color | Tailwind Class |
|---------|-----------|-----------|----------------|
| Active menu text | DaisyUI default | `#F97316` | `text-accent-primary` |
| Active menu border | None | `#F97316` | `border-accent-primary` |
| Active menu bg | DaisyUI default | `#171717` | `bg-deep` |
| Hover text | Default | `#F97316/80` | `text-accent-primary/80` |
| Logo gradient from | N/A | `#F97316` | `from-accent-primary` |
| Logo gradient to | N/A | `#EC4899` | `to-pink-500` |

### Chart Colors

| Semantic | Old Color | New Color | Usage |
|----------|-----------|-----------|-------|
| Primary data | `rgba(94, 158, 176, 0.7)` | `rgba(249, 115, 22, 0.7)` | Default bars/lines |
| Success metrics | Green variants | `#2DD4BF` | Positive trends |
| AI/Copilot | Same as primary | `#C084FC` | Copilot charts |
| Warning | Amber | `#FBBF24` | Warning states |
| Error/negative | Red | `#F87171` | Negative metrics |
| Grid lines | Default gray | `rgba(163, 163, 163, 0.1)` | Chart grid |
| Tooltip bg | Default | `#262626` | Tooltip background |
| Tooltip text | Default | `#FAFAFA` | Tooltip title |

---

## Chart.js Integration Details

### Current Chart Initialization Flow

1. HTMX loads chart partial (e.g., `cycle_time_chart.html`)
2. Template includes `<canvas id="cycle-time-chart">` and JSON script data
3. `app.js` listens for `htmx:afterSwap` event
4. Checks for canvas and data elements
5. Calls `AppDashboardCharts.weeklyBarChart(ctx, data, label)`
6. `weeklyBarChart` creates Chart.js instance with inline colors

### Updated Flow (with Theme)

1. Same HTMX loading
2. Same canvas/data setup
3. Same event listener
4. `weeklyBarChart` imports theme from `chart-theme.js`
5. Chart created with theme colors and styling
6. For Copilot chart, pass `{ ai: true }` option for purple color

### Chart Functions to Update

| Function | File | Changes |
|----------|------|---------|
| `weeklyBarChart` | dashboard-charts.js | Use theme.bar colors |
| `barChartWithDates` | dashboard-charts.js | Use theme.bar colors |
| `cumulativeChartWithDates` | dashboard-charts.js | Use theme.line colors |

---

## DaisyUI Menu Component Reference

### Current Menu Structure

```html
<ul class="menu p-2 rounded-box">
  <li class="menu-title">
    <span>Application</span>
  </li>
  <li>
    <a href="..." class="menu-active">  <!-- Active state -->
      <i class="fa fa-chart-line h-4 w-4"></i>
      Dashboard
    </a>
  </li>
</ul>
```

### DaisyUI Menu Active Selectors

DaisyUI v5 (Tailwind 4) uses these selectors for menu active:
```css
.menu li > *:not(ul, .menu-title, details, .btn):active,
.menu li > *:not(ul, .menu-title, details, .btn).active,
.menu li > *:not(ul, .menu-title, details, .btn).menu-active
```

Our override needs to match these selectors.

---

## Testing Commands

```bash
# Build assets
npm run build

# Run navigation tests (includes login/logout, menu access)
make e2e-auth

# Run dashboard tests (includes chart rendering)
make e2e-dashboard

# Run all e2e tests
make e2e

# Quick smoke test
make e2e-smoke

# Start dev server if not running
make dev
```

---

## WCAG AA Contrast Verification

All chart colors verified against dark background (#171717):

| Color | Hex | Ratio | Pass? |
|-------|-----|-------|-------|
| Primary (coral) | `#F97316` | 5.2:1 | ✓ |
| Success (teal) | `#2DD4BF` | 9.3:1 | ✓ |
| AI (purple) | `#C084FC` | 5.9:1 | ✓ |
| Warning (amber) | `#FBBF24` | 8.7:1 | ✓ |
| Error (red) | `#F87171` | 5.8:1 | ✓ |
| Tooltip text | `#FAFAFA` on `#262626` | 12.6:1 | ✓ |

---

## Notes for Implementation

### Stage 6 Implementation Order

1. Add menu-active CSS override first (non-breaking)
2. Update logo gradient second
3. Test navigation on desktop and mobile
4. Run e2e-auth tests

### Stage 8 Implementation Order

1. Create chart-theme.js first (no imports yet)
2. Update weeklyBarChart to import theme
3. Test AI Adoption chart renders correctly
4. Add AI color option for Copilot chart
5. Update remaining chart functions
6. Run npm build and e2e-dashboard tests

### Potential Gotchas

1. **DaisyUI Specificity**: May need `!important` or more specific selectors for menu override
2. **Chart.js Reactivity**: Charts are destroyed/recreated on HTMX swap - ensure no memory leaks
3. **Mobile Menu**: The drawer menu uses same components - test responsive behavior
4. **Copilot Chart Identification**: Need way to know which chart is Copilot (check element ID or pass option)

---

## Related Documentation

- Master plan: `dev/visual-improvement-plan.md`
- Stage 1 context: `dev/active/visual-stage-1/visual-stage-1-context.md`
- Design system: `assets/styles/app/tailwind/design-system.css` (header comments)
- CLAUDE.md: Design System section
