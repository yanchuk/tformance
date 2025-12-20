# Visual Stage 2: Context & Dependencies

**Last Updated:** 2025-12-20

## Key Files

### Primary File to Modify

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `assets/styles/app/tailwind/design-system.css` | CSS utility classes | All 610 lines |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `dev/visual-improvement-plan.md` | Master plan with all stages |
| `tailwind.config.js` | Color token definitions |
| `assets/styles/site-tailwind.css` | DaisyUI theme |
| `CLAUDE.md` | Design system documentation |

---

## Color Replacement Reference

### Cyan → Accent Primary (Coral Orange)

| Old | New | Context |
|-----|-----|---------|
| `cyan` | `accent-primary` | Main accent color |
| `cyan-dark` | `orange-600` | Darker variant (hover) |
| `cyan-light` | `pink-500` | Lighter variant (gradients) |
| `cyan/40` | `accent-primary/40` | Opacity variants |
| `cyan/50` | `accent-primary/50` | Focus rings |
| `cyan/10` | `accent-primary/10` | Subtle backgrounds |
| `cyan/20` | `accent-primary/20` | Badge backgrounds |
| `cyan/30` | `accent-primary/30` | Alert borders |

### Status Colors

| Old | New | Usage |
|-----|-----|-------|
| `emerald-400` | `accent-tertiary` | Positive metrics, success |
| `emerald-500/20` | `accent-tertiary/20` | Success badges |
| `emerald-500/10` | `accent-tertiary/10` | Success alerts |
| `emerald-500/30` | `accent-tertiary/30` | Success borders |
| `rose-400` | `accent-error` | Negative metrics, errors |
| `rose-600` | `red-600` | Danger button bg |
| `rose-700` | `red-700` | Danger button hover |
| `rose-500/20` | `accent-error/20` | Error badges |
| `rose-500/10` | `accent-error/10` | Error alerts |
| `rose-500/30` | `accent-error/30` | Error borders |

### Slate → Neutral Migration

| Old | New | Usage |
|-----|-----|-------|
| `slate-100` | `neutral-100` | Light text on dark |
| `slate-200` | `neutral-200` | Secondary light text |
| `slate-300` | `neutral-300` | Tertiary text |
| `slate-400` | `neutral-400` | Muted text |
| `slate-500` | `neutral-500` | Very muted |
| `slate-600` | `neutral-600` | Borders, dividers |

---

## Classes by Category

### Interactive Cards (Lines 82-86, 117-120)

```css
/* BEFORE */
.app-card-interactive {
  @apply hover:border-cyan/40 transition-colors duration-200;
}
.app-stat-card {
  @apply hover:border-cyan/40 transition-colors duration-200;
}

/* AFTER */
.app-card-interactive {
  @apply hover:border-accent-primary/40 transition-colors duration-200;
}
.app-stat-card {
  @apply hover:border-accent-primary/40 transition-colors duration-200;
}
```

### Buttons (Lines 163-193)

```css
/* BEFORE */
.app-btn-* {
  @apply focus:ring-cyan/50 focus:ring-offset-deep;
}
.app-btn-primary {
  @apply bg-cyan hover:bg-cyan-dark text-deep;
}

/* AFTER */
.app-btn-* {
  @apply focus:ring-accent-primary/50 focus:ring-offset-deep;
}
.app-btn-primary {
  @apply bg-accent-primary hover:bg-orange-600 text-white;
}
```

### Form Inputs (Lines 214-249)

```css
/* BEFORE */
.app-input, .app-select, .app-textarea {
  @apply focus:border-cyan focus:ring-cyan/50;
}
.app-checkbox {
  @apply text-cyan focus:ring-cyan;
}

/* AFTER */
.app-input, .app-select, .app-textarea {
  @apply focus:border-accent-primary focus:ring-accent-primary/50;
}
.app-checkbox {
  @apply text-accent-primary focus:ring-accent-primary;
}
```

### Sidebar Navigation (Lines 298-301)

```css
/* BEFORE */
.app-sidebar-item-active {
  @apply bg-deep text-cyan border-l-2 border-cyan;
}

/* AFTER */
.app-sidebar-item-active {
  @apply bg-deep text-accent-primary border-l-2 border-accent-primary;
}
```

### Badges (Lines 326-340)

```css
/* BEFORE */
.app-badge-primary { @apply bg-cyan/20 text-cyan; }
.app-badge-success { @apply bg-emerald-500/20 text-emerald-400; }
.app-badge-danger { @apply bg-rose-500/20 text-rose-400; }

/* AFTER */
.app-badge-primary { @apply bg-accent-primary/20 text-accent-primary; }
.app-badge-success { @apply bg-accent-tertiary/20 text-accent-tertiary; }
.app-badge-danger { @apply bg-accent-error/20 text-accent-error; }
```

### Alerts (Lines 376-390)

```css
/* BEFORE */
.app-alert-info { @apply bg-cyan/10 border-cyan/30 text-cyan; }
.app-alert-success { @apply bg-emerald-500/10 border-emerald-500/30 text-emerald-400; }
.app-alert-error { @apply bg-rose-500/10 border-rose-500/30 text-rose-400; }

/* AFTER */
.app-alert-info { @apply bg-accent-primary/10 border-accent-primary/30 text-accent-primary; }
.app-alert-success { @apply bg-accent-tertiary/10 border-accent-tertiary/30 text-accent-tertiary; }
.app-alert-error { @apply bg-accent-error/10 border-accent-error/30 text-accent-error; }
```

### Progress & Steps (Lines 402-443)

```css
/* BEFORE */
.app-progress-bar { @apply bg-cyan; }
.app-step-indicator-active { @apply bg-cyan text-deep; }
.app-step-label-active { @apply text-cyan; }
.app-step-connector-complete { @apply bg-cyan; }

/* AFTER */
.app-progress-bar { @apply bg-accent-primary; }
.app-step-indicator-active { @apply bg-accent-primary text-white; }
.app-step-label-active { @apply text-accent-primary; }
.app-step-connector-complete { @apply bg-accent-primary; }
```

### Text Utilities (Lines 515-528)

```css
/* BEFORE */
.app-text-accent { @apply text-cyan; }
.app-text-gradient {
  @apply bg-gradient-to-r from-cyan to-cyan-light bg-clip-text text-transparent;
}

/* AFTER */
.app-text-accent { @apply text-accent-primary; }
.app-text-gradient {
  @apply bg-gradient-to-r from-accent-primary to-pink-500 bg-clip-text text-transparent;
}
```

---

## Testing Commands

```bash
# Build CSS (run after each phase)
npm run build

# Quick smoke test
make e2e-smoke

# Full e2e tests
make e2e

# Dashboard-specific tests
make e2e-dashboard
```

---

## Related Documentation

- Stage 1 Context: `dev/active/visual-stage-1/visual-stage-1-context.md`
- Master Plan: `dev/visual-improvement-plan.md`
- Design System: `CLAUDE.md` (Design System section)
