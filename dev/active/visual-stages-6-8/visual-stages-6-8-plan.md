# Visual Stages 6 & 8 Implementation Plan

**Last Updated:** 2025-12-20

## Executive Summary

This plan implements Visual Stages 6 (Navigation/Sidebar) and 8 (Charts) from the "Sunset Dashboard" visual improvement initiative. These stages apply the warm coral/orange color scheme to navigation elements and Chart.js visualizations, completing key UI touchpoints for the new design system.

**Scope:**
- Stage 6: Update sidebar/navigation active states and logo with warm gradient
- Stage 8: Create centralized chart theme and apply to all Chart.js instances

**Prerequisites:** Stages 1-2 complete (color tokens and design system CSS classes updated)

---

## Current State Analysis

### Navigation (Stage 6)

**Current Implementation:**
- Sidebar navigation uses DaisyUI `menu` component (`templates/web/components/app_nav.html`)
- Menu items use `menu-active` class for active state (DaisyUI default styling)
- Logo uses generic rocket icon with `text-primary` class
- No custom sidebar styling beyond DaisyUI defaults

**Key Files:**
| File | Purpose |
|------|---------|
| `templates/web/components/app_nav.html` | Main sidebar container |
| `templates/web/components/app_nav_menu_items.html` | Menu items with `menu-active` class |
| `templates/web/components/team_nav.html` | Team-specific nav items |
| `templates/web/components/top_nav.html` | Top navbar with logo |
| `assets/styles/app/tailwind/design-system.css` | Already has `.app-sidebar-*` classes |

**Current Active State:** DaisyUI's `menu-active` applies default primary color styling. We need to ensure it uses our warm accent colors.

### Charts (Stage 8)

**Current Implementation:**
- Chart.js used for dashboard visualizations
- Colors defined inline in `dashboard-charts.js` (hardcoded cyan/teal: `rgba(94, 158, 176, 0.7)`)
- No centralized theme object
- Three chart types: AI Adoption, Cycle Time, Copilot Trend

**Key Files:**
| File | Purpose |
|------|---------|
| `assets/javascript/dashboard/dashboard-charts.js` | Chart rendering functions |
| `assets/javascript/app.js` | Chart initialization on HTMX swap |
| `templates/metrics/partials/*_chart.html` | Chart canvas elements |

**Current Colors:** `rgba(94, 158, 176, 0.7)` (muted cyan) - needs update to warm palette.

---

## Proposed Future State

### Stage 6: Navigation & Sidebar

1. **Active menu items** display with:
   - Orange text (`text-accent-primary`)
   - Left border accent (`border-l-2 border-accent-primary`)
   - Subtle background highlight

2. **Logo** uses warm gradient:
   - `from-accent-primary to-pink-500`
   - Rounded container with white icon/letter

3. **Hover states** use warm tones:
   - Text transitions to `text-accent-primary/80`
   - Subtle background change

### Stage 8: Charts

1. **Centralized theme object** (`chart-theme.js`):
   - Primary: `#F97316` (coral orange)
   - Success: `#2DD4BF` (teal)
   - AI-related: `#C084FC` (soft purple)
   - Grid/tooltip styling with neutral colors

2. **All Chart.js instances** use theme:
   - Consistent bar/line colors
   - Matching tooltip styling
   - Grid colors aligned with design system

---

## Implementation Phases

### Phase 1: Navigation Styling (Stage 6)

#### 1.1 Update DaisyUI Menu Active Override

Add CSS to override DaisyUI's `menu-active` class with warm colors.

**File:** `assets/styles/app/tailwind/design-system.css`

```css
/* DaisyUI menu-active override for warm colors */
.menu li > *:not(ul, .menu-title, details, .btn):active,
.menu li > *:not(ul, .menu-title, details, .btn).active,
.menu li > *:not(ul, .menu-title, details, .btn).menu-active,
.menu li > details > summary:active {
  @apply bg-deep text-accent-primary;
  @apply border-l-2 border-accent-primary;
}
```

**Acceptance Criteria:**
- [ ] Active menu items show coral orange text
- [ ] Active items have left border accent
- [ ] Hover states use warm tones
- [ ] No visual regressions in navigation

