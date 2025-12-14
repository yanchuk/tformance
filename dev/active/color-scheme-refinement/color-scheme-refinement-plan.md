# Color Scheme Refinement - Implementation Plan

Last Updated: 2025-12-14

## Executive Summary

Refine the tformance color scheme to be less "acid" (harsh/vibrant) and more professional/subdued. Implement centralized color management and add automated accessibility testing using Playwright + axe-core.

## Current State Analysis

### Color Management Architecture

The application uses a **multi-layered color system**:

| Layer | File | Purpose |
|-------|------|---------|
| DaisyUI Theme | `site-tailwind.css` | Semantic colors via `data-theme="dark"` |
| Custom Colors | `tailwind.config.js` | Landing page colors (deep, surface, cyan) |
| Design System | `design-system.css` | App-specific utility classes |
| Pegasus Legacy | `pegasus/tailwind.css` | Helper classes from boilerplate |

### Current Theme Issues

1. **DaisyUI "dark" theme** - Uses default colors which can feel harsh
2. **Cyan accent (#06b6d4)** - Vibrant cyan is prominent throughout
3. **Color inconsistency** - Mix of DaisyUI semantic colors and hardcoded values
4. **No centralized theme** - Colors defined in multiple places

### Files Using Colors

```
templates/web/base.html         → data-theme="dark"
templates/web/surveys/base.html → data-theme="dark"
design-system.css               → Hardcoded slate + cyan
tailwind.config.js              → Custom color definitions
```

## Proposed Future State

### 1. Centralized Color Management

Define a **custom DaisyUI theme** that:
- Inherits from a softer base theme (nord, business, or custom)
- Overrides only what's needed for brand consistency
- Is defined in ONE place (`site-tailwind.css`)

### 2. Refined Color Palette

**Option A: Nord-Inspired (Recommended)**
- Cooler, muted tones based on Nord palette
- Professional without being sterile
- Excellent accessibility out of the box

**Option B: Business Theme**
- DaisyUI's built-in business theme
- Corporate feel, high contrast
- Minimal customization needed

**Option C: Custom Theme**
- Create entirely custom theme
- Maximum control but more effort
- Based on slate + softer teal accent

### 3. Accessibility Testing

- Add `@axe-core/playwright` for automated WCAG testing
- Create accessibility test fixtures
- Test critical user flows for contrast/readability

## Implementation Phases

### Phase 1: Audit & Planning (Effort: S)

1. Visual audit of current color usage
2. Document all color-related CSS classes in use
3. Decide on theme direction (nord vs business vs custom)
4. Create color token mapping

### Phase 2: Theme Implementation (Effort: M)

1. Create custom DaisyUI theme definition
2. Update `tailwind.config.js` custom colors
3. Update `design-system.css` to use semantic colors
4. Update `data-theme` attribute across templates

### Phase 3: Cleanup & Consolidation (Effort: M)

1. Remove hardcoded color values from templates
2. Migrate pegasus legacy colors to new theme
3. Update Chart.js chart colors
4. Update any inline styles

### Phase 4: Accessibility Testing (Effort: M)

1. Install `@axe-core/playwright`
2. Create accessibility test fixtures
3. Add WCAG 2.1 AA compliance tests
4. Fix any accessibility violations

### Phase 5: Documentation & Review (Effort: S)

1. Document color system usage
2. Create color palette reference
3. Visual QA across all pages
4. Team review of changes

## Technical Implementation Details

### Custom Theme Definition

```css
/* site-tailwind.css */
@plugin "daisyui/theme" {
  name: "tformance";
  default: true;
  prefersdark: true;
  color-scheme: dark;

  /* Base colors - softer slate */
  --color-base-100: oklch(0.15 0.01 260);   /* Deep background */
  --color-base-200: oklch(0.18 0.01 260);   /* Card background */
  --color-base-300: oklch(0.22 0.01 260);   /* Elevated */
  --color-base-content: oklch(0.90 0.01 260); /* Text */

  /* Primary - softer teal instead of acid cyan */
  --color-primary: oklch(0.65 0.12 195);    /* Muted teal */
  --color-primary-content: oklch(0.15 0.01 260);

  /* Secondary - subtle */
  --color-secondary: oklch(0.55 0.08 260);
  --color-secondary-content: oklch(0.95 0.01 260);

  /* Accent - warm to balance cool tones */
  --color-accent: oklch(0.70 0.12 60);      /* Warm amber */
  --color-accent-content: oklch(0.15 0.01 260);

  /* Status colors - muted but distinct */
  --color-success: oklch(0.65 0.15 145);
  --color-warning: oklch(0.75 0.15 70);
  --color-error: oklch(0.60 0.18 25);
  --color-info: oklch(0.65 0.10 230);
}
```

### Accessibility Test Setup

```typescript
// tests/e2e/accessibility.spec.ts
import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test.describe('Accessibility Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto('/accounts/login/');
    await page.fill('[name="login"]', 'admin@example.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
  });

  test('app home page has no WCAG 2.1 AA violations', async ({ page }) => {
    await page.goto('/app/');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });

  test('team dashboard has no accessibility violations', async ({ page }) => {
    await page.goto('/app/metrics/dashboard/team/');
    await page.waitForLoadState('networkidle');
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa'])
      .analyze();
    expect(results.violations).toEqual([]);
  });
});
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Color changes break visual design | Medium | High | Visual QA checklist, screenshots before/after |
| Accessibility regressions | Low | High | Automated axe-core tests |
| Template updates miss files | Medium | Medium | Grep audit of all color usage |
| Chart.js colors not updated | Medium | Low | Separate chart color config |
| Team dislikes new palette | Medium | Medium | Review before deployment |

## Success Metrics

- [ ] Single source of truth for all colors (DaisyUI theme)
- [ ] No hardcoded hex values in templates
- [ ] All accessibility tests passing (WCAG 2.1 AA)
- [ ] Contrast ratio >= 4.5:1 for normal text
- [ ] Contrast ratio >= 3:1 for large text
- [ ] Visual approval from stakeholders

## Required Resources

- **Package**: `@axe-core/playwright` (npm)
- **Reference**: [DaisyUI Theme Customization](https://daisyui.com/docs/themes/)
- **Reference**: [Playwright Accessibility Testing](https://playwright.dev/docs/accessibility-testing)
- **Tool**: [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/)

## Timeline Estimation

| Phase | Effort |
|-------|--------|
| Phase 1: Audit & Planning | S |
| Phase 2: Theme Implementation | M |
| Phase 3: Cleanup & Consolidation | M |
| Phase 4: Accessibility Testing | M |
| Phase 5: Documentation & Review | S |

## Dependencies

- DaisyUI 5.x (already installed)
- Playwright (already installed)
- @axe-core/playwright (to be installed)
