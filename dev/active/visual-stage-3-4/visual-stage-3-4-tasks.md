# Visual Stages 3 & 4: Task Checklist

**Last Updated:** 2025-12-20
**Status:** ✅ COMPLETED

## Overview

- **Total Tasks:** 16
- **Estimated Effort:** Small (most are single-line changes)
- **Dependencies:** Stages 1-2 complete (color tokens and design system CSS)

---

## Phase 1: CSS Updates (landing-page.css)

- [x] **1.1** Update terminal prompt color
  - File: `assets/styles/app/tailwind/landing-page.css:27`
  - Change: `text-cyan` → `text-accent-primary`

- [x] **1.2** Update terminal cursor color
  - File: `assets/styles/app/tailwind/landing-page.css:31`
  - Change: `bg-cyan` → `bg-accent-primary`

- [x] **1.3** Update gradient text
  - File: `assets/styles/app/tailwind/landing-page.css:36`
  - Change: `from-cyan-light to-slate-100` → `from-accent-primary to-pink-500`

- [x] **1.4** Update stat card hover
  - File: `assets/styles/app/tailwind/landing-page.css:42`
  - Change: `hover:border-cyan/50` → `hover:border-accent-primary/50`

- [x] **1.5** Update feature card hover
  - File: `assets/styles/app/tailwind/landing-page.css:64`
  - Change: `hover:border-cyan/30` → `hover:border-accent-primary/30`

- [x] **1.6** Update integration logo hover
  - File: `assets/styles/app/tailwind/landing-page.css:70`
  - Change: `hover:border-cyan/50` → `hover:border-accent-primary/50`

---

## Phase 2: Hero Terminal Updates (hero_terminal.html)

- [x] **2.1** Update background grid tint
  - File: `templates/web/components/hero_terminal.html:5`
  - Change: `rgba(6,182,212,0.03)` → `rgba(249,115,22,0.03)`

- [x] **2.2** Update result line color
  - File: `templates/web/components/hero_terminal.html:59`
  - Change: `text-cyan` → `text-accent-primary`

- [x] **2.3** Update "busier" text color
  - File: `templates/web/components/hero_terminal.html:75`
  - Change: `text-rose-400` → `text-accent-error`

- [x] **2.4** Update primary CTA button
  - File: `templates/web/components/hero_terminal.html:84`
  - Change: `bg-cyan hover:bg-cyan-dark text-deep` → `bg-accent-primary hover:bg-orange-600 text-white`

---

## Phase 3: Features Grid Updates (features_grid.html)

- [x] **3.1** Update section label color
  - File: `templates/web/components/features_grid.html:6`
  - Change: `text-cyan` → `text-accent-primary`

- [x] **3.2** Update Feature 1 icon (Dashboard)
  - File: `templates/web/components/features_grid.html:21-22`
  - Change: `bg-cyan/10`, `text-cyan` → `bg-accent-primary/10`, `text-accent-primary`

- [x] **3.3** Update Feature 1 mini chart
  - File: `templates/web/components/features_grid.html:40-41`
  - Change: `bg-cyan/30`, `bg-cyan` → `bg-accent-primary/30`, `bg-accent-primary`

- [x] **3.4** Update Feature 3 icon (Visibility)
  - File: `templates/web/components/features_grid.html:98-99`
  - Change: `bg-emerald-500/10`, `text-emerald-400` → `bg-accent-tertiary/10`, `text-accent-tertiary`

- [x] **3.5** Update Slack bot avatar
  - File: `templates/web/components/features_grid.html:76-77`
  - Change: `bg-cyan/20`, `text-cyan` → `bg-accent-primary/20`, `text-accent-primary`

- [x] **3.6** Update survey button hovers
  - File: `templates/web/components/features_grid.html:86-88`
  - Change: `hover:border-cyan/50` → `hover:border-accent-primary/50` (3x)

---

## Phase 4: Validation

- [x] **4.1** Build assets
  ```bash
  npm run build
  ```

- [x] **4.2** Run e2e smoke tests
  ```bash
  make e2e-smoke
  ```
  **Result:** 6 passed (3.8s)

- [x] **4.3** Visual verification
  - [x] Terminal prompt is coral orange
  - [x] Terminal result line is coral orange
  - [x] "faster" has coral-to-pink gradient
  - [x] "busier" uses soft red
  - [x] CTA button is coral orange with white text
  - [x] "Features" label is coral orange
  - [x] Feature 1 icon is coral orange
  - [x] Feature 2 icon remains amber
  - [x] Feature 3 icon is teal
  - [x] Card hover states show orange border
  - [x] No broken layouts

---

## Completion Criteria

All items above must be checked before marking stages complete:

1. [x] All CSS changes applied
2. [x] All template changes applied
3. [x] `npm run build` succeeds
4. [x] `make e2e-smoke` passes
5. [x] Visual review approved

---

## Quick Reference

### Files Modified
1. `assets/styles/app/tailwind/landing-page.css`
2. `templates/web/components/hero_terminal.html`
3. `templates/web/components/features_grid.html`

### Color Tokens
- `accent-primary`: `#F97316` (coral orange)
- `accent-tertiary`: `#2DD4BF` (teal)
- `accent-error`: `#F87171` (soft red)
- `pink-500`: `#EC4899` (gradient end)
- `orange-600`: `#EA580C` (hover state)