#### 1.2 Update Logo/Brand Element

Update logo in `top_nav.html` with warm gradient background.

**File:** `templates/web/components/top_nav.html`

```html
<!-- Replace rocket icon with warm gradient badge -->
<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-pink-500
            flex items-center justify-center">
  <span class="font-bold text-white text-sm">T</span>
</div>
```

**Acceptance Criteria:**
- [ ] Logo displays warm gradient (coral to pink)
- [ ] Visible on both desktop and mobile nav
- [ ] Maintains proper sizing and alignment

#### 1.3 Verify Existing Design System Classes

The design-system.css already has `.app-sidebar-item-active` with correct warm styling. Verify these classes are being used or add override for DaisyUI.

---

### Phase 2: Chart Theme Creation (Stage 8)

#### 2.1 Create Chart Theme File

Create centralized theme configuration.

**File:** `assets/javascript/dashboard/chart-theme.js`

```javascript
/**
 * Tformance Chart.js Theme
 * "Sunset Dashboard" warm color palette
 */
export const TformanceChartTheme = {
  // Chart colors - warm palette
  colors: {
    primary: '#F97316',     // Coral orange - main data
    secondary: '#FDA4AF',   // Warm rose - secondary data
    success: '#2DD4BF',     // Teal - positive metrics
    warning: '#FBBF24',     // Amber - warning states
    error: '#F87171',       // Soft red - negative metrics
    ai: '#C084FC',          // Soft purple - AI-related
    muted: '#A3A3A3',       // Neutral gray
  },

  // Dataset styling
  bar: {
    backgroundColor: 'rgba(249, 115, 22, 0.7)',   // primary with opacity
    borderColor: '#F97316',
    borderWidth: 1,
    borderRadius: 4,
    hoverBackgroundColor: 'rgba(249, 115, 22, 0.9)',
  },

  line: {
    backgroundColor: 'rgba(249, 115, 22, 0.1)',
    borderColor: '#F97316',
    borderWidth: 2,
    tension: 0.3,
    fill: true,
  },

  // Grid styling
  grid: {
    color: 'rgba(163, 163, 163, 0.1)',  // muted with low opacity
    borderColor: '#404040',              // elevated
  },

  // Axis labels
  axis: {
    color: '#A3A3A3',        // muted text
    titleColor: '#D4D4D4',   // neutral-300
  },

  // Tooltip styling
  tooltip: {
    backgroundColor: '#262626',  // surface
    borderColor: '#404040',      // elevated
    titleColor: '#FAFAFA',       // neutral-50
    bodyColor: '#D4D4D4',        // neutral-300
    borderWidth: 1,
    cornerRadius: 8,
    padding: 12,
  },

  // Legend styling
  legend: {
    color: '#D4D4D4',  // neutral-300
  },
};

// Color palette for multi-series charts
export const chartColorPalette = [
  '#F97316',  // primary - coral orange
  '#2DD4BF',  // success - teal
  '#C084FC',  // AI - purple
  '#FDA4AF',  // secondary - rose
  '#FBBF24',  // warning - amber
  '#60A5FA',  // info - blue
];

// Helper to get chart defaults
export function getChartDefaults() {
  return {
    responsive: true,
    plugins: {
      legend: {
        labels: {
          color: TformanceChartTheme.legend.color,
        },
      },
      tooltip: {
        backgroundColor: TformanceChartTheme.tooltip.backgroundColor,
        titleColor: TformanceChartTheme.tooltip.titleColor,
        bodyColor: TformanceChartTheme.tooltip.bodyColor,
        borderColor: TformanceChartTheme.tooltip.borderColor,
        borderWidth: TformanceChartTheme.tooltip.borderWidth,
        cornerRadius: TformanceChartTheme.tooltip.cornerRadius,
        padding: TformanceChartTheme.tooltip.padding,
      },
    },
    scales: {
      x: {
        ticks: { color: TformanceChartTheme.axis.color },
        title: { color: TformanceChartTheme.axis.titleColor },
        grid: { color: TformanceChartTheme.grid.color },
      },
      y: {
        ticks: { color: TformanceChartTheme.axis.color },
        title: { color: TformanceChartTheme.axis.titleColor },
        grid: { color: TformanceChartTheme.grid.color },
      },
    },
  };
}
```

