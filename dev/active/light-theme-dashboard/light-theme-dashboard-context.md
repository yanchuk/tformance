# Light Theme Dashboard - Context Document

**Last Updated:** 2025-12-20 (Session 2 continued)

## Current Status

**Progress: ~60% Complete**

### What's Working
- ✅ tformance-light theme created and applied to app pages
- ✅ Design system fully theme-aware (auto-adapts to light/dark)
- ✅ Dashboard home page clean and professional
- ✅ Navigation sidebar properly themed
- ✅ Analytics/CTO overview page working
- ✅ Integration cards match light theme
- ✅ All DaisyUI components automatically adapt

### What Needs Work
- ⏳ Chart.js colors need light-theme optimization
- ⏳ Some table partials may have hardcoded colors
- ⏳ Jira/Slack settings pages not reviewed
- ⏳ Setup wizard components not tested
- ⏳ Full accessibility audit pending

### Recent Commits
- `7b82105` - Add tformance-light theme for internal dashboard
- `90f60cf` - Make design system theme-aware for light/dark support

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
2. Do we need a theme toggle for users? (Probably not for MVP)
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
