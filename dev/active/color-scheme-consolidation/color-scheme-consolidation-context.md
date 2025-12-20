# Color Scheme Consolidation - Context

**Last Updated:** 2025-12-20 (Session 3 - Phase 2 Complete)

## Key Files

### Color Definition Files (Modify These)

| File | Purpose |
|------|---------|
| `assets/styles/site-tailwind.css` | DaisyUI theme definitions (tformance, tformance-light) + light theme overrides |
| `assets/styles/app/tailwind/design-system.css` | Semantic component classes (app-*) |
| `tailwind.config.js` | Custom color tokens (deep, surface, elevated, accent-*) |
| `assets/styles/app/tailwind/landing-page.css` | Marketing page-specific classes, terminal always-dark styling |

### Template Files (Update to Use Semantic Classes)

#### Marketing Components (`templates/web/components/`) - COMPLETED
- `hero_terminal.html` - ✅ Updated
- `features_grid.html` - ✅ Updated
- `what_you_get.html` - ✅ Updated
- `faq.html` - ✅ Updated
- `pricing_simple.html` - ✅ Updated
- `how_it_works.html` - ✅ Updated
- `security.html` - ✅ Updated
- `built_with_you.html` - ✅ Updated
- `integrations.html` - ✅ Updated
- `data_transparency.html` - ✅ Updated
- `cta_terminal.html` - ✅ Updated
- `problem_discovery.html` - ✅ Updated
- `problem_statement.html` - ✅ Updated

#### Onboarding (`templates/onboarding/`) - PENDING
- `start.html`, `complete.html`, `select_org.html` - ~7 each
- `connect_jira.html`, `connect_slack.html`, `select_repos.html` - ~3 each

#### Account (`templates/account/`) - PENDING
- `email.html` - 4 occurrences
- `password_reset.html` - 3 occurrences
- Others - 1-2 each

#### Error Pages - PENDING
- `400.html`, `403.html`, `404.html`, `429.html`, `500.html` - 2 each

## Key Decisions Made

### 1. Easy Eyes-Inspired Dark Theme
**Decision:** Adopted warmer colors from Easy Eyes VS Code theme
**Rationale:** Reduces eye strain for developers spending long hours in dashboards
**Changes:**
- Background: `#171717` → `#1e1e1e` (softer)
- Text: Pure white → Warm beige `#d4d0c8`
- Borders: `#404040` → `#363636` (subtler)

### 2. Semantic Status Classes
**Decision:** Create `app-status-*` classes instead of hardcoded colors
**Rationale:** Theme-aware colors that work in light and dark modes
**Classes Created:**
```css
.app-status-connected { @apply text-emerald-600 dark:text-emerald-400; }
.app-status-available { @apply text-violet-600 dark:text-violet-400; }
.app-status-disconnected { @apply text-base-content/60; }
.app-status-error { @apply text-red-600 dark:text-red-400; }
```

### 3. DaisyUI Semantic Colors Over Hardcoded
**Decision:** Use DaisyUI tokens (`text-base-content`, `bg-base-100`) instead of Tailwind colors
**Rationale:** Automatically adapts to theme, easier maintenance
**Mapping:**
- `text-stone-*` → `text-base-content` with opacity variants
- `bg-deep/bg-surface` → `bg-base-100/bg-base-200`
- `border-elevated` → `border-base-300`

### 4. Terminal Always Dark (Session 3)
**Decision:** Terminal component stays dark regardless of user theme
**Rationale:** Part of brand identity, developer aesthetic
**Implementation:** Hardcoded dark colors in `landing-page.css`:
```css
.terminal-window {
  background-color: #1e1e1e;
  color: #d4d0c8;
}
.terminal-window .text-base-content { color: #d4d0c8 !important; }
.terminal-window .text-accent-primary { color: #FB923C !important; }
```

### 5. Theme Flash Prevention for All Pages (Session 3)
**Decision:** Apply theme flash prevention script to all pages, not just authenticated
**Rationale:** Eliminates flicker when navigating between Sign Up/Sign In pages
**Location:** `templates/web/base.html` line 44-51

### 6. Light Theme Accessibility Overrides (Session 3)
**Decision:** Use `!important` overrides for light theme contrast fixes
**Rationale:** DaisyUI cascade requires specificity override
**Colors Fixed:**
- `text-teal-400` → `oklch(0.45 0.15 175)`
- `text-accent-primary` → `oklch(0.50 0.18 40)`
- `text-purple-300` → `oklch(0.40 0.15 290)`
- `text-amber-400` → `oklch(0.55 0.15 80)`
- `text-accent-error` → `oklch(0.50 0.18 25)`

## Color Token Reference

### DaisyUI Theme Tokens (tformance - dark)

```css
/* Backgrounds */
--color-base-100: #1e1e1e;  /* Main background */
--color-base-200: #282725;  /* Cards, panels */
--color-base-300: #363636;  /* Borders */

/* Text */
--color-base-content: #d4d0c8;  /* Warm beige text */

/* Accents */
--color-primary: #F97316;    /* Coral orange */
--color-secondary: #FDA4AF;  /* Warm rose */
--color-accent: #2DD4BF;     /* Teal */

/* Status */
--color-success: #2DD4BF;    /* Teal */
--color-warning: #FBBF24;    /* Amber */
--color-error: #F87171;      /* Soft red */
--color-info: #60A5FA;       /* Soft blue */
```

### DaisyUI Theme Tokens (tformance-light)