**Acceptance Criteria:**
- [ ] Theme file created with all color tokens
- [ ] Exports theme object and helper functions
- [ ] Colors match design system

#### 2.2 Update Dashboard Charts

Apply theme to `dashboard-charts.js`.

**File:** `assets/javascript/dashboard/dashboard-charts.js`

Update `weeklyBarChart` and other functions to use theme colors.

**Acceptance Criteria:**
- [ ] `weeklyBarChart` uses `TformanceChartTheme.bar` styles
- [ ] Grid and axis colors match theme
- [ ] Tooltip styling applied

#### 2.3 Verify Chart Rendering

Test all chart instances on CTO dashboard.

**Acceptance Criteria:**
- [ ] AI Adoption chart uses coral orange
- [ ] Cycle Time chart uses coral orange
- [ ] Copilot Trend chart uses purple (AI-related)
- [ ] Tooltips have dark surface background
- [ ] Grid lines are subtle

---

## Detailed Task Breakdown

### Stage 6 Tasks

| # | Task | Effort | Dependencies |
|---|------|--------|--------------|
| 6.1 | Add DaisyUI menu-active override to design-system.css | S | None |
| 6.2 | Update logo gradient in top_nav.html | S | None |
| 6.3 | Add hover state styling for menu items | S | 6.1 |
| 6.4 | Test navigation on mobile (drawer menu) | S | 6.1-6.3 |
| 6.5 | Run e2e-auth tests | S | 6.1-6.4 |

### Stage 8 Tasks

| # | Task | Effort | Dependencies |
|---|------|--------|--------------|
| 8.1 | Create chart-theme.js with color tokens | M | None |
| 8.2 | Update weeklyBarChart in dashboard-charts.js | S | 8.1 |
| 8.3 | Update barChartWithDates function | S | 8.1 |
| 8.4 | Update cumulativeChartWithDates function | S | 8.1 |
| 8.5 | Apply AI-specific purple to Copilot chart | S | 8.2 |
| 8.6 | Run npm build and verify no errors | S | 8.1-8.5 |
| 8.7 | Run e2e-dashboard tests | S | 8.6 |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| DaisyUI override conflicts | Medium | Low | Test with both DaisyUI defaults and custom classes |
| Chart.js version incompatibility | Low | Medium | Use Chart.js 4.x compatible API |
| Mobile nav styling issues | Medium | Low | Test responsive breakpoints |
| Color contrast accessibility | Low | High | All colors already WCAG AA verified |

---

## Validation Steps

### Build Validation
```bash
# Build CSS and JS
npm run build

# Check for build errors
echo $?  # Should be 0
```

### E2E Test Validation
```bash
# Run auth tests (includes navigation)
make e2e-auth

# Run dashboard tests (includes charts)
make e2e-dashboard

# Full suite
make e2e
```

### Visual Checklist
- [ ] Sidebar active item shows coral orange highlight
- [ ] Logo has warm gradient (coral to pink)
- [ ] Charts render with coral orange bars
- [ ] Copilot chart uses purple (AI theme)
- [ ] Tooltips have dark background
- [ ] No broken layouts or missing styles

---

## Success Metrics

1. **All E2E tests pass**: `make e2e-auth` and `make e2e-dashboard` succeed
2. **No build errors**: `npm run build` completes successfully
3. **Visual consistency**: All navigation and charts use warm color palette
4. **Performance**: No bundle size increase > 1KB from chart theme

---

## Files to Modify

| File | Changes |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | Add menu-active override |
| `templates/web/components/top_nav.html` | Update logo gradient |
| `assets/javascript/dashboard/chart-theme.js` | NEW - Create theme |
| `assets/javascript/dashboard/dashboard-charts.js` | Import and apply theme |
| `assets/javascript/app.js` | Optionally pass chart-specific colors |

---

## Related Documentation

- Master plan: `dev/visual-improvement-plan.md`
- Color mappings: `dev/active/visual-stage-1/visual-stage-1-context.md`
- Design system: `assets/styles/app/tailwind/design-system.css`
- CLAUDE.md: Design System section
