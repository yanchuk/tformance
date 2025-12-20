# Visual Stages 6 & 8: Task Checklist

**Last Updated:** 2025-12-20

## Overview

Implementation checklist for Visual Stages 6 (Navigation/Sidebar) and 8 (Charts) from the Sunset Dashboard design system.

---

## Stage 6: Navigation & Sidebar

### 6.1 CSS Override for Menu Active State
- [ ] Open `assets/styles/app/tailwind/design-system.css`
- [ ] Add DaisyUI menu-active override in Navigation section (after line 313)
- [ ] Override should include:
  - [ ] `bg-deep` background
  - [ ] `text-accent-primary` text color
  - [ ] `border-l-2 border-accent-primary` left border
- [ ] Verify override uses correct DaisyUI selectors

**Code to add:**
```css
/* DaisyUI menu-active override for warm Sunset Dashboard colors */
.menu li > *:not(ul, .menu-title, details, .btn):active,
.menu li > *:not(ul, .menu-title, details, .btn).active,
.menu li > *:not(ul, .menu-title, details, .btn).menu-active,
.menu li > details > summary:active {
  @apply !bg-deep !text-accent-primary;
  @apply border-l-2 border-accent-primary;
  @apply rounded-r-lg rounded-l-none;
}

/* Menu hover states */
.menu li > *:not(ul, .menu-title, details, .btn):hover {
  @apply bg-deep/50 text-neutral-200;
}
```

### 6.2 Update Logo with Warm Gradient
- [ ] Open `templates/web/components/top_nav.html`
- [ ] Find logo element (lines 35-39, rocket icon with `text-primary`)
- [ ] Replace with warm gradient badge:

**Code to update:**
```html
<!-- Before: -->
<i class="fa-solid fa-rocket text-primary text-xl"></i>
<span class="font-bold text-2xl tracking-tight font-sans">{{project_meta.NAME|title}}</span>

<!-- After: -->
<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-pink-500
            flex items-center justify-center mr-2 shadow-lg shadow-accent-primary/20">
  <span class="font-bold text-white text-sm">T</span>
</div>
<span class="font-bold text-2xl tracking-tight font-sans">{{project_meta.NAME|title}}</span>
```

### 6.3 Update Mobile Logo (if different)
- [ ] Check mobile nav logo in same file (lines 15-20)
- [ ] Apply consistent gradient styling

### 6.4 Test Navigation
- [ ] Start dev server: `make dev`
- [ ] Navigate to dashboard as logged-in user
- [ ] Verify active menu item shows coral orange
- [ ] Verify hover states work
- [ ] Test mobile menu (resize browser or use devtools)
- [ ] Verify logo gradient displays correctly

### 6.5 Run E2E Auth Tests
- [ ] Run: `make e2e-auth`
- [ ] All tests should pass
- [ ] Check for visual regressions in test screenshots

---

## Stage 8: Charts

### 8.1 Create Chart Theme File
- [ ] Create new file: `assets/javascript/dashboard/chart-theme.js`
- [ ] Define `TformanceChartTheme` object with:
  - [ ] `colors` object (primary, success, ai, etc.)
  - [ ] `bar` styles (backgroundColor, borderColor, etc.)
  - [ ] `line` styles
  - [ ] `grid` styles
  - [ ] `axis` styles
  - [ ] `tooltip` styles
  - [ ] `legend` styles
- [ ] Export `chartColorPalette` array
- [ ] Export `getChartDefaults()` helper function

**File structure:**
```javascript
// assets/javascript/dashboard/chart-theme.js
export const TformanceChartTheme = {
  colors: {
    primary: '#F97316',
    secondary: '#FDA4AF',
    success: '#2DD4BF',
    warning: '#FBBF24',
    error: '#F87171',
    ai: '#C084FC',
    muted: '#A3A3A3',
  },
  bar: { /* ... */ },
  line: { /* ... */ },
  grid: { /* ... */ },
  tooltip: { /* ... */ },
};

export const chartColorPalette = [ /* ... */ ];
export function getChartDefaults() { /* ... */ }
```

