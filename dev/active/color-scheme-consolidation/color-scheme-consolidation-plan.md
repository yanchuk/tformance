# Color Scheme Consolidation Plan

**Last Updated:** 2025-12-20

## Executive Summary

Consolidate the color system from scattered hardcoded Tailwind classes across 40+ template files into a centralized, semantic design token system. This will reduce maintenance overhead, ensure theme consistency, and make future color adjustments trivial.

**Current Problem:** Colors are defined in 4+ locations with 261+ direct color class usages in templates, making theme changes require touching dozens of files.

**Target State:** All colors controlled via 2 files (DaisyUI theme + design-system.css), with templates using only semantic classes.

## Current State Analysis

### Color Definition Locations (Problem: Too Many)

| Location | Purpose | Issue |
|----------|---------|-------|
| `tailwind.config.js` | Custom color tokens | Good - centralized tokens |
| `site-tailwind.css` | DaisyUI theme definitions | Good - theme variants |
| `design-system.css` | Component classes | Good - semantic classes |
| **Templates (40+ files)** | Direct color classes | **BAD - hardcoded colors** |

### Hardcoded Color Usage (From Analysis)

- **Gray-scale colors:** 261 occurrences across 42 files
- **Status colors (emerald/green):** 12 occurrences across 4 files
- **Violet/purple colors:** ~10 occurrences
- **Other accent colors:** ~50 occurrences

### Already Completed (This Session)

1. Updated dark theme with Easy Eyes-inspired warmer colors
2. Created semantic status classes (`app-status-connected`, `app-status-available`, etc.)
3. Replaced `slate` with warmer `stone` in marketing components
4. Added light theme accessibility overrides
5. Started using semantic classes in integrations page

## Proposed Future State

### Color Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    COLOR SYSTEM HIERARCHY                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Level 1: Theme Definitions (site-tailwind.css)             │
│  ├── tformance (dark theme)                                 │
│  │   └── base-100, base-200, base-300, base-content, etc.  │
│  └── tformance-light (light theme)                          │
│      └── Same tokens, light values                          │
│                                                              │
│  Level 2: Semantic Classes (design-system.css)              │
│  ├── Text: app-text-primary, app-text-muted, app-text-accent│
│  ├── Status: app-status-connected, app-status-error, etc.  │
│  ├── Cards: app-card, app-card-interactive                 │
│  └── Buttons: app-btn-primary, app-btn-secondary, etc.     │
│                                                              │
│  Level 3: Templates (use ONLY semantic classes)             │
│  ├── NO direct color classes (text-stone-400, etc.)        │
│  └── Only app-* classes or DaisyUI semantic classes        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Semantic Color Mapping

| Current (Hardcoded) | Future (Semantic) |
|---------------------|-------------------|
| `text-stone-100` | `text-base-content` |
| `text-stone-200` | `text-base-content` |
| `text-stone-300` | `text-base-content/90` |
| `text-stone-400` | `text-base-content/70` or `app-text-muted` |
| `text-emerald-400` | `app-status-connected` |
| `text-violet-400` | `app-status-available` |
| `text-red-400` | `app-status-error` or `text-error` |
| `bg-surface` | `bg-base-200` |
| `border-elevated` | `border-base-300` |

## Implementation Phases

### Phase 1: Expand Semantic Classes (Effort: M)
Add missing semantic classes to design-system.css to cover all use cases.

### Phase 2: Marketing Pages Refactor (Effort: L)
Update all marketing/landing page templates to use semantic classes.

### Phase 3: App Pages Refactor (Effort: M)
Update all authenticated app templates to use semantic classes.

### Phase 4: Onboarding & Error Pages (Effort: S)
Update onboarding flow and error pages.

### Phase 5: Validation & Cleanup (Effort: S)
Run linting, accessibility tests, remove unused color definitions.

## Detailed Tasks

### Phase 1: Expand Semantic Classes

**1.1 Add marketing-specific text classes** [S]
- Add `app-text-hero` for large headings (stone-100 equivalent)
- Add `app-text-body` for paragraph text (stone-300 equivalent)
- Add `app-text-caption` for small text (stone-400 equivalent)
- Acceptance: Classes work in both light and dark themes

**1.2 Add marketing background classes** [S]
- Add `app-bg-section` for alternating sections
- Add `app-bg-card-dark` for always-dark cards (marketing)
- Acceptance: No hardcoded bg-surface/bg-deep in templates

