# Visual Stages 3 & 4: Landing Page Color Update

**Last Updated:** 2025-12-20

## Executive Summary

This plan covers the implementation of Visual Stages 3 and 4 from the "Sunset Dashboard" design system migration. These stages focus on updating the landing page hero section and features grid to use the new warm color palette (coral orange, teal, amber) instead of the legacy cyan accent colors.

**Scope:**
- Stage 3: Hero terminal section (`hero_terminal.html`)
- Stage 4: Features grid section (`features_grid.html`)

**Prerequisites Completed:**
- Stage 1: Color token foundation (tailwind.config.js, DaisyUI theme) ✓
- Stage 2: Design system CSS classes (design-system.css) ✓

---

## Current State Analysis

### hero_terminal.html

Current color usage (lines to change):
| Line | Current | Issue |
|------|---------|-------|
| 5 | `rgba(6,182,212,0.03)` (cyan grid) | Needs warm orange tint |
| 27 | `.terminal-prompt` (cyan via CSS) | CSS uses `text-cyan` |
| 59 | `text-cyan` (result line) | Should use `text-accent-primary` |
| 74-75 | `gradient-text` (from-cyan-light) | CSS gradient needs update |
| 75 | `text-rose-400` ("busier") | Should use `text-accent-error` |
| 84 | `bg-cyan hover:bg-cyan-dark` (CTA) | Should use `bg-accent-primary` |

### features_grid.html

Current color usage:
| Line | Current | Issue |
|------|---------|-------|
| 6 | `text-cyan` (section label) | Should use `text-accent-primary` |
| 21-22 | `bg-cyan/10`, `text-cyan` | Feature 1 icon - update to coral |
| 40-41 | `bg-cyan/30`, `bg-cyan` | Mini chart bars - update to coral |
| 59-60 | `bg-amber-500/10`, `text-amber-400` | Feature 2 - keep (already warm) |
| 76-77 | `bg-cyan/20`, `text-cyan` | Slack bot avatar |
| 86-88 | `hover:border-cyan/50` | Survey buttons hover |
| 98-99 | `bg-emerald-500/10`, `text-emerald-400` | Feature 3 - update to teal |

### landing-page.css

Lines needing updates:
| Line | Current | New |
|------|---------|-----|
| 27 | `@apply text-cyan` | `@apply text-accent-primary` |
| 31 | `@apply ... bg-cyan` | `@apply ... bg-accent-primary` |
| 36 | `from-cyan-light to-slate-100` | `from-accent-primary to-pink-500` |
| 42 | `hover:border-cyan/50` | `hover:border-accent-primary/50` |
| 64 | `hover:border-cyan/30` | `hover:border-accent-primary/30` |
| 70 | `hover:border-cyan/50` | `hover:border-accent-primary/50` |

---

## Proposed Future State

### Hero Section
- Terminal prompt: Coral orange (`text-accent-primary`)
- Result line: Coral orange (`text-accent-primary`)
- "faster" gradient: Coral to pink (`from-accent-primary to-pink-500`)
- "busier" text: Soft red (`text-accent-error`)
- CTA button: Coral orange bg with white text
- Grid background: Subtle orange tint instead of cyan

### Features Section
- Section label: Coral orange (`text-accent-primary`)
- Feature 1 (Dashboard): Coral orange icon
- Feature 2 (Surveys): Amber (keep as-is - already warm)
- Feature 3 (Visibility): Teal (`text-accent-tertiary`)
- Card hover: Orange border (`hover:border-accent-primary/50`)
- Slack bot avatar: Orange accent

---

## Implementation Phases

### Phase 1: Update landing-page.css (3 changes)
Update CSS classes before template changes to ensure styles are available.

### Phase 2: Update hero_terminal.html (6 changes)
Apply new colors to hero section elements.

### Phase 3: Update features_grid.html (8 changes)
Apply new colors to feature cards and interactive elements.

### Phase 4: Validation
Build assets and run e2e smoke tests.

---

## Detailed Tasks

### Phase 1: CSS Updates

**Task 1.1: Update terminal prompt color** [S]
- File: `assets/styles/app/tailwind/landing-page.css`
- Line 27: Change `@apply text-cyan` to `@apply text-accent-primary`
- Acceptance: Terminal prompt uses coral orange

**Task 1.2: Update terminal cursor color** [S]
- File: `assets/styles/app/tailwind/landing-page.css`
- Line 31: Change `bg-cyan` to `bg-accent-primary`
- Acceptance: Blinking cursor uses coral orange

**Task 1.3: Update gradient text** [S]
- File: `assets/styles/app/tailwind/landing-page.css`
- Line 36: Change `from-cyan-light to-slate-100` to `from-accent-primary to-pink-500`
- Acceptance: "faster" text shows coral-to-pink gradient

**Task 1.4: Update stat card hover** [S]
- File: `assets/styles/app/tailwind/landing-page.css`
- Line 42: Change `hover:border-cyan/50` to `hover:border-accent-primary/50`
- Acceptance: Stat cards show orange hover border

**Task 1.5: Update feature card hover** [S]
- File: `assets/styles/app/tailwind/landing-page.css`
- Line 64: Change `hover:border-cyan/30` to `hover:border-accent-primary/30`
- Acceptance: Feature cards show orange hover border