### 8.2 Update weeklyBarChart Function
- [ ] Open `assets/javascript/dashboard/dashboard-charts.js`
- [ ] Import theme at top: `import { TformanceChartTheme, getChartDefaults } from './chart-theme';`
- [ ] Update `weeklyBarChart` function (lines 115-158):
  - [ ] Replace hardcoded cyan colors with theme
  - [ ] Add optional `options` parameter for chart-specific colors
  - [ ] Apply grid and axis styling from theme
  - [ ] Apply tooltip styling from theme

**Code changes:**
```javascript
// Before (line 128):
backgroundColor: 'rgba(94, 158, 176, 0.7)',
borderColor: 'rgba(94, 158, 176, 1)',

// After:
backgroundColor: options?.ai
  ? 'rgba(192, 132, 252, 0.7)'  // AI purple
  : TformanceChartTheme.bar.backgroundColor,
borderColor: options?.ai
  ? TformanceChartTheme.colors.ai
  : TformanceChartTheme.bar.borderColor,
```

### 8.3 Update barChartWithDates Function
- [ ] Update `barChartWithDates` function (lines 31-66)
- [ ] Apply same theme styling pattern
- [ ] Use default theme colors (no AI option needed)

### 8.4 Update cumulativeChartWithDates Function
- [ ] Update `cumulativeChartWithDates` function (lines 68-110)
- [ ] Use `TformanceChartTheme.line` styles
- [ ] Apply grid and tooltip styling

### 8.5 Apply AI Purple to Copilot Chart
- [ ] Open `assets/javascript/app.js`
- [ ] Find Copilot chart initialization (lines 54-64)
- [ ] Pass `{ ai: true }` option to weeklyBarChart:

```javascript
// Before:
AppDashboardCharts.weeklyBarChart(ctx, data, "Copilot Acceptance Rate (%)");

// After:
AppDashboardCharts.weeklyBarChart(ctx, data, "Copilot Acceptance Rate (%)", { ai: true });
```

### 8.6 Build and Verify
- [ ] Run: `npm run build`
- [ ] Check for build errors (should exit with 0)
- [ ] Check bundle size hasn't increased significantly

### 8.7 Visual Testing
- [ ] Start dev server: `make dev`
- [ ] Navigate to CTO Overview dashboard
- [ ] Verify AI Adoption chart uses coral orange
- [ ] Verify Cycle Time chart uses coral orange
- [ ] Verify Copilot Trend chart uses purple
- [ ] Check tooltip styling (dark background)
- [ ] Check grid lines are subtle

### 8.8 Run E2E Dashboard Tests
- [ ] Run: `make e2e-dashboard`
- [ ] All tests should pass
- [ ] Verify chart rendering in test output

---

## Final Validation

### Build Validation
- [ ] Run: `npm run build` - exits with 0
- [ ] Run: `make test ARGS='--keepdb'` - all tests pass

### E2E Test Suite
- [ ] Run: `make e2e-auth` - passes
- [ ] Run: `make e2e-dashboard` - passes
- [ ] Run: `make e2e` - full suite passes

### Visual Review Checklist
- [ ] Sidebar active item: coral orange text with left border
- [ ] Sidebar hover: subtle warm highlight
- [ ] Logo: coral-to-pink gradient badge
- [ ] AI Adoption chart: coral orange bars
- [ ] Cycle Time chart: coral orange bars
- [ ] Copilot Trend chart: purple bars (AI theme)
- [ ] Chart tooltips: dark surface background
- [ ] Chart grid: subtle neutral lines
- [ ] No broken layouts or missing styles
- [ ] Mobile navigation works correctly

### Performance Check
- [ ] Bundle size increase < 2KB
- [ ] No console errors or warnings
- [ ] Charts render without delay

---

## Rollback Plan

If issues arise:
1. Revert CSS changes in `design-system.css`
2. Revert template changes in `top_nav.html`
3. Delete `chart-theme.js`
4. Revert `dashboard-charts.js` to previous version
5. Run `npm run build` and `make e2e` to verify rollback

---

## Notes

- Chart theme can be extended for future chart types
- Menu override uses `!important` to ensure precedence over DaisyUI
- AI purple color (`#C084FC`) matches existing Copilot icons in cto_overview.html
- All color combinations are WCAG AA compliant (verified in context.md)