**1.3 Add additional status/accent classes** [S]
- Add `app-accent-primary`, `app-accent-secondary`, `app-accent-tertiary`
- Add `app-status-warning`, `app-status-info`
- Acceptance: All status colors have semantic equivalents

**1.4 Create dark-only wrapper class** [S]
- Add `.app-dark-only` that forces dark theme on children
- Use for marketing pages that should always be dark
- Acceptance: Marketing pages render correctly regardless of system theme

### Phase 2: Marketing Pages Refactor

**2.1 Hero section** [S]
- File: `templates/web/components/hero_terminal.html`
- Replace: 7 stone-* occurrences
- Acceptance: Uses only app-* or base-content classes

**2.2 Features section** [M]
- Files: `features_grid.html`, `feature_highlight.html`
- Replace: 27 stone-* occurrences, 3 emerald-* occurrences
- Acceptance: All colors are semantic

**2.3 How it works section** [S]
- File: `how_it_works.html`
- Replace: 14 stone-* occurrences
- Acceptance: Uses semantic classes

**2.4 What you get section** [M]
- File: `what_you_get.html`
- Replace: 24 stone-* occurrences
- Acceptance: Uses semantic classes

**2.5 Pricing section** [M]
- File: `pricing_simple.html`
- Replace: 12 stone-* + 5 emerald-* occurrences
- Acceptance: Uses semantic classes

**2.6 FAQ section** [M]
- File: `faq.html`
- Replace: 26 stone-* occurrences
- Acceptance: Uses semantic classes

**2.7 Security & Trust sections** [M]
- Files: `security.html`, `data_transparency.html`, `built_with_you.html`
- Replace: ~40 stone-* occurrences
- Acceptance: Uses semantic classes

**2.8 Footer & CTA sections** [S]
- Files: `footer.html`, `cta_terminal.html`, `cta.html`
- Replace: ~10 occurrences
- Acceptance: Uses semantic classes

### Phase 3: App Pages Refactor

**3.1 Update integrations page** [M]
- File: `apps/integrations/templates/integrations/home.html`
- Status: Partially done, finish remaining
- Acceptance: No direct color classes

**3.2 Update metrics dashboard partials** [M]
- Files: `templates/metrics/partials/*.html`
- Acceptance: All use semantic classes

**3.3 Update team management templates** [S]
- Files: `templates/teams/*.html`
- Acceptance: Uses semantic classes

### Phase 4: Onboarding & Error Pages

**4.1 Onboarding flow** [M]
- Files: `templates/onboarding/*.html`
- Replace: ~25 stone-* occurrences
- Acceptance: Semantic classes, works in both themes

**4.2 Error pages (400, 403, 404, 429, 500)** [S]
- Files: `templates/4*.html`, `templates/5*.html`
- Replace: ~10 occurrences
- Acceptance: Uses semantic classes

**4.3 Account pages** [M]
- Files: `templates/account/*.html`
- Replace: ~20 occurrences
- Acceptance: Uses semantic classes

### Phase 5: Validation & Cleanup

**5.1 Run accessibility tests** [S]
- Command: `npx playwright test accessibility.spec.ts`
- Acceptance: All 9 tests pass

**5.2 Create color linting rule** [M]
- Add custom linter to flag direct color classes in templates
- Acceptance: Can run `make lint-colors` to find violations

**5.3 Update CLAUDE.md documentation** [S]
- Document color system in CLAUDE.md
- Add examples of correct usage
- Acceptance: New developers understand the system

**5.4 Remove unused color definitions** [S]
- Audit tailwind.config.js for unused tokens
- Remove legacy colors if not needed
- Acceptance: No dead code

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Breaking existing pages | High | Medium | Incremental changes, test each file |
| Light/dark theme inconsistency | Medium | Medium | Test both themes for each change |
| Accessibility regression | High | Low | Run axe-core tests after each phase |
| Missing semantic class | Low | High | Create classes before refactoring |

## Success Metrics

1. **Zero hardcoded color classes** in templates
2. **All accessibility tests pass** (9/9)
3. **Color changes require editing max 2 files** (theme + design-system)
4. **Documentation updated** with color system guide

## Required Resources

- **Files to modify:** ~50 template files
- **New classes to create:** ~15 semantic classes
- **Estimated effort:** 4-6 hours total
- **Dependencies:** None (can be done incrementally)