```css
/* Backgrounds */
--color-base-100: #FAFAF8;   /* Warm off-white */
--color-base-200: #FFFFFF;   /* Pure white cards */
--color-base-300: #E5E7EB;   /* Light gray borders */

/* Text */
--color-base-content: #1F2937;  /* Dark gray text */

/* Primary - darker for WCAG AA */
--color-primary: #C2410C;    /* Orange-700 (4.5:1 contrast) */
```

## Semantic Class Mapping

### Text Classes

| Hardcoded | Semantic Replacement |
|-----------|---------------------|
| `text-stone-100` | `text-base-content` |
| `text-stone-200` | `text-base-content` |
| `text-stone-300` | `text-base-content/90` |
| `text-stone-400` | `text-base-content/80` |
| `text-white` | `text-base-content` (in dark contexts) |

### Background Classes

| Hardcoded | Semantic Replacement |
|-----------|---------------------|
| `bg-deep` | `bg-base-100` |
| `bg-surface` | `bg-base-200` |
| `bg-neutral-900` | `bg-base-100` |
| `bg-neutral-800` | `bg-base-200` |

### Border Classes

| Hardcoded | Semantic Replacement |
|-----------|---------------------|
| `border-elevated` | `border-base-300` |
| `border-neutral-700` | `border-base-300` |

### Status Classes

| Hardcoded | Semantic Replacement |
|-----------|---------------------|
| `text-emerald-400` | `app-status-connected` |
| `text-violet-400` | `app-status-available` |
| `text-red-400` | `app-status-error` or `text-error` |
| `text-amber-400` | `text-warning` |

## Dependencies

- **DaisyUI 5.x** - Theme system
- **Tailwind CSS 4.x** - Utility classes
- **Playwright + axe-core** - Accessibility testing

## Testing Commands

```bash
# Run accessibility tests
npx playwright test accessibility.spec.ts

# Check for hardcoded colors (after creating linter)
make lint-colors

# View in browser
open http://localhost:8000/
```

## Related Documentation

- CLAUDE.md Design System section (updated Session 3)
- Color tokens: `assets/styles/app/tailwind/design-system.css` (header comments)

---

## Session 3 Progress (2025-12-20)

### Completed This Session

1. **Phase 2: Marketing Pages Refactor** - COMPLETE
   - Updated 13 marketing templates replacing `stone-*` with `text-base-content` variants
   - All templates now use semantic DaisyUI colors

2. **Terminal Always-Dark Styling**
   - Added hardcoded dark colors in `landing-page.css`
   - Overrides theme-aware classes inside terminal
   - Verdict line uses lighter orange (#FB923C) vs prompt (#F97316)

3. **Theme Toggle for All Users**
   - Moved dark mode selector outside auth check in `top_nav.html`
   - Added `gap-2` spacing between header elements

4. **Theme Flash Prevention**
   - Extended theme flash script to all pages (not just authenticated)
   - Eliminates flicker on Sign Up ↔ Sign In navigation

5. **Button Border Visibility**
   - Changed "See How It Works" button border from `border-base-300` to `border-base-content/30`

6. **Light Theme Accessibility Overrides**
   - Added 5 new contrast fixes in `site-tailwind.css`
   - All 9 accessibility tests passing

7. **CLAUDE.md Documentation**
   - Updated with consolidated color system guidelines
   - Added color usage rules table
   - Added DaisyUI theme tokens reference

### Key Decisions This Session

1. **Terminal components always dark** - Use hardcoded colors, not theme-aware
2. **Theme flash prevention for all users** - Not just authenticated
3. **Verdict line lighter orange** - #FB923C (orange-400) vs #F97316 (orange-500) for prompt
4. **Button borders use content-based opacity** - `border-base-content/30` more visible than `border-base-300`

### Files Modified This Session

| File | Changes |
|------|---------|
| `assets/styles/app/tailwind/landing-page.css` | Terminal always-dark styling (55 lines) |
| `assets/styles/site-tailwind.css` | Light theme accessibility overrides (+30 lines) |
| `templates/web/base.html` | Theme flash prevention for all pages |
| `templates/web/components/top_nav.html` | Theme toggle for all users + gap-2 |
| `templates/web/components/hero_terminal.html` | Button border visibility |
| `templates/web/components/faq.html` | stone-* → text-base-content |
| `templates/web/components/what_you_get.html` | stone-* → text-base-content |
| `templates/web/components/features_grid.html` | stone-* → text-base-content |
| `templates/web/components/pricing_simple.html` | stone-* → text-base-content |
| `templates/web/components/how_it_works.html` | stone-* → text-base-content |
| `templates/web/components/security.html` | stone-* → text-base-content |
| `templates/web/components/built_with_you.html` | stone-* → text-base-content |
| `templates/web/components/data_transparency.html` | stone-* → text-base-content |
| `templates/web/components/cta_terminal.html` | stone-* → text-base-content |
| `templates/web/components/problem_discovery.html` | stone-* → text-base-content |
| `templates/web/components/problem_statement.html` | stone-* → text-base-content |
| `templates/web/components/integrations.html` | stone-* → text-base-content |
| `CLAUDE.md` | Color system guidelines update |

### Commits This Session

```
35484fd Phase 2: Consolidate marketing page colors with semantic classes
515b941 Fix theme flicker on page navigation for all users
2e4d409 Update CLAUDE.md with consolidated color system guidelines
```

### Next Session: Phase 3

**Goal:** Update app pages (dashboard, integrations, team management) with semantic classes.

**Priority files:**
1. `templates/metrics/partials/` - Dashboard tables and cards
2. `templates/teams/` - Team management
3. `templates/integrations/` - Integration settings (partially done)

**Testing:**
```bash
make test                              # Ensure no regressions
npx playwright test accessibility.spec.ts  # Contrast checks
```
