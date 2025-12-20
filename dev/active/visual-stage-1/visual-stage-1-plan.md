# Visual Improvement Stage 1: Color Token Foundation

**Last Updated:** 2025-12-20

## Executive Summary

Stage 1 establishes the foundational color system for the "Sunset Dashboard" design direction. This involves updating Tailwind CSS configuration and DaisyUI theme to use warm coral/orange tones instead of the current cold cyan/slate palette. No template changes occur in this stage - only configuration files are modified.

**Goal:** Update color tokens so all existing components automatically inherit new warm colors through CSS custom properties and Tailwind classes.

**Risk Level:** Low - purely configuration changes with no template modifications.

---

## Current State Analysis

### Tailwind Config (`tailwind.config.js`)
Current color tokens:
- `deep: #0f172a` (slate-900) - cold blue-gray
- `surface: #1e293b` (slate-800) - cold blue-gray
- `elevated: #334155` (slate-700) - cold blue-gray
- `muted: #94a3b8` (slate-400)
- `cyan` object with DEFAULT/light/dark variants

### DaisyUI Theme (`site-tailwind.css`)
Current theme defined via `@plugin "daisyui/theme"`:
- Uses OKLCH color space
- Primary: Muted teal `oklch(0.62 0.11 195)`
- Base colors: Slate backgrounds
- Located in `assets/styles/site-tailwind.css` lines 22-62

### Color Usage Analysis
- **CSS files:** 82 occurrences of cyan/deep/surface/elevated/muted across 5 files
- **Templates:** 51 occurrences of cyan across 17 templates
- **Note:** Templates reference Tailwind classes (e.g., `text-cyan`), so updating tokens should cascade automatically

---

## Proposed Future State

### New Color Tokens (tailwind.config.js)
```javascript
colors: {
  // Warm neutral backgrounds
  deep: '#171717',        // neutral-900
  surface: '#262626',     // neutral-800
  elevated: '#404040',    // neutral-700
  muted: '#A3A3A3',       // neutral-400

  // Legacy cyan (keep for migration period)
  cyan: {
    DEFAULT: '#5e9eb0',
    light: '#7ab5c4',
    dark: '#4a8a9c',
  },

  // New accent system
  accent: {
    primary: '#F97316',   // Coral orange
    secondary: '#FDA4AF', // Warm rose
    tertiary: '#2DD4BF',  // Teal
    warning: '#FBBF24',   // Amber
    info: '#60A5FA',      // Soft blue
    error: '#F87171',     // Soft red
  },
}
```

### New DaisyUI Theme (site-tailwind.css)
```css
@plugin "daisyui/theme" {
  name: "tformance";
  default: true;
  prefersdark: true;
  color-scheme: dark;

  /* Warm neutral backgrounds */
  --color-base-100: #171717;
  --color-base-200: #262626;
  --color-base-300: #404040;
  --color-base-content: #FAFAFA;

  /* Primary - Coral orange */
  --color-primary: #F97316;
  --color-primary-content: #FFFFFF;

  /* Secondary - Warm rose */
  --color-secondary: #FDA4AF;
  --color-secondary-content: #171717;

  /* Accent - Teal */
  --color-accent: #2DD4BF;
  --color-accent-content: #171717;

  /* Neutral */
  --color-neutral: #262626;
  --color-neutral-content: #D4D4D4;

  /* Status colors */
  --color-info: #60A5FA;
  --color-success: #2DD4BF;
  --color-warning: #FBBF24;
  --color-error: #F87171;
}
```

---

## Implementation Phases

### Phase 1: Preparation (5 min)
1. Verify dev server running
2. Run baseline e2e-smoke tests
3. Take baseline screenshots (optional)

### Phase 2: Update Tailwind Config (10 min)
1. Update background colors (deep, surface, elevated)
2. Update muted color
3. Add new accent color object
4. Keep legacy cyan for backwards compatibility

### Phase 3: Update DaisyUI Theme (15 min)
1. Convert OKLCH colors to hex for clarity
2. Update primary to coral orange
3. Update secondary to warm rose
4. Update accent to teal
5. Update status colors (success, warning, error, info)
6. Update base colors to warm neutrals

### Phase 4: Validation (10 min)
1. Build CSS: `npm run build`
2. Run smoke tests: `make e2e-smoke`
3. Visual verification checklist
4. Check browser console for errors

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CSS build fails | Low | High | Validate syntax before saving |
| Color contrast issues | Medium | Medium | All colors pre-verified for WCAG AA |
| Component styling breaks | Low | Medium | Keep legacy cyan temporarily |
| E2E tests fail | Low | High | Only config changes, no selector changes |

---

## Success Metrics

1. **Build Success:** `npm run build` completes without errors
2. **E2E Pass:** `make e2e-smoke` passes (all tests green)
3. **No Console Errors:** Browser dev tools show no CSS/JS errors
4. **Visual Verification:** Pages render with new warm colors
5. **Accessibility:** All text maintains 4.5:1+ contrast ratio

---

## Rollback Plan

If issues occur:
1. Revert `tailwind.config.js` to previous state
2. Revert `assets/styles/site-tailwind.css` to previous state
3. Run `npm run build` to restore original styles
4. Git: `git checkout tailwind.config.js assets/styles/site-tailwind.css`

---

## Files Modified

| File | Changes |
|------|---------|
| `tailwind.config.js` | Update colors object with new tokens |
| `assets/styles/site-tailwind.css` | Update DaisyUI theme plugin |

---

## Dependencies

- Node.js and npm installed
- Tailwind CSS 4.x
- DaisyUI 5.x
- Dev server running for visual verification
