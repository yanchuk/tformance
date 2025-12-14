# Color Scheme Refinement - Tasks

Last Updated: 2025-12-14

## Status: COMPLETED

---

## Phase 1: Audit & Planning (Effort: S)

### 1.1 Visual Audit
- [ ] Take screenshots of all major pages (before state)
  - [ ] App Home (`/app/`)
  - [ ] Team Dashboard (`/app/metrics/dashboard/team/`)
  - [ ] CTO Dashboard (`/app/metrics/dashboard/cto/`)
  - [ ] Integrations page (`/app/integrations/`)
  - [ ] Login page (`/accounts/login/`)
  - [ ] Landing page (`/`)
- [ ] Document colors that feel "too acid" or harsh

### 1.2 Color Usage Audit
- [ ] Run grep audit for all color-related classes
  ```bash
  grep -r "cyan" assets/styles/ --include="*.css"
  grep -r "text-cyan\|bg-cyan\|border-cyan" templates/
  grep -rE "#[0-9a-fA-F]{3,6}" assets/styles/ --include="*.css"
  ```
- [ ] Create list of all hardcoded color values
- [ ] Identify Chart.js color configurations

### 1.3 Theme Decision
- [ ] Review DaisyUI built-in themes: nord, business, corporate
- [ ] Decide: Use existing theme vs create custom
- [ ] Define target color palette with hex/oklch values
- [ ] Verify color contrast ratios meet WCAG AA (4.5:1)

---

## Phase 2: Theme Implementation (Effort: M)

### 2.1 Create Custom DaisyUI Theme
- [ ] Add custom theme definition to `site-tailwind.css`
  ```css
  @plugin "daisyui/theme" {
    name: "tformance";
    /* ... */
  }
  ```
- [ ] Define base colors (base-100, base-200, base-300, base-content)
- [ ] Define primary color (softer teal instead of cyan)
- [ ] Define secondary and accent colors
- [ ] Define status colors (success, warning, error, info)
- [ ] Test theme loads correctly

### 2.2 Update Tailwind Config
- [ ] Update `tailwind.config.js` custom colors
- [ ] Change cyan to softer teal variant
- [ ] Ensure custom colors align with DaisyUI theme
- [ ] Remove redundant color definitions

### 2.3 Update HTML Templates
- [ ] Update `templates/web/base.html` data-theme
- [ ] Update `templates/web/surveys/base.html` data-theme
- [ ] Verify all templates inherit correct theme

---

## Phase 3: Cleanup & Consolidation (Effort: M)

### 3.1 Update Design System CSS
- [ ] Review `design-system.css` (571 lines)
- [ ] Replace hardcoded `text-cyan` with `text-primary`
- [ ] Replace hardcoded `bg-cyan` with `bg-primary`
- [ ] Replace hardcoded slate colors with DaisyUI semantic equivalents
- [ ] Update button classes to use theme colors
- [ ] Update badge classes
- [ ] Update alert classes
- [ ] Update form input classes

### 3.2 Update Pegasus Legacy CSS
- [ ] Review `pegasus/tailwind.css`
- [ ] Update `.pg-link` color
- [ ] Update `.pg-button-danger` colors
- [ ] Update `.pg-text-*` classes

### 3.3 Update Template Colors
- [ ] Search templates for inline color classes
- [ ] Replace hardcoded colors with semantic classes
- [ ] Check partial templates in `templates/metrics/partials/`
- [ ] Check component templates in `templates/web/components/`

### 3.4 Update Chart.js Colors
- [ ] Locate Chart.js color configurations
- [ ] Create chart color constants file (if needed)
- [ ] Update chart backgrounds to match new palette
- [ ] Update chart borders/lines

---

## Phase 4: Accessibility Testing (Effort: M)

### 4.1 Setup
- [ ] Install @axe-core/playwright
  ```bash
  npm install @axe-core/playwright
  ```
- [ ] Create `tests/e2e/accessibility.spec.ts`
- [ ] Create test fixtures for authenticated pages

### 4.2 Create Accessibility Tests
- [ ] Test: Login page accessibility
- [ ] Test: App Home accessibility
- [ ] Test: Team Dashboard accessibility
- [ ] Test: CTO Dashboard accessibility
- [ ] Test: Integrations page accessibility
- [ ] Test: Survey pages accessibility

### 4.3 Fix Violations
- [ ] Run accessibility tests
- [ ] Document all violations
- [ ] Fix color contrast issues
- [ ] Fix missing labels/alt text
- [ ] Fix focus indicators
- [ ] Re-run tests until all pass

---

## Phase 5: Documentation & Review (Effort: S)

### 5.1 Documentation
- [ ] Update CLAUDE.md if needed (color guidelines)
- [ ] Create color palette reference (optional)
- [ ] Document theme customization approach

### 5.2 Visual QA
- [ ] Take "after" screenshots
- [ ] Compare with "before" screenshots
- [ ] Check all pages render correctly
- [ ] Verify charts are readable
- [ ] Test dark mode consistency

### 5.3 Team Review
- [ ] Share screenshots for feedback
- [ ] Address any concerns
- [ ] Final approval

### 5.4 Commit
- [ ] Commit theme changes
- [ ] Commit accessibility tests
- [ ] Update dev docs

---

## Verification Commands

```bash
# Run accessibility tests
npx playwright test accessibility.spec.ts

# Run all E2E tests (ensure no regressions)
npx playwright test

# Check dev server
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/

# Audit color usage
grep -r "cyan" assets/styles/ --include="*.css" | wc -l
```

---

## Quick Reference: Color Token Mapping

| Old Value | New Semantic Token | DaisyUI Class |
|-----------|-------------------|---------------|
| `text-cyan` | `--color-primary` | `text-primary` |
| `bg-cyan` | `--color-primary` | `bg-primary` |
| `#06b6d4` | `--color-primary` | `text-primary` |
| `text-emerald-400` | `--color-success` | `text-success` |
| `text-rose-400` | `--color-error` | `text-error` |
| `text-amber-400` | `--color-warning` | `text-warning` |
| `bg-surface` | `--color-base-200` | `bg-base-200` |
| `bg-deep` | `--color-base-100` | `bg-base-100` |
| `bg-elevated` | `--color-base-300` | `bg-base-300` |