**Task 1.6: Update integration logo hover** [S]
- File: `assets/styles/app/tailwind/landing-page.css`
- Line 70: Change `hover:border-cyan/50` to `hover:border-accent-primary/50`
- Acceptance: Integration logos show orange hover border

---

### Phase 2: Hero Terminal Updates

**Task 2.1: Update background grid tint** [S]
- File: `templates/web/components/hero_terminal.html`
- Line 5: Change `rgba(6,182,212,0.03)` to `rgba(249,115,22,0.03)`
- Acceptance: Subtle warm orange grid pattern

**Task 2.2: Update result line color** [S]
- File: `templates/web/components/hero_terminal.html`
- Line 59: Change `text-cyan` to `text-accent-primary`
- Acceptance: Terminal result line shows in coral orange

**Task 2.3: Update "busier" text color** [S]
- File: `templates/web/components/hero_terminal.html`
- Line 75: Change `text-rose-400` to `text-accent-error`
- Acceptance: "busier" text uses design system error color

**Task 2.4: Update primary CTA button** [M]
- File: `templates/web/components/hero_terminal.html`
- Line 84: Change `bg-cyan hover:bg-cyan-dark text-deep` to `bg-accent-primary hover:bg-orange-600 text-white`
- Acceptance: "Join Waitlist" button uses coral orange bg with white text

---

### Phase 3: Features Grid Updates

**Task 3.1: Update section label color** [S]
- File: `templates/web/components/features_grid.html`
- Line 6: Change `text-cyan` to `text-accent-primary`
- Acceptance: "Features" label shows in coral orange

**Task 3.2: Update Feature 1 icon (Dashboard)** [S]
- File: `templates/web/components/features_grid.html`
- Lines 21-22: Change `bg-cyan/10`, `text-cyan` to `bg-accent-primary/10`, `text-accent-primary`
- Acceptance: Chart icon uses coral orange

**Task 3.3: Update Feature 1 mini chart** [S]
- File: `templates/web/components/features_grid.html`
- Lines 40-41: Change `bg-cyan/30`, `bg-cyan` to `bg-accent-primary/30`, `bg-accent-primary`
- Acceptance: AI-assisted chart bars use coral orange

**Task 3.4: Update Feature 3 icon (Visibility)** [S]
- File: `templates/web/components/features_grid.html`
- Lines 98-99: Change `bg-emerald-500/10`, `text-emerald-400` to `bg-accent-tertiary/10`, `text-accent-tertiary`
- Acceptance: Eye icon uses teal color

**Task 3.5: Update Slack bot avatar** [S]
- File: `templates/web/components/features_grid.html`
- Lines 76-77: Change `bg-cyan/20`, `text-cyan` to `bg-accent-primary/20`, `text-accent-primary`
- Acceptance: Slack bot "T" avatar uses coral orange

**Task 3.6: Update survey button hovers** [S]
- File: `templates/web/components/features_grid.html`
- Lines 86-88: Change `hover:border-cyan/50` to `hover:border-accent-primary/50` (3 occurrences)
- Acceptance: Yes/No/Partially buttons have warm hover state

---

### Phase 4: Validation

**Task 4.1: Build assets** [S]
```bash
npm run build
```
- Acceptance: Build completes without errors

**Task 4.2: Run e2e smoke tests** [M]
```bash
make e2e-smoke
```
- Acceptance: All smoke tests pass

**Task 4.3: Visual verification checklist** [M]
- [ ] Terminal prompt is coral orange
- [ ] Terminal result line is coral orange
- [ ] "faster" has coral-to-pink gradient
- [ ] "busier" uses soft red
- [ ] CTA button is coral orange with white text
- [ ] "Features" label is coral orange
- [ ] Feature 1 icon is coral orange
- [ ] Feature 2 icon remains amber (no change)
- [ ] Feature 3 icon is teal
- [ ] Card hover states show orange border
- [ ] No broken layouts or missing styles

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| CSS class conflicts | Low | Medium | Test each change incrementally |
| Color token not available | Low | High | Verify tailwind.config.js has all tokens |
| E2E test failures | Low | Medium | Fix any selector changes |
| Contrast issues | Low | Medium | All colors already WCAG AA verified |

---

## Success Metrics

1. **Build passes**: `npm run build` completes without errors
2. **E2E smoke tests pass**: `make e2e-smoke` succeeds
3. **Color consistency**: All warm colors from design system used correctly
4. **No regressions**: All interactive elements still work
5. **Visual coherence**: Landing page feels "warm" and unified

---

## Dependencies

### Required Files (Read)
- `dev/visual-improvement-plan.md` - Master plan reference
- `tailwind.config.js` - Verify color tokens exist
- `assets/styles/app/tailwind/design-system.css` - CSS class reference

### Files to Modify
- `assets/styles/app/tailwind/landing-page.css` - CSS class definitions
- `templates/web/components/hero_terminal.html` - Hero section
- `templates/web/components/features_grid.html` - Features section

### Test Commands
```bash
npm run build          # Build CSS/JS assets
make e2e-smoke         # Run smoke tests
make dev               # Start dev server (if not running)
```

---

## Rollback Plan

If issues occur:
1. Revert changes in Git: `git checkout -- templates/web/components/ assets/styles/`
2. Rebuild: `npm run build`
3. Verify: `make e2e-smoke`
