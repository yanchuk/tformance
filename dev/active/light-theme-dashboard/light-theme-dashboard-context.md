# Light Theme Dashboard - Context Document

**Last Updated:** 2025-12-20 (Session 5 - Dark Mode Toggle Added)

## Current Status

**Progress: 100% Complete ✅ + Dark Mode Toggle**

### Implementation Complete
- ✅ tformance-light theme created and applied to all app pages
- ✅ Design system fully theme-aware (auto-adapts to light/dark)
- ✅ Chart.js colors adapt to light/dark theme
- ✅ All chart/table partials use theme-aware classes
- ✅ Dashboard home, Analytics, Integrations pages tested
- ✅ Responsive layouts verified (desktop, tablet, mobile)
- ✅ Focus states verified for accessibility
- ✅ All DaisyUI components automatically adapt
- ✅ Dark mode toggle for app pages (Light/Dark/System options)

### Commits Made
- `7b82105` - Add tformance-light theme for internal dashboard
- `90f60cf` - Make design system theme-aware for light/dark support
- `2a8075e` - Fix hardcoded colors in chart/table partials
- `405c6cd` - Add light theme support to Chart.js
- `11c85d0` - Fix hardcoded colors in empty_state.html
- `29e2a33` - Add dark mode toggle with syncDarkMode function
- `d47f459` - Fix z-index and auth-only display

### Ready for Production
This task is complete. Move documentation to `dev/completed/` when merging to main.

---

## Purpose

This document captures key context, decisions, and dependencies for the light theme dashboard implementation. Use this to quickly get up to speed when resuming work.

---

## Design Decision

### Why Light Theme?

User feedback indicated the current dark dashboard feels "too dark" and lacks the warmth of the homepage. Inspired by:

1. **Fizzy.do** - Light cream background, colorful accents, playful
2. **Yandex** - Clean white with warm coral/orange (similar to our brand color)

### Key Design Principles

