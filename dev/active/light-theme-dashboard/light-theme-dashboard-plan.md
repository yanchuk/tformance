# Light Theme Dashboard Implementation Plan

**Last Updated:** 2025-12-20

## Executive Summary

Transform the internal dashboard from a dark theme to a light, warm, colorful theme inspired by Fizzy.do and classic Yandex design. The homepage (marketing) will remain dark while all authenticated app pages switch to a light theme with warm coral/orange accents.

### Goals
1. Create a friendlier, more approachable dashboard experience
2. Improve readability and reduce eye strain during extended use
3. Maintain brand consistency with warm coral orange (#F97316) accents
4. Ensure WCAG AA accessibility compliance

### Inspiration Sources
- **Fizzy.do** - Light cream background, colorful accents, playful feel
- **Yandex** - Clean white/cream with warm coral/orange accents
- **Linear** - Professional light theme with colorful data visualization

---

## Current State Analysis

### Theme Architecture
- **Current setup**: Single "tformance" DaisyUI theme (dark)
- **Location**: `assets/styles/site-tailwind.css`
- **Design system**: `assets/styles/app/tailwind/design-system.css`

### Template Structure
| Area | Template Base | Theme Needed |
|------|---------------|--------------|
| Marketing (homepage) | `web/base.html` | Dark (keep) |
| Dashboard | `web/app/app_base.html` | Light (new) |
| Metrics | `metrics/team_dashboard.html` | Light (new) |
| Integrations | `integrations/*.html` | Light (new) |
| Surveys | `web/surveys/base.html` | Light (new) |

### Files Requiring Updates

**CSS/Theme Files:**
- `assets/styles/site-tailwind.css` - Add new light theme
- `assets/styles/app/tailwind/design-system.css` - Add light variants

**Base Templates:**
- `templates/web/app/app_base.html` - Switch to light theme
- `templates/web/base.html` - Keep dark (marketing)

**Dashboard Templates (12 files):**
- `templates/web/app_home.html`
- `templates/metrics/team_dashboard.html`
- `templates/metrics/cto_overview.html`
- `templates/metrics/metrics_home.html`
- `templates/metrics/partials/*.html` (16 partials)

**Component Templates:**
- `templates/web/components/app_nav.html` - Sidebar
- `templates/web/components/top_nav_app.html` - Top nav
- `templates/web/components/app_nav_menu_items.html`
- `templates/web/components/quick_stats.html`
- `templates/web/components/recent_activity.html`
- `templates/web/components/setup_wizard.html`
- `templates/web/components/setup_prompt.html`
- `templates/web/components/empty_state.html`

**Integration Templates:**
- `templates/integrations/jira_projects_list.html`
- `templates/integrations/jira_select_site.html`
- `templates/integrations/slack_settings.html`

---

## Proposed Future State

### New Color Palette: "Sunset Light"

| Token | Dark Theme | Light Theme | Usage |
|-------|------------|-------------|-------|
| `base-100` | #171717 | #FAFAF8 | Main background (warm off-white) |
| `base-200` | #262626 | #FFFFFF | Cards, panels (pure white) |
| `base-300` | #404040 | #E5E7EB | Borders, dividers |
| `base-content` | #FAFAFA | #1F2937 | Primary text (dark gray) |
| `primary` | #F97316 | #F97316 | **Keep same** - coral orange |
| `secondary` | #FDA4AF | #FDA4AF | **Keep same** - warm rose |
| `accent` | #2DD4BF | #10B981 | Emerald (better on light) |
| `success` | #2DD4BF | #10B981 | Emerald green |
| `warning` | #FBBF24 | #F59E0B | Slightly darker amber |
| `error` | #F87171 | #EF4444 | Slightly darker red |
| `info` | #60A5FA | #3B82F6 | Slightly darker blue |

### Theme Switching Strategy

```
┌─────────────────────────────────────────────────────────┐
│                    web/base.html                        │
│              data-theme="tformance" (dark)              │
│                                                         │
│  ┌─────────────────┐    ┌────────────────────────────┐ │
│  │ Landing Page    │    │ app/app_base.html          │ │
│  │ Marketing Pages │    │ data-theme="tformance-light"│ │
│  │ (dark theme)    │    │                            │ │
│  └─────────────────┘    │  ┌──────────────────────┐  │ │
│                         │  │ Dashboard            │  │ │
│                         │  │ Metrics              │  │ │
│                         │  │ Integrations         │  │ │
│                         │  │ Settings             │  │ │
│                         │  └──────────────────────┘  │ │
│                         └────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Theme Foundation (Effort: M)
Create the light theme in DaisyUI and design system.

### Phase 2: Base Templates (Effort: S)
Update app_base.html to use light theme, ensure marketing pages stay dark.

### Phase 3: Navigation Components (Effort: M)
Update sidebar, top nav, and menu components for light theme.

### Phase 4: Dashboard Home (Effort: M)
Update app_home.html, quick_stats, recent_activity, setup components.

### Phase 5: Metrics Dashboard (Effort: L)
Update team_dashboard.html and all 16 partials + Chart.js colors.

### Phase 6: Integration Pages (Effort: S)
Update integrations templates.

### Phase 7: Polish & Testing (Effort: M)
Accessibility audit, visual QA, cross-browser testing.

---

## Detailed Tasks

### Phase 1: Theme Foundation

**1.1 Create "tformance-light" DaisyUI theme**
- File: `assets/styles/site-tailwind.css`
- Add new `@plugin "daisyui/theme"` block with light colors
- Acceptance: Theme compiles without errors
- Effort: S

**1.2 Add light-mode design system classes**
- File: `assets/styles/app/tailwind/design-system.css`
- Add `.app-light-*` variants or theme-aware classes
- Acceptance: Classes work with data-theme attribute
- Effort: M

**1.3 Define Chart.js color palette for light theme**
- File: `assets/javascript/charts/theme.js` (new)
- Define colors that work on light backgrounds
- Acceptance: Charts readable on light background
- Effort: S

### Phase 2: Base Templates

**2.1 Update app_base.html to use light theme**
- File: `templates/web/app/app_base.html`
- Add `data-theme="tformance-light"` to html/body
- Acceptance: Dashboard pages render with light background
- Effort: S

**2.2 Verify marketing pages stay dark**
- File: `templates/web/base.html`
- Ensure landing page still uses dark theme
- Acceptance: Homepage unchanged
- Effort: S

### Phase 3: Navigation Components

**3.1 Update sidebar navigation**
- File: `templates/web/components/app_nav.html`
- Update colors for light theme
- Acceptance: Sidebar readable, active states visible
- Effort: S

**3.2 Update top navigation bar**
- File: `templates/web/components/top_nav_app.html`
- Update colors for light theme
- Acceptance: Top nav looks good on light
- Effort: S

**3.3 Update menu items**
- File: `templates/web/components/app_nav_menu_items.html`
- Update hover/active states
- Acceptance: Menu items have proper contrast
- Effort: S

### Phase 4: Dashboard Home

**4.1 Update app_home.html**
- File: `templates/web/app_home.html`
- Update card backgrounds, text colors
- Acceptance: Dashboard home renders correctly
- Effort: M

**4.2 Update quick_stats.html**
- File: `templates/web/components/quick_stats.html`
- Update stat card styling
- Acceptance: Stats readable with proper contrast
- Effort: S

**4.3 Update recent_activity.html**
- File: `templates/web/components/recent_activity.html`
- Update activity feed styling
- Acceptance: Activity items clear and readable
- Effort: S

**4.4 Update setup components**
- Files: `setup_wizard.html`, `setup_prompt.html`, `empty_state.html`
- Update for light theme
- Acceptance: Setup flows look correct
- Effort: S

### Phase 5: Metrics Dashboard

**5.1 Update team_dashboard.html**
- File: `templates/metrics/team_dashboard.html`
- Update main container and card styling
- Acceptance: Dashboard structure correct
- Effort: M

**5.2 Update key_metrics_cards.html**
- File: `templates/metrics/partials/key_metrics_cards.html`
- Update metric card styling
- Acceptance: Metric cards readable
- Effort: S

**5.3 Update all chart partials**
- Files: `cycle_time_chart.html`, `review_time_chart.html`, `pr_size_chart.html`, etc.
- Update Chart.js configurations for light theme
- Acceptance: Charts have proper colors for light bg
- Effort: L

**5.4 Update all table partials**
- Files: `leaderboard_table.html`, `recent_prs_table.html`, etc.
- Update table styling
- Acceptance: Tables readable with proper row contrast
- Effort: M

**5.5 Update cto_overview.html**
- File: `templates/metrics/cto_overview.html`
- Update CTO dashboard styling
- Acceptance: CTO view renders correctly
- Effort: M

### Phase 6: Integration Pages

**6.1 Update Jira integration pages**
- Files: `jira_projects_list.html`, `jira_select_site.html`
- Update for light theme
- Acceptance: Jira pages render correctly
- Effort: S

**6.2 Update Slack settings page**
- File: `templates/integrations/slack_settings.html`
- Update for light theme
- Acceptance: Slack settings render correctly
- Effort: S

### Phase 7: Polish & Testing

**7.1 Accessibility audit**
- Run contrast checker on all pages
- Verify 4.5:1 ratio for text
- Acceptance: All text meets WCAG AA
- Effort: M

**7.2 Visual QA**
- Screenshot all pages
- Compare with design goals
- Acceptance: Consistent visual style
- Effort: M

**7.3 Cross-browser testing**
- Test Chrome, Firefox, Safari
- Acceptance: Renders correctly in all browsers
- Effort: S

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Chart colors hard to read | Medium | High | Pre-define color palette, test early |
| CSS specificity conflicts | Medium | Medium | Use theme-aware selectors properly |
| Missed template updates | Low | Medium | Systematic file audit, visual QA |
| Accessibility regressions | Low | High | Run contrast checks on every component |

---

## Success Metrics

1. **Visual consistency**: All internal pages use light theme
2. **Accessibility**: All text meets WCAG AA (4.5:1 contrast)
3. **User feedback**: Dashboard feels friendlier and easier to read
4. **No regressions**: Marketing pages unchanged, all features work

---

## Dependencies

- Tailwind CSS v4
- DaisyUI plugin
- Chart.js (for data visualization colors)
- No external dependencies needed

---

## Estimated Total Effort

| Phase | Effort | Description |
|-------|--------|-------------|
| Phase 1 | M | Theme foundation |
| Phase 2 | S | Base templates |
| Phase 3 | M | Navigation |
| Phase 4 | M | Dashboard home |
| Phase 5 | L | Metrics dashboard |
| Phase 6 | S | Integrations |
| Phase 7 | M | Polish & testing |
| **Total** | **L-XL** | Full implementation |
