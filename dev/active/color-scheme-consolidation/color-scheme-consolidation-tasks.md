# Color Scheme Consolidation - Tasks

**Last Updated:** 2025-12-20 (Session 4 - All Phases Complete)

## Progress Overview

- [x] Phase 0: Initial Setup (completed Session 1)
- [x] Phase 1: Expand Semantic Classes (completed Session 2)
- [x] Phase 2: Marketing Pages Refactor (completed Session 3)
- [x] Phase 3: App Pages Refactor (completed Session 4)
- [x] Phase 4: Onboarding & Error Pages (completed Session 4)
- [x] Phase 5: Validation & Cleanup (completed Session 4)

**🎉 Color scheme consolidation complete!**

---

## Phase 0: Initial Setup [COMPLETED]

- [x] Update dark theme with Easy Eyes-inspired colors
- [x] Update tailwind.config.js with new color tokens
- [x] Replace slate with warmer stone in marketing templates
- [x] Create app-status-* semantic classes
- [x] Add light theme accessibility overrides
- [x] Update integrations page with semantic classes (partial)
- [x] Add CLI FAQ question
- [x] Create dev-docs structure

---

## Phase 1: Expand Semantic Classes [COMPLETED]

### 1.1 Add marketing-specific text classes [S] [COMPLETED]
- [x] Add `app-text-hero` class (equivalent to stone-100)
- [x] Add `app-text-body` class (equivalent to stone-300)
- [x] Add `app-text-caption` class (equivalent to stone-400)
- [x] Add `app-text-subtle` class (for fine print)
- [x] Test in both light and dark themes

### 1.2 Add marketing background classes [S] [COMPLETED]
- [x] Add `app-bg-section` for alternating sections
- [x] Add `app-bg-card-dark` for always-dark cards
- [x] Add `app-bg-section-bordered` for bordered sections
- [x] Verify consistency across marketing pages

### 1.3 Add additional status/accent classes [S] [COMPLETED]
- [x] Add `app-accent-primary`, `app-accent-secondary`, `app-accent-tertiary`
- [x] Add `app-status-warning`, `app-status-info`
- [x] Add `app-status-pill-warning`, `app-status-pill-info`

### 1.4 Light theme accessibility fixes [S] [COMPLETED]
- [x] Add table header contrast override
- [x] Add text-secondary contrast override
- [x] Add text-success contrast override
- [x] Replace text-accent-tertiary with text-teal-400 in marketing templates
- [x] All 9 accessibility tests passing

---

## Phase 2: Marketing Pages Refactor [COMPLETED]

### 2.1 Hero section [S] [COMPLETED]
- [x] Update `hero_terminal.html`
- [x] Replace stone-* with text-base-content variants
- [x] Fix button border visibility (border-base-content/30)
- [x] Verify accessibility

### 2.2 Features section [M] [COMPLETED]
- [x] Update `features_grid.html` (20 occurrences)
- [x] Replace emerald-* with semantic classes

### 2.3 How it works section [S] [COMPLETED]
- [x] Update `how_it_works.html`
- [x] Replace stone-* with text-base-content variants

### 2.4 What you get section [M] [COMPLETED]
- [x] Update `what_you_get.html`
- [x] Replace stone-* with text-base-content variants

### 2.5 Pricing section [M] [COMPLETED]
- [x] Update `pricing_simple.html`
- [x] Replace stone-* + emerald-* with semantic classes

### 2.6 FAQ section [M] [COMPLETED]
- [x] Update `faq.html`
- [x] Replace stone-* with text-base-content variants

### 2.7 Security & Trust sections [M] [COMPLETED]
- [x] Update `security.html`
- [x] Update `data_transparency.html`
- [x] Update `built_with_you.html`

### 2.8 Footer & CTA sections [S] [COMPLETED]
- [x] Update `cta_terminal.html`
- [x] Update `problem_discovery.html`
- [x] Update `problem_statement.html`
- [x] Update `integrations.html`