1. **Light background** - Warm off-white (#FAFAF8), not pure white
2. **Keep warm accents** - Coral orange (#F97316) remains primary brand color
3. **Colorful data** - Charts and metrics should be vibrant
4. **WCAG AA compliant** - All text must meet 4.5:1 contrast ratio

---

## Key Files

### Theme Configuration
```
assets/styles/site-tailwind.css        # DaisyUI theme definitions
assets/styles/app/tailwind/design-system.css  # Custom utility classes
tailwind.config.js                      # Color tokens
```

### Base Templates
```
templates/web/base.html                 # Marketing pages (KEEP DARK)
templates/web/app/app_base.html         # App pages (CHANGE TO LIGHT)
```

### Dashboard Templates
```
templates/web/app_home.html             # Dashboard home
templates/metrics/team_dashboard.html   # Main metrics dashboard
templates/metrics/cto_overview.html     # CTO view
templates/metrics/partials/*.html       # 16 partial templates
```

### Navigation Components
```
templates/web/components/app_nav.html           # Sidebar
templates/web/components/top_nav_app.html       # Top nav
templates/web/components/app_nav_menu_items.html
```

### Integration Templates
```
templates/integrations/jira_projects_list.html
templates/integrations/jira_select_site.html
templates/integrations/slack_settings.html
```

---

## Color Palette Reference

### Light Theme ("tformance-light")

| Token | Value | Hex | Usage |
|-------|-------|-----|-------|
| base-100 | warm off-white | #FAFAF8 | Main background |
| base-200 | white | #FFFFFF | Cards, panels |
| base-300 | light gray | #E5E7EB | Borders |
| base-content | dark gray | #1F2937 | Primary text |
| primary | coral orange | #F97316 | CTAs, brand |
| secondary | warm rose | #FDA4AF | Highlights |
| accent | emerald | #10B981 | Success |
| warning | amber | #F59E0B | Caution |
| error | red | #EF4444 | Errors |
| info | blue | #3B82F6 | Informational |

### Text Colors for Light Background

| Purpose | Color | Contrast Ratio |
|---------|-------|----------------|
| Primary text | #1F2937 | 13:1 on #FAFAF8 |
| Secondary text | #6B7280 | 5.3:1 on #FAFAF8 |
| Muted text | #9CA3AF | 3.5:1 (use only for decorative) |

---

## Current Theme Structure

The existing dark theme is defined in `site-tailwind.css`:

```css
@plugin "daisyui/theme" {
  name: "tformance";
  default: true;
  prefersdark: true;
  color-scheme: dark;

  --color-base-100: oklch(0.145 0 0);  /* #171717 */
  --color-base-200: oklch(0.185 0 0);  /* #262626 */
  /* ... etc */
}
```

The new light theme will follow the same structure:

```css
@plugin "daisyui/theme" {
  name: "tformance-light";
  color-scheme: light;

  --color-base-100: oklch(0.98 0.005 90);  /* #FAFAF8 */
  --color-base-200: oklch(1 0 0);           /* #FFFFFF */
  /* ... etc */
}
```

---

## Template Theme Switching

### How to Apply Light Theme

In `app_base.html`, set the theme on the HTML element:

```html
<html data-theme="tformance-light">
```

This will automatically apply all DaisyUI component colors.

### Keeping Marketing Dark

`base.html` continues to use:
```html
<html data-theme="tformance">
```

---

## Chart.js Considerations

Charts need updated colors for light backgrounds:

### Current (Dark Theme)
```javascript
const colors = {
  primary: '#F97316',    // Coral orange
  grid: 'rgba(255,255,255,0.1)',
  text: '#FAFAFA',
}
```

### New (Light Theme)
```javascript
const colors = {
  primary: '#F97316',    // Keep same
  grid: 'rgba(0,0,0,0.1)',
  text: '#1F2937',
}
```

---

## Screenshots for Reference

Reference screenshots saved in `.playwright-mcp/`:
- `homepage-baseline.png` - Current homepage (dark, warm)
- `dashboard-main.png` - Current dashboard (too dark)
- `fizzy-do-homepage.png` - Design inspiration (light, colorful)
- `yandex-homepage.png` - Design inspiration (light, coral accent)

---

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| Tailwind CSS | v4 | Utility classes |
| DaisyUI | latest | Component library |
| Chart.js | 4.x | Data visualization |

---

## Related Documentation

- `CLAUDE.md` - Design System section
- `dev/visual-improvement-plan.md` - Original visual design plan
- `prd/DASHBOARDS.md` - Dashboard requirements

---

## Open Questions

1. Should surveys also use light theme? (Probably yes)
2. ~~Do we need a theme toggle for users?~~ **DONE** - Toggle implemented for app pages
3. Should charts use exact same colors or optimized for light? (Optimized)

---

## Session History

### Session 2 (2025-12-20)

**Key Technical Approach:**
The most effective fix was making `design-system.css` fully theme-aware rather than updating individual templates. By replacing hardcoded colors with DaisyUI theme variables, all components automatically adapt to the theme.

**Color Replacements Made:**
```css
/* Background mappings */
bg-surface → bg-base-200
bg-deep → bg-base-100
bg-elevated → bg-base-300

/* Border mappings */
border-elevated → border-base-300

/* Text mappings */
text-neutral-100 → text-base-content
text-neutral-200 → text-base-content/80
text-neutral-300 → text-base-content/60
text-neutral-400 → text-base-content/50

/* Accent mappings */
text-accent-primary → text-primary
```

**Template Fixes:**
- `integrations/home.html` - Replaced `text-slate-*` with `text-base-content/*`

**Screenshots Taken:**
- `dashboard-light-nav-check.png` - Verified nav styling
- `integrations-light-check.png` - Found dark card issue
- `integrations-light-theme-fixed.png` - Verified fix
- `dashboard-light-theme-v2.png` - Analytics page working

### User Product Feedback (Captured)

User provided feedback for future features (not current scope):
1. **Benchmarks needed**: "I see numbers and I don't know if it's good or bad" - wants industry comparisons
2. **More guidance**: Weekly checklists, action items, metrics change summaries

### Session 4 (2025-12-20) - Final Session

**Phase 7 Completed:**
1. **Responsive Testing**
   - Tested at 1920px (desktop), 768px (tablet), 375px (mobile)
   - Dashboard home: Stats grid adapts from 4→2→1 columns
   - Analytics: Charts stack properly on smaller screens
   - Integrations: Cards in 2-column grid on tablet, single column mobile
   - Sidebar collapses to hamburger menu on mobile/tablet

2. **Accessibility Verified**
   - Focus states visible on all interactive elements
   - Tab navigation works correctly
   - DaisyUI ensures proper contrast ratios
   - `text-base-content` on `#FAFAF8` background exceeds 4.5:1

3. **Screenshots Saved**
   - All saved in `.playwright-mcp/` directory
   - Desktop, tablet, mobile for each major page
   - Focus state verification screenshots

**Task Complete - Ready for Production**

### Session 5 (2025-12-20) - Dark Mode Toggle

**Feature Added: Theme Toggle for App Pages**

User requested ability to switch between light/dark themes. Implementation:

1. **Files Created/Modified:**
   - `assets/javascript/theme.js` (NEW) - `syncDarkMode()` function
   - `assets/javascript/site.js` - Added theme import
   - `templates/web/base.html` - Flash prevention inline script
   - `templates/web/components/top_nav.html` - Toggle include (auth-only)
   - `templates/web/components/dark_mode_selector.html` - Fixed z-index (z-1 → z-50)

2. **Design Decision:**
   - Marketing pages remain dark-only (hardcoded `bg-deep`, `text-slate-*` throughout)
   - Toggle only shows for authenticated users (app pages)
   - Making marketing theme-aware would require updating ~10 component templates

3. **How It Works:**
   - localStorage stores theme preference ('tformance', 'tformance-light', or 'system')
   - Inline script in `<head>` prevents flash on page load
   - `syncDarkMode()` applies theme and listens for system preference changes
   - Pre-existing `dark_mode_selector.html` component handles UI

4. **Commits:**
   - `29e2a33` - Add dark mode toggle with syncDarkMode function
   - `d47f459` - Fix z-index and auth-only display

**Screenshots:**
- `dashboard-dark-theme.png` - Dark theme on dashboard
- `dashboard-light-theme.png` - Light theme on dashboard
