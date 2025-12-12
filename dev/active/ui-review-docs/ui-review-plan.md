# UI Consistency Review Plan

**Last Updated:** 2025-12-12
**Branch:** `feature/ui-consistency-review`
**Worktree:** `dev/active/ui-review`

---

## Executive Summary

This plan addresses the need for a comprehensive UI audit to ensure visual and behavioral consistency across all user-facing interfaces. The current implementation has evolved organically, resulting in style drift between the polished landing page and internal app pages.

**Goal:** Create a cohesive, distinctive user experience that carries the terminal-themed aesthetic from landing through the entire application.

---

## Current State Analysis

### Design System Foundation

**Existing Assets:**
- **Colors:** Custom palette (deep `#0f172a`, surface `#1e293b`, elevated `#334155`, cyan `#06b6d4`)
- **Typography:** JetBrains Mono (code/data) + DM Sans (body)
- **Components:** DaisyUI + Flowbite + custom landing-page CSS
- **Theme:** Dark mode enforced (`class="dark" data-theme="dark"`)

### Identified Inconsistencies

| Area | Landing Page | App Pages | Issue |
|------|-------------|-----------|-------|
| **Background** | `bg-deep` (slate-900) | `bg-base-100` (DaisyUI) | Color mismatch |
| **Cards** | `bg-surface` with `border-elevated` | `bg-base-100 shadow-md border-base-200` | Different styling |
| **Accent** | Cyan (`#06b6d4`) | DaisyUI primary | Color inconsistency |
| **Typography** | Custom font classes | Default DaisyUI | Missing font application |
| **Navigation** | None (minimal) | Generic DaisyUI tabs | Style drift |
| **Buttons** | `bg-cyan hover:bg-cyan-dark` | `btn-primary` | Different treatments |

### User Flow Gaps

1. **Landing → Sign Up:** Abrupt transition from terminal theme to generic auth pages
2. **Onboarding:** Uses basic DaisyUI, loses brand identity
3. **Dashboard:** Placeholder content, no data visualization
4. **Integrations:** Good card structure but doesn't match landing aesthetic

---

## Proposed Future State

### Design Direction: "Terminal-Native Dashboard"

A cohesive dark theme that extends the landing page's terminal aesthetic throughout:

- **Dark-first:** All pages use deep/surface/elevated color scheme
- **Data-forward:** Monospace fonts for metrics, clean sans for UI text
- **Cyan accents:** Primary interaction color throughout
- **Subtle grid patterns:** Background texture for depth
- **Card consistency:** All cards use surface bg with elevated borders

### Visual Components to Standardize

1. **App Shell**
   - Dark sidebar navigation
   - Cyan accent for active states
   - Team switcher with consistent dropdown styling

2. **Cards**
   - Unified `.app-card` class
   - Surface background, elevated border
   - Hover states with cyan accent

3. **Data Visualization**
   - Chart.js with cyan/emerald/rose color palette
   - Monospace numbers
   - Dark backgrounds

4. **Forms & Inputs**
   - Dark inputs with elevated borders
   - Cyan focus rings
   - Clear error/success states

---

## Implementation Phases

### Phase 1: Design System Consolidation (Foundation)

**Objective:** Create unified CSS classes and document the design system.

1. Create `assets/styles/app/tailwind/design-system.css`
2. Define standardized component classes:
   - `.app-page-bg` - page background
   - `.app-card` - unified card styling
   - `.app-sidebar` - navigation styling
   - `.app-stat` - metric display
   - `.app-btn-primary/secondary/ghost` - button variants
3. Update `tailwind.config.js` to ensure all custom colors are available
4. Create design tokens documentation

**Effort:** M

### Phase 2: Base Templates (Structure)

**Objective:** Update base templates to use the design system.

1. Update `templates/web/base.html`:
   - Apply `bg-deep` to body
   - Ensure font families are applied

2. Update `templates/web/app/app_base.html`:
   - New sidebar design with terminal aesthetic
   - Dark theme throughout
   - Consistent nav patterns

3. Create `templates/web/components/app_card.html` - reusable card component

**Effort:** M

### Phase 3: Navigation Overhaul

**Objective:** Create consistent navigation that matches brand identity.

1. Redesign `top_nav.html` for public pages
2. Redesign `top_nav_app.html` for authenticated pages
3. Redesign `app_nav.html` sidebar
4. Ensure mobile responsiveness
5. Add active state indicators with cyan accent

**Effort:** L

### Phase 4: Onboarding Flow Polish

**Objective:** Make onboarding feel premium and on-brand.

1. Update `onboarding/base.html` with terminal aesthetic
2. Redesign progress steps component
3. Polish each step:
   - `start.html` - GitHub connection
   - `select_org.html` - Organization selection
   - `select_repos.html` - Repository selection
   - `connect_jira.html` - Jira integration
   - `connect_slack.html` - Slack integration
   - `complete.html` - Completion celebration
4. Add subtle animations and transitions

**Effort:** L

### Phase 5: Dashboard Implementation

**Objective:** Create the main dashboard with real metrics visualization.

1. Replace placeholder `app_home.html` with actual dashboard
2. Implement Chart.js components:
   - PR activity over time
   - AI adoption trend
   - Key metrics cards
   - Team breakdown table
3. Create `templates/web/components/charts/` directory
4. Add loading states and empty states

**Effort:** XL

### Phase 6: Integrations Pages Alignment

**Objective:** Ensure integrations pages match the design system.

1. Update `integrations/home.html` card styling
2. Update `integrations/github_repos.html`
3. Update `integrations/github_members.html`
4. Update component partials
5. Ensure consistent button and badge styling

**Effort:** M

### Phase 7: Authentication Pages

**Objective:** Polish login/signup/account pages.

1. Update `account/base.html` with brand styling
2. Polish login page
3. Polish signup page
4. Polish password reset flow
5. Update `allauth/elements/` components

**Effort:** M

### Phase 8: Error Pages & Edge Cases

**Objective:** Ensure error states are on-brand.

1. Update `400.html`, `403.html`, `404.html`, `429.html`, `500.html`
2. Create consistent error messaging components
3. Polish empty states throughout the app

**Effort:** S

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing functionality | High | Test each template change, maintain component API |
| CSS specificity conflicts | Medium | Use consistent class naming, avoid !important |
| Mobile responsiveness regression | Medium | Test on multiple viewport sizes |
| Accessibility degradation | High | Ensure color contrast ratios, focus states |
| Performance impact from animations | Low | Use `prefers-reduced-motion` |

---

## Success Metrics

1. **Visual Consistency Score:** All pages use the same color palette
2. **Component Reuse:** 80%+ of UI uses standardized components
3. **User Flow Smoothness:** No jarring transitions between pages
4. **Accessibility:** WCAG AA color contrast compliance
5. **Performance:** No increase in page load time

---

## Required Resources

- **Templates:** All files in `templates/` directory
- **CSS:** `assets/styles/` directory
- **JavaScript:** Alpine.js components in templates
- **Images:** `static/images/` for any new icons/graphics
- **Fonts:** Already configured (JetBrains Mono, DM Sans)

---

## Dependencies

- Phase 2 depends on Phase 1 (design system)
- Phases 3-8 can run in parallel after Phase 2
- Phase 5 (Dashboard) is the largest effort and can be split into sub-phases
