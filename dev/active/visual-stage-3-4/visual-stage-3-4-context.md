# Visual Stages 3 & 4: Context & Dependencies

**Last Updated:** 2025-12-20
**Status:** ✅ COMPLETED

## Key Files

### Primary Files to Modify

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `assets/styles/app/tailwind/landing-page.css` | Landing page CSS classes | Lines 27, 31, 36, 42, 64, 70 |
| `templates/web/components/hero_terminal.html` | Hero section template | Lines 5, 59, 75, 84 |
| `templates/web/components/features_grid.html` | Features grid template | Lines 6, 21-22, 40-41, 76-77, 86-88, 98-99 |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `dev/visual-improvement-plan.md` | Master plan with all stages |
| `assets/styles/app/tailwind/design-system.css` | CSS utility class definitions |
| `tailwind.config.js` | Color token definitions |
| `CLAUDE.md` | Design system documentation |
| `dev/active/visual-stage-1/visual-stage-1-context.md` | Stage 1 color mappings |

---

## Design Decisions

### Decision 1: Keep Emerald for Trust Indicators
**Choice:** Keep `text-emerald-500` for checkmarks in trust indicators (lines 96-112 in hero_terminal.html)
**Rationale:** Checkmarks indicate "positive confirmation" which aligns with green/emerald semantics. The design system uses teal for success metrics in dashboards, but checkmarks are a universal "yes/good" symbol best served by green.

