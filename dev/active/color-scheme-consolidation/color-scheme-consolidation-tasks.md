# Color Scheme Consolidation - Tasks

**Last Updated:** 2025-12-20

## Progress Overview

- [x] Phase 0: Initial Setup (completed this session)
- [ ] Phase 1: Expand Semantic Classes
- [ ] Phase 2: Marketing Pages Refactor
- [ ] Phase 3: App Pages Refactor
- [ ] Phase 4: Onboarding & Error Pages
- [ ] Phase 5: Validation & Cleanup

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

## Phase 1: Expand Semantic Classes

### 1.1 Add marketing-specific text classes [S]
- [ ] Add `app-text-hero` class (equivalent to stone-100)
- [ ] Add `app-text-body` class (equivalent to stone-300)
- [ ] Add `app-text-caption` class (equivalent to stone-400)
- [ ] Test in both light and dark themes

### 1.2 Add marketing background classes [S]
- [ ] Add `app-bg-section` for alternating sections
- [ ] Add `app-bg-card-dark` for always-dark cards
- [ ] Verify consistency across marketing pages

### 1.3 Add additional status/accent classes [S]
- [ ] Add `app-accent-primary`, `app-accent-secondary`, `app-accent-tertiary`
- [ ] Add `app-status-warning`, `app-status-info`
- [ ] Document in design-system.css header

### 1.4 Create dark-only wrapper class [S]
- [ ] Add `.app-dark-only` that forces dark theme
- [ ] Test with marketing page sections

---

## Phase 2: Marketing Pages Refactor

### 2.1 Hero section [S]
- [ ] Update `hero_terminal.html`
- [ ] Replace 7 stone-* occurrences
- [ ] Verify accessibility

### 2.2 Features section [M]
- [ ] Update `features_grid.html` (20 occurrences)
- [ ] Update `feature_highlight.html` (7 occurrences)
- [ ] Replace emerald-* with semantic classes

### 2.3 How it works section [S]
- [ ] Update `how_it_works.html`
- [ ] Replace 14 stone-* occurrences

### 2.4 What you get section [M]
- [ ] Update `what_you_get.html`
- [ ] Replace 24 stone-* occurrences

### 2.5 Pricing section [M]
- [ ] Update `pricing_simple.html`
- [ ] Replace 12 stone-* + 5 emerald-* occurrences

### 2.6 FAQ section [M]
- [ ] Update `faq.html`
- [ ] Replace 26 stone-* occurrences

### 2.7 Security & Trust sections [M]
- [ ] Update `security.html` (14 occurrences)
- [ ] Update `data_transparency.html` (4 occurrences)
- [ ] Update `built_with_you.html` (21 occurrences)

### 2.8 Footer & CTA sections [S]
- [ ] Update `footer.html`
- [ ] Update `cta_terminal.html`
- [ ] Update `cta.html`

---

## Phase 3: App Pages Refactor

### 3.1 Complete integrations page [M]
- [ ] Finish semantic class migration
- [ ] Remove all direct color classes
- [ ] Test both themes

### 3.2 Update metrics dashboard partials [M]
- [ ] `copilot_members_table.html`
- [ ] `leaderboard_table.html`
- [ ] `recent_prs_table.html`
- [ ] Other partials in `templates/metrics/partials/`

### 3.3 Update team management templates [S]
- [ ] Review `templates/teams/` for hardcoded colors
- [ ] Update to semantic classes

---

## Phase 4: Onboarding & Error Pages

### 4.1 Onboarding flow [M]
- [ ] Update `start.html` (7 occurrences)
- [ ] Update `complete.html` (7 occurrences)
- [ ] Update `select_org.html` (7 occurrences)
- [ ] Update `connect_jira.html` (3 occurrences)
- [ ] Update `connect_slack.html` (3 occurrences)
- [ ] Update `select_repos.html` (2 occurrences)
- [ ] Update `base.html` (1 occurrence)

### 4.2 Error pages [S]
- [ ] Update `400.html`
- [ ] Update `403.html`
- [ ] Update `404.html`
- [ ] Update `429.html`
- [ ] Update `500.html`

### 4.3 Account pages [M]
- [ ] Update `email.html`
- [ ] Update `password_reset.html`
- [ ] Update other account templates

---

## Phase 5: Validation & Cleanup

### 5.1 Run accessibility tests [S]
- [ ] Run `npx playwright test accessibility.spec.ts`
- [ ] All 9 tests must pass
- [ ] Fix any contrast issues

### 5.2 Create color linting rule [M]
- [ ] Create script to detect hardcoded colors
- [ ] Add `make lint-colors` command
- [ ] Document in CLAUDE.md

### 5.3 Update documentation [S]
- [ ] Update CLAUDE.md Design System section
- [ ] Add color usage examples
- [ ] Document semantic class reference

### 5.4 Remove unused code [S]
- [ ] Audit tailwind.config.js
- [ ] Remove legacy color definitions
- [ ] Clean up unused CSS

---

## Notes

- **Test after each file change** to catch regressions early
- **Commit frequently** after completing each section
- **Run accessibility tests** after completing each phase
