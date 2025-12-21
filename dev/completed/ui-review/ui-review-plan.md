# UI Review Plan: Seeded Demo Data Verification

**Last Updated:** 2025-12-20

## Executive Summary

Comprehensive UI review of all pages displaying seeded demo data using Playwright MCP. Goal is to identify design inconsistencies, broken elements, and UX improvements following the "Sunset Dashboard" design system.

## Current State

**Seeded Data:** `ai-success` scenario with seed 42
- Team: "AI Pioneers" (5 members)
- 155 PRs, 79 surveys
- 8 weeks of data showing AI adoption 10%→75%

**Already Fixed:**
- ✅ PR titles showing NOT_PROVIDED - FIXED (commit 3e5c597)
- ✅ Team switcher lacks dropdown indicator - FIXED (commit 0b65b29)

**E2E Test Coverage (Existing):**
- `dashboard.spec.ts` - Comprehensive metrics page tests
- `teams.spec.ts` - Team navigation, team switcher dropdown
- `interactive.spec.ts` - HTMX, charts, tables, filters

---

## Scope

### Pages to Review (23+ views)

**Main Dashboards:**
| Page | URL | Priority |
|------|-----|----------|
| Team Home | `/app/` | High |
| CTO Overview | `/app/metrics/dashboard/cto/` | High |
| Team Dashboard | `/app/metrics/dashboard/team/` | High |

**Chart Components (HTMX loaded):**
- AI Adoption Trend chart
- AI Quality Comparison chart
- Cycle Time Trend chart
- Review Time Trend chart
- PR Size Distribution chart
- Review Distribution chart
- Copilot Acceptance Rate Trend chart

**Table Components:**
- Team Breakdown table (per-member stats)
- AI Detective Leaderboard
- Recent PRs table
- PRs Missing Jira Links table
- Reviewer Workload table
- Copilot Members table
- Reviewer Correlations table

**Card Components:**
- Key Metrics cards (PRs, Cycle Time, AI%, Quality)
- Revert/Hotfix Rate card
- Copilot Metrics card
- Iteration Metrics card
- Quick Stats (home page)

---

## Design System Reference

### Color Usage (CRITICAL)
| Element | Correct | Avoid |
|---------|---------|-------|
| Primary text | `text-base-content` | `text-white`, `text-stone-*` |
| Secondary text | `text-base-content/80` | `text-gray-400` |
| Card bg | `bg-base-200` | `bg-neutral-*`, `bg-surface` |
| Page bg | `bg-base-100` | `bg-deep` |
| Borders | `border-base-300` | `border-elevated` |
| Success | `text-accent` / `app-status-connected` | `text-green-*` |
| Error | `text-error` | `text-red-*` |
| Primary | `text-primary` / `bg-primary` | `text-orange-*` |

### Typography
- DM Sans for UI text/headings
- JetBrains Mono (`app-text-mono`) for metrics/data values

### Component Classes
- Cards: `app-card`, `app-card-interactive`
- Buttons: `app-btn-primary`, `app-btn-secondary`
- Stats: `app-stat-value`, `app-stat-value-positive`, `app-stat-value-negative`
- Status: `app-status-connected`, `app-badge-success`

---

## Implementation Phases

### Phase 1: Baseline Screenshots [Effort: S]
Capture screenshots of all main dashboards for reference.

1. Navigate to Team Home (`/app/`)
2. Take full-page screenshot
3. Navigate to CTO Overview (`/app/metrics/dashboard/cto/`)
4. Take full-page screenshot
5. Navigate to Team Dashboard (`/app/metrics/dashboard/team/`)
6. Take full-page screenshot

### Phase 2: Component Review - Team Home [Effort: M]
Review all components on the home page.

- Quick stats cards (PRs, Cycle Time, AI%, Quality)
- Recent activity feed (PR merges, surveys)
- Integration status cards
- Team overview stats
- Number formatting
- Trend indicators (↑/↓)

### Phase 3: Component Review - CTO Overview [Effort: L]
Review all components on the CTO dashboard.

- Key metrics cards with period comparison
- AI Adoption trend chart
- AI Quality comparison chart
- Copilot metrics section
- Cycle Time / Review Time charts
- PR Size Distribution chart
- Team Breakdown table
- Reviewer Workload table
- PRs Missing Jira table

### Phase 4: Component Review - Team Dashboard [Effort: M]
Review all components on the team dashboard.

- Key metrics cards
- Cycle Time / Review Time charts
- PR Size Distribution
- Review Distribution chart
- AI Detective Leaderboard
- Recent PRs table
- Reviewer Workload table

### Phase 5: Interaction Testing [Effort: M]
Test all interactive elements.

- Date range filter changes
- Theme toggle (light/dark mode)
- Team switcher dropdown
- HTMX partial loads (no flicker)
- Hover states

### Phase 6: User Flow Testing & E2E Coverage [Effort: L]
Test key user journeys and add missing E2E tests.

**Dashboard Navigation Flows:**
- User logs in → lands on Team Home → sees stats
- User clicks "View Analytics" → navigates to Team Dashboard
- User clicks "Analytics" in sidebar → navigates to dashboard
- User changes date range filter → charts/tables update

**Missing E2E Tests to Add:**
- Theme toggle test
- Metric value formatting test
- Empty state handling test

### Phase 7: Document & Fix Issues [Effort: M-L]
Categorize and fix issues by severity.

- 🔴 **Critical** - Broken functionality
- 🟠 **Major** - Design inconsistencies, wrong colors
- 🟡 **Minor** - Small improvements
- 🟢 **Enhancement** - Nice-to-have

---

## Success Metrics

1. All 3 main dashboards reviewed with screenshots
2. All design system violations identified and fixed
3. All broken UI elements fixed
4. Missing E2E tests added (theme toggle, metric formatting)
5. Zero critical issues remaining

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Design system violations widespread | Medium | Batch similar fixes together |
| HTMX components not loading | High | Check network requests, verify endpoints |
| Theme toggle broken | Medium | Test CSS variable inheritance |
| Charts not rendering | High | Verify Chart.js initialization |

---

## Output Deliverables

1. Categorized list of issues found (by severity)
2. Screenshots of problematic areas saved to `.playwright-mcp/`
3. Specific fixes implemented for each issue
4. New E2E tests for missing coverage
5. Updated dev-docs with session notes