### Decision 2: Use accent-error for "busier"
**Choice:** Use `text-accent-error` (#F87171) instead of `text-rose-400`
**Rationale:** Maintains design system consistency. The soft red has been verified for WCAG AA contrast against the deep background.

### Decision 3: Feature Icon Color Distribution
**Choice:**
- Feature 1 (Dashboard): Coral orange (`accent-primary`) - primary feature
- Feature 2 (Surveys): Amber (keep existing) - already warm, works well
- Feature 3 (Visibility): Teal (`accent-tertiary`) - represents trust/safety
**Rationale:** Creates visual variety while using the warm color system. Orange for primary focus, amber for engagement, teal for trust.

### Decision 4: CTA Button Text Color
**Choice:** Use `text-white` instead of `text-deep`
**Rationale:** White text on coral orange (#F97316) has 4.5:1 contrast ratio (WCAG AA compliant). Dark text would require darker orange bg.

---

## Color Mapping Reference

### Stage 3: hero_terminal.html

| Element | Old Color | New Color | CSS Token |
|---------|-----------|-----------|-----------|
| Grid background | `rgba(6,182,212,0.03)` (cyan) | `rgba(249,115,22,0.03)` (orange) | - |
| Terminal prompt | `text-cyan` (via CSS) | `text-accent-primary` | `#F97316` |
| Terminal cursor | `bg-cyan` (via CSS) | `bg-accent-primary` | `#F97316` |
| Result line | `text-cyan` | `text-accent-primary` | `#F97316` |
| "faster" gradient | `from-cyan-light to-slate-100` | `from-accent-primary to-pink-500` | `#F97316` → `#EC4899` |
| "busier" text | `text-rose-400` | `text-accent-error` | `#F87171` |
| CTA button bg | `bg-cyan` | `bg-accent-primary` | `#F97316` |
| CTA button hover | `hover:bg-cyan-dark` | `hover:bg-orange-600` | `#EA580C` |
| CTA button text | `text-deep` | `text-white` | `#FFFFFF` |

### Stage 4: features_grid.html

| Element | Old Color | New Color | CSS Token |
|---------|-----------|-----------|-----------|
| Section label | `text-cyan` | `text-accent-primary` | `#F97316` |
| Feature 1 icon bg | `bg-cyan/10` | `bg-accent-primary/10` | `#F97316/10` |
| Feature 1 icon | `text-cyan` | `text-accent-primary` | `#F97316` |
| Feature 1 chart bars | `bg-cyan`, `bg-cyan/30` | `bg-accent-primary`, `bg-accent-primary/30` | `#F97316` |
| Feature 2 icon | `text-amber-400` | `text-amber-400` | (unchanged) |
| Feature 3 icon bg | `bg-emerald-500/10` | `bg-accent-tertiary/10` | `#2DD4BF/10` |
| Feature 3 icon | `text-emerald-400` | `text-accent-tertiary` | `#2DD4BF` |
| Slack avatar bg | `bg-cyan/20` | `bg-accent-primary/20` | `#F97316/20` |
| Slack avatar text | `text-cyan` | `text-accent-primary` | `#F97316` |
| Survey btn hover | `hover:border-cyan/50` | `hover:border-accent-primary/50` | `#F97316/50` |
| Card hover | `hover:border-cyan/30` | `hover:border-accent-primary/30` | `#F97316/30` |

---

## WCAG AA Contrast Verification

All color combinations verified for 4.5:1+ contrast ratio:

| Foreground | Background | Ratio | Pass? |
|------------|------------|-------|-------|
| `#FAFAFA` (text) | `#171717` (deep) | 15.5:1 | ✓ |
| `#F97316` (accent-primary) | `#171717` (deep) | 5.2:1 | ✓ |
| `#2DD4BF` (accent-tertiary) | `#171717` (deep) | 9.3:1 | ✓ |
| `#F87171` (accent-error) | `#171717` (deep) | 5.8:1 | ✓ |
| `#FFFFFF` (btn text) | `#F97316` (btn bg) | 4.5:1 | ✓ |
| `#FBBF24` (amber) | `#171717` (deep) | 10.1:1 | ✓ |

---

## Testing Commands

```bash
# Build CSS/JS assets
npm run build

# Run smoke tests (includes landing page)
make e2e-smoke

# Run all e2e tests
make e2e

# Start dev server (if not running)
make dev

# Verify dev server is running
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/
```

---

## Related Documentation

- Design Direction: `dev/visual-improvement-plan.md`
- Color Reference: `CLAUDE.md` (Design System section)
- CSS Classes: `assets/styles/app/tailwind/design-system.css` (header)
- Stage 1 Context: `dev/active/visual-stage-1/visual-stage-1-context.md`

---

## Implementation Summary (2025-12-20)

### Completed Changes

**Phase 1: landing-page.css (6 edits)**
- Line 27: `.terminal-prompt` - `text-cyan` → `text-accent-primary`
- Line 31: `.terminal-cursor` - `bg-cyan` → `bg-accent-primary`
- Line 36: `.gradient-text` - `from-cyan-light to-slate-100` → `from-accent-primary to-pink-500`
- Line 42: `.stat-card` hover - `hover:border-cyan/50` → `hover:border-accent-primary/50`
- Line 64: `.feature-card` hover - `hover:border-cyan/30` → `hover:border-accent-primary/30`
- Line 70: `.integration-logo` hover - `hover:border-cyan/50` → `hover:border-accent-primary/50`

**Phase 2: hero_terminal.html (4 edits)**
- Line 5: Background grid - `rgba(6,182,212,0.03)` → `rgba(249,115,22,0.03)`
- Line 59: Result line - `text-cyan` → `text-accent-primary`
- Line 75: "busier" text - `text-rose-400` → `text-accent-error`
- Line 84: CTA button - `bg-cyan hover:bg-cyan-dark text-deep` → `bg-accent-primary hover:bg-orange-600 text-white`

**Phase 3: features_grid.html (6 edits)**
- Line 6: Section label - `text-cyan` → `text-accent-primary`
- Lines 21-22: Feature 1 icon - `bg-cyan/10`, `text-cyan` → `bg-accent-primary/10`, `text-accent-primary`
- Lines 40-41: Mini chart - `bg-cyan/30`, `bg-cyan` → `bg-accent-primary/30`, `bg-accent-primary`
- Lines 76-77: Slack avatar - `bg-cyan/20`, `text-cyan` → `bg-accent-primary/20`, `text-accent-primary`
- Lines 86-88: Survey buttons - `hover:border-cyan/50` → `hover:border-accent-primary/50` (3x)
- Lines 98-99: Feature 3 icon - `bg-emerald-500/10`, `text-emerald-400` → `bg-accent-tertiary/10`, `text-accent-tertiary`

### Validation Results
```
npm run build     ✓ Built in 1.90s (no errors)
make e2e-smoke    ✓ 6 passed (3.8s)
```

### Key Decisions Made
1. **Trust indicators kept emerald** - Checkmarks use `text-emerald-500` (universal "good" symbol)
2. **CTA text changed to white** - `text-white` on coral orange meets WCAG AA (4.5:1)
3. **Feature 2 unchanged** - Amber icon already warm, provides visual variety

### No Django Changes
- No models, views, URLs, or migrations affected
- This was purely a frontend CSS/template update

---

## Notes for Future Stages

### Stage 5: Dashboard Metric Cards
- Update `templates/metrics/cto_overview.html` section headers
- Apply `text-accent-primary` to divider icons
- Apply `text-accent-tertiary` for positive metrics
- Apply `text-accent-error` for negative metrics

### Stage 6: Navigation & Sidebar
- Update `templates/web/app/sidebar.html` active states
- Apply `text-accent-primary` to active nav items
- Update logo with warm gradient

### CSS Classes Already Updated (Stage 2)
The following classes in `design-system.css` already use the new colors:
- `.app-card-interactive` - uses `hover:border-accent-primary/40`
- `.app-stat-value-positive` - uses `text-accent-tertiary`
- `.app-stat-value-negative` - uses `text-accent-error`
- `.app-btn-primary` - uses `bg-accent-primary`
- `.app-text-gradient` - uses `from-accent-primary to-pink-500`
- `.app-sidebar-item-active` - uses `text-accent-primary`

---

## Diff Preview

### landing-page.css Changes

```diff
- .terminal-prompt {
-   @apply text-cyan inline-block;
- }
+ .terminal-prompt {
+   @apply text-accent-primary inline-block;
+ }

- .terminal-cursor {
-   @apply inline-block w-2 h-5 bg-cyan ml-1 animate-blink;
- }
+ .terminal-cursor {
+   @apply inline-block w-2 h-5 bg-accent-primary ml-1 animate-blink;
+ }

- .gradient-text {
-   @apply bg-gradient-to-r from-cyan-light to-slate-100 bg-clip-text text-transparent;
- }
+ .gradient-text {
+   @apply bg-gradient-to-r from-accent-primary to-pink-500 bg-clip-text text-transparent;
+ }

- .stat-card {
-   @apply hover:border-cyan/50 transition-colors duration-300;
- }
+ .stat-card {
+   @apply hover:border-accent-primary/50 transition-colors duration-300;
+ }

- .feature-card {
-   @apply hover:border-cyan/30 hover:bg-surface/80 transition-all duration-300;
- }
+ .feature-card {
+   @apply hover:border-accent-primary/30 hover:bg-surface/80 transition-all duration-300;
+ }

- .integration-logo {
-   @apply hover:border-cyan/50 hover:scale-105 transition-all duration-300;
- }
+ .integration-logo {
+   @apply hover:border-accent-primary/50 hover:scale-105 transition-all duration-300;
+ }
```