### 2.9 Terminal Always-Dark Styling [S] [COMPLETED]
- [x] Force terminal dark in light theme
- [x] Override text colors inside terminal
- [x] Fix verdict line color (lighter orange #FB923C)

### 2.10 Theme Toggle & Navigation [S] [COMPLETED]
- [x] Show theme toggle for all users (not just authenticated)
- [x] Add spacing between header elements (gap-2)
- [x] Fix theme flicker on page navigation

### 2.11 Light Theme Accessibility [S] [COMPLETED]
- [x] Add text-teal-400 contrast override
- [x] Add text-accent-primary contrast override
- [x] Add text-purple-300 contrast override
- [x] Add text-amber-400 contrast override
- [x] Add text-accent-error contrast override
- [x] All 9 accessibility tests passing

---

## Phase 3: App Pages Refactor [COMPLETED]

### 3.1 Complete integrations page [M] [COMPLETED]
- [x] Finish semantic class migration
- [x] Remove all direct color classes (keep brand colors for logos)
- [x] Test both themes

### 3.2 Update metrics dashboard partials [M] [COMPLETED]
- [x] Templates already using DaisyUI semantic classes
- [x] Verified no hardcoded colors

### 3.3 Update team management templates [S] [COMPLETED]
- [x] Review `templates/teams/` for hardcoded colors
- [x] Only Pegasus framework classes (pg-*) found - these are OK

---

## Phase 4: Onboarding & Error Pages [COMPLETED]

### 4.1 Onboarding flow [M] [COMPLETED]
- [x] Update `start.html` - stone-* → text-base-content variants
- [x] Update `complete.html` - stone-* → text-base-content variants
- [x] Update `select_org.html` - stone-* → text-base-content variants
- [x] Update `connect_jira.html` - stone-* → text-base-content variants
- [x] Update `connect_slack.html` - stone-* → text-base-content variants
- [x] Update `select_repos.html` - stone-* → text-base-content variants
- [x] Update `base.html` - stone-* → text-base-content variants

### 4.2 Error pages [S] [COMPLETED]
- [x] Update `error_base.html` - rose-* → text-error semantic
- [x] Update `400.html` (uses error_base.html)
- [x] Update `403.html` (uses error_base.html)
- [x] Update `404.html` (uses error_base.html)
- [x] Update `429.html` (uses error_base.html)
- [x] Update `500.html` (uses error_base.html)

### 4.3 Account pages [M] [COMPLETED]
- [x] Update `email.html` - elevated/cyan → base-300/primary
- [x] Update all 11 account templates
- [x] All stone-* → text-base-content variants

---

## Phase 5: Validation & Cleanup [COMPLETED]

### 5.1 Run accessibility tests [S] [COMPLETED]
- [x] Run `npx playwright test accessibility.spec.ts`
- [x] All 9 tests passing
- [x] Fix any contrast issues

### 5.2 Create color linting rule [M] [COMPLETED]
- [x] Create `scripts/lint_colors.py` script
- [x] Add `make lint-colors` command
- [x] Add `make lint-colors-fix` command with suggestions
- [x] Update `make lint` to include color linting
- [x] Document in CLAUDE.md

### 5.3 Update documentation [S] [COMPLETED]
- [x] Update CLAUDE.md Design System section
- [x] Add color usage examples
- [x] Document semantic class reference

### 5.4 Remove unused code [S] [COMPLETED]
- [x] Audit tailwind.config.js
- [x] Legacy colors kept for CSS utility classes (used internally)
- [x] Removed 6 unused legacy marketing templates
- [x] All templates now use DaisyUI semantic colors

---

## Additional Fixes [COMPLETED]

### Fix sign-in button positioning [S] [COMPLETED]
- [x] Sign-in button too close to window edge on main page
- [x] Add proper spacing/margin from browser scrollbar (px-4 lg:px-6)

### Remove unused legacy templates [S] [COMPLETED]
- [x] Removed `cta.html` (unused)
- [x] Removed `hero.html` (unused)
- [x] Removed `landing_section1.html` (unused)
- [x] Removed `landing_section2.html` (unused)
- [x] Removed `feature_highlight.html` (unused)
- [x] Removed `testimonials.html` (unused)

---

## Summary

The color scheme consolidation is complete:

1. **All templates migrated** to DaisyUI semantic colors (text-base-content, bg-base-*, text-success, text-error, etc.)
2. **Color linter created** (`make lint-colors`) to prevent regression
3. **Light/dark theme support** working correctly across all pages
4. **Accessibility tests passing** (9/9)
5. **Legacy templates removed** (6 unused files)
6. **Brand colors preserved** for integration logos (Jira, Slack, Copilot)

The codebase now uses a consistent semantic color system that automatically adapts to light/dark themes.
