# Visual Stages 3-9: Parallel Execution Prompts

**Created:** 2025-12-20
**For:** Running in parallel git worktrees

## Setup Instructions

```bash
# Create worktrees for parallel work
git worktree add ../tformance-landing visual-landing
git worktree add ../tformance-dashboard visual-dashboard
git worktree add ../tformance-chrome visual-chrome

# Run each prompt in its respective worktree
cd ../tformance-landing && claude
cd ../tformance-dashboard && claude
cd ../tformance-chrome && claude
```

## Reference Files (Read These First)

All prompts reference:
- **Master Plan:** `dev/visual-improvement-plan.md` (full stage descriptions)
- **Stage 1 Context:** `dev/active/visual-stage-1/visual-stage-1-context.md` (color mappings)
- **Stage 2 Context:** `dev/active/visual-stage-2/visual-stage-2-context.md` (CSS class updates)
- **Design System:** `CLAUDE.md` (Design System section)

---

## Prompt 1: Landing Page (Stages 3 + 4)

Copy and paste this into Claude Code in the `tformance-landing` worktree:

```
/dev-docs Implement Visual Stages 3 and 4 from dev/visual-improvement-plan.md

## Context

You are implementing the "Sunset Dashboard" visual redesign. Stages 1-2 are complete:
- Color tokens updated in tailwind.config.js
- CSS utility classes updated in design-system.css
- New warm color system: accent-primary (#F97316 coral), accent-tertiary (#2DD4BF teal), accent-error (#F87171)

## Reference Files

- Master plan: dev/visual-improvement-plan.md (see Stages 3 and 4)
- Color mappings: dev/active/visual-stage-1/visual-stage-1-context.md
- CSS reference: dev/active/visual-stage-2/visual-stage-2-context.md

## Stage 3: Landing Page Hero Update

File: templates/web/components/hero_terminal.html

Tasks:
- Update terminal prompt color to accent-primary (coral orange)
- Update headline gradient to warm gradient (coral to pink)
- Update "busier" text to accent-error (soft red)
- Update CTA button to bg-accent-primary hover:bg-orange-600 text-white

## Stage 4: Features Grid Update

File: templates/web/components/features_grid.html

Tasks:
- Update first feature icon to accent-primary (coral orange)
- Keep second feature icon amber (already warm)
- Update third feature icon to accent-tertiary (teal)
- Update feature card hover states to hover:border-accent-primary/50

## Validation

After each stage:
1. npm run build
2. make e2e-smoke
3. Visual check of landing page at localhost:8000

Create task files in dev/active/visual-stages-3-4/
```

---

## Prompt 2: Dashboard (Stages 5 + 9)

Copy and paste this into Claude Code in the `tformance-dashboard` worktree:

```
/dev-docs Implement Visual Stages 5 and 9 from dev/visual-improvement-plan.md

## Context

You are implementing the "Sunset Dashboard" visual redesign. Stages 1-2 are complete:
- Color tokens updated in tailwind.config.js
- CSS utility classes updated in design-system.css
- New warm color system: accent-primary (#F97316 coral), accent-tertiary (#2DD4BF teal), accent-error (#F87171)

## Reference Files

- Master plan: dev/visual-improvement-plan.md (see Stages 5 and 9)
- Color mappings: dev/active/visual-stage-1/visual-stage-1-context.md
- CSS reference: dev/active/visual-stage-2/visual-stage-2-context.md

## Stage 5: Dashboard Metric Cards

Files:
- templates/metrics/cto_overview.html
- templates/metrics/partials/*.html

Tasks:
- Update section header icons to accent-primary (coral orange)
- Update divider colors to use warm accents
- Verify stat cards use accent-tertiary for positive, accent-error for negative
- Update any remaining cyan references to accent-primary

## Stage 9: Empty States & Loading

Files:
- templates/*/partials/empty_state.html (search for empty state templates)
- Any loading skeleton components

Tasks:
- Update empty state icons to accent-primary/10 background with accent-primary icon
- Update CTA buttons in empty states to app-btn-primary
- Update loading skeleton shimmer to warm orange tint (if custom CSS exists)

## Validation

After each stage:
1. npm run build
2. make e2e-dashboard
3. Visual check of dashboard at localhost:8000/a/{team}/dashboard/

Create task files in dev/active/visual-stages-5-9/
```

---

## Prompt 3: App Chrome (Stages 6 + 8)

Copy and paste this into Claude Code in the `tformance-chrome` worktree:

```
/dev-docs Implement Visual Stages 6 and 8 from dev/visual-improvement-plan.md

## Context

You are implementing the "Sunset Dashboard" visual redesign. Stages 1-2 are complete:
- Color tokens updated in tailwind.config.js
- CSS utility classes updated in design-system.css
- New warm color system: accent-primary (#F97316 coral), accent-tertiary (#2DD4BF teal), accent-error (#F87171)

## Reference Files

- Master plan: dev/visual-improvement-plan.md (see Stages 6 and 8)
- Color mappings: dev/active/visual-stage-1/visual-stage-1-context.md
- CSS reference: dev/active/visual-stage-2/visual-stage-2-context.md

## Stage 6: Navigation & Sidebar

Files:
- templates/web/app/sidebar.html (or similar sidebar template)
- Any navigation components

Tasks:
- Update active sidebar item to text-accent-primary border-accent-primary
- Update sidebar hover states to use warm colors
- Update logo/brand element to warm gradient (from-accent-primary to-pink-500)
- Verify navigation links use correct active states

## Stage 8: Charts & Data Visualization

Files:
- assets/javascript/chart-theme.js (create if doesn't exist)
- Any inline chart configurations in templates

Tasks:
- Create/update chart theme with warm colors:
  - primary: #F97316 (coral orange)
  - secondary: #FDA4AF (warm rose)
  - success: #2DD4BF (teal)
  - warning: #FBBF24 (amber)
  - ai: #C084FC (soft purple for AI metrics)
- Update grid and tooltip colors to match warm neutrals
- Apply theme to any Chart.js instances

## Validation

After each stage:
1. npm run build
2. make e2e-auth (tests navigation)
3. make e2e-dashboard (tests charts)
4. Visual check of sidebar and charts

Create task files in dev/active/visual-stages-6-8/
```

---

## After Parallel Work Completes

Once all 3 worktrees are done:

```bash
# Return to main repo
cd /path/to/tformance

# Merge all branches
git merge visual-landing
git merge visual-dashboard
git merge visual-chrome

# Run full validation
npm run build
make e2e

# Then proceed with Stage 10 (Accessibility) and Stage 11 (Final)
```

---

## Stage 7 Note

Stage 7 (Buttons & Form Elements) was largely completed in Stage 2. Verify by checking:
```bash
grep -r "cyan\|slate-" assets/styles/app/tailwind/design-system.css
```

If any remain, include in whichever parallel track makes sense.
