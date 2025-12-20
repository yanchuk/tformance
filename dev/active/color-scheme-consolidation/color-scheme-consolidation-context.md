# Color Scheme Consolidation - Context

**Last Updated:** 2025-12-20 (Session 2 - Phase 1 Complete)

## Key Files

### Color Definition Files (Modify These)

| File | Purpose |
|------|---------|
| `assets/styles/site-tailwind.css` | DaisyUI theme definitions (tformance, tformance-light) |
| `assets/styles/app/tailwind/design-system.css` | Semantic component classes (app-*) |
| `tailwind.config.js` | Custom color tokens (deep, surface, elevated, accent-*) |
| `assets/styles/app/tailwind/landing-page.css` | Marketing page-specific classes |

### Template Files (Update to Use Semantic Classes)

#### Marketing Components (`templates/web/components/`)
- `hero_terminal.html` - 7 color occurrences
- `features_grid.html` - 20 occurrences
- `what_you_get.html` - 24 occurrences
- `faq.html` - 26 occurrences
- `pricing_simple.html` - 17 occurrences
- `how_it_works.html` - 14 occurrences
- `security.html` - 14 occurrences
- `built_with_you.html` - 21 occurrences
- `integrations.html` - 15 occurrences

#### Onboarding (`templates/onboarding/`)
- `start.html`, `complete.html`, `select_org.html` - ~7 each
- `connect_jira.html`, `connect_slack.html`, `select_repos.html` - ~3 each

#### Account (`templates/account/`)
- `email.html` - 4 occurrences
- `password_reset.html` - 3 occurrences
- Others - 1-2 each

#### Error Pages
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

### 3. Replace Slate with Stone
**Decision:** Use `stone` instead of `slate` for gray tones
**Rationale:** Stone is warmer (yellow undertone) vs slate (blue undertone)
**Applied To:** All marketing component templates

### 4. Opacity Standards for Contrast
**Decision:** Use `/80` opacity minimum for readable text
**Rationale:** WCAG AA requires 4.5:1 contrast; `/60` and `/70` fail with warm backgrounds
**Standard:**
- Primary text: `text-base-content` (full)
- Secondary text: `text-base-content/80`
- Muted text: `text-base-content/70` (minimum)

### 5. Marketing Pages Always Dark
**Decision:** Marketing pages don't follow user theme preference
**Rationale:** Brand consistency, dark theme is part of developer-focused identity
**Implementation:** Flash prevention script only runs for authenticated users

## Color Token Reference

### DaisyUI Theme Tokens (tformance)

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

### Custom Tailwind Tokens

```js
// tailwind.config.js
colors: {
  deep: '#1e1e1e',       // Main background
  surface: '#282725',    // Cards
  elevated: '#363636',   // Borders
  muted: '#9a9690',      // Muted text
  accent: {
    primary: '#F97316',
    secondary: '#FDA4AF',
    tertiary: '#2DD4BF',
    warning: '#FBBF24',
    error: '#F87171',
    info: '#60A5FA',
  }
}
```

## Semantic Class Mapping

### Text Classes

| Hardcoded | Semantic Replacement |
|-----------|---------------------|
| `text-stone-100` | `text-base-content` |
| `text-stone-200` | `text-base-content` |
| `text-stone-300` | `text-base-content/90` |
| `text-stone-400` | `text-base-content/70` or `app-text-muted` |
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

- Design system: `dev/visual-improvement-plan.md`
- Color tokens: `assets/styles/app/tailwind/design-system.css` (header comments)
- CLAUDE.md Design System section

---

## Session 2 Progress (2025-12-20)

### Completed This Session

1. **Phase 1: Expand Semantic Classes** - COMPLETE
   - Added marketing text classes: `app-text-hero`, `app-text-body`, `app-text-caption`, `app-text-subtle`
   - Added marketing bg classes: `app-bg-section`, `app-bg-card-dark`, `app-bg-section-bordered`
   - Added status classes: `app-status-warning`, `app-status-info`, pill variants
   - Added accent classes: `app-accent-primary`, `app-accent-secondary`, `app-accent-tertiary`

2. **Light Theme Accessibility Fixes**
   - Table header contrast override in `site-tailwind.css`
   - `text-secondary`, `text-success` darker colors for light mode
   - `app-status-pill-connected` uses `emerald-700` in light mode
   - All 9 accessibility tests now passing

3. **Template Updates**
   - Replaced `text-accent-tertiary` → `text-teal-400` in 7 marketing templates
   - Fixed navbar padding (`px-4 lg:px-6`) for sign-in button spacing

### Key Decisions This Session

1. **Use `text-teal-400` in marketing templates instead of `text-accent-tertiary`**
   - Reason: CSS specificity issues with theme overrides made `text-accent-tertiary` unreliable
   - Marketing pages are always dark, so using a direct Tailwind color works reliably
   - For app pages, use semantic classes (`app-accent-tertiary`)

2. **Light theme overrides use `!important`**
   - Required due to DaisyUI theme cascade
   - Placed at end of `site-tailwind.css` after DaisyUI plugin definitions

3. **Use `:is()` and `:where()` for specificity control**
   - Attempted but not needed after switching to `text-teal-400`
   - Keep in mind for future theme-aware overrides

### Files Modified This Session

| File | Changes |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | Added ~50 lines of new semantic classes |
| `assets/styles/site-tailwind.css` | Added light theme accessibility overrides (lines 160-176) |
| `templates/web/components/top_nav.html` | Added `px-4 lg:px-6` to navbar |
| `templates/web/components/what_you_get.html` | Replaced `text-accent-tertiary` → `text-teal-400` |
| `templates/web/components/hero_terminal.html` | Replaced `text-accent-tertiary` → `text-teal-400` |
| `templates/web/components/how_it_works.html` | Replaced `text-accent-tertiary` → `text-teal-400` |
| `templates/web/components/features_grid.html` | Replaced `text-accent-tertiary` → `text-teal-400` |
| `templates/web/components/built_with_you.html` | Replaced `text-accent-tertiary` → `text-teal-400` |
| `templates/web/components/data_transparency.html` | Replaced `text-accent-tertiary` → `text-teal-400` |
| `templates/web/components/security.html` | Replaced `text-accent-tertiary` → `text-teal-400` |

### Testing Commands

```bash
# Run accessibility tests
npx playwright test accessibility.spec.ts

# Run all tests
make test

# Check for CSS errors (start vite first)
npm run dev
```

### Next Session: Phase 2

**Goal:** Replace remaining hardcoded `stone-*` colors in marketing templates with semantic classes.

**Files to update (priority order):**
1. `faq.html` - 26 occurrences
2. `what_you_get.html` - 24 occurrences
3. `features_grid.html` - 20 occurrences
4. `pricing_simple.html` - 17 occurrences
5. `how_it_works.html` - 14 occurrences

**Mapping to use:**
```
text-stone-100 → text-base-content (or app-text-hero)
text-stone-200 → text-base-content
text-stone-300 → text-base-content/90 (or app-text-body)
text-stone-400 → text-base-content/80 (or app-text-caption)
```

### Commits This Session

```
18a871a Phase 1: Expand semantic color classes and fix accessibility
```
