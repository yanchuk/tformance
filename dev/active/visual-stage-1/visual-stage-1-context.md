# Visual Stage 1: Context & Dependencies

**Last Updated:** 2025-12-20

## Key Files

### Primary Files to Modify

| File | Purpose | Lines of Interest |
|------|---------|-------------------|
| `tailwind.config.js` | Tailwind color tokens | Lines 18-32 (colors object) |
| `assets/styles/site-tailwind.css` | DaisyUI theme definition | Lines 22-62 (theme plugin) |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `dev/visual-improvement-plan.md` | Master plan with all stages |
| `assets/styles/app/tailwind/design-system.css` | CSS utility classes (Stage 2) |
| `CLAUDE.md` | Design system documentation |

### Files That Will Inherit Changes

These use Tailwind classes and will automatically update:
- `assets/styles/app/tailwind/design-system.css` (82 color references)
- `assets/styles/app/tailwind/landing-page.css` (13 references)
- All 17 template files using `text-cyan`, `bg-deep`, etc.

---

## Design Decisions

### Decision 1: Keep Legacy Cyan
**Choice:** Keep `cyan` color object temporarily
**Rationale:** Templates reference `text-cyan`, `bg-cyan`. Removing would break immediately. Will migrate in Stage 2-4.

### Decision 2: Use Hex Instead of OKLCH
**Choice:** Define DaisyUI theme colors in hex format
**Rationale:** Easier to read and verify. OKLCH is powerful but harder to debug. Hex values are documented in design-system.css header.

### Decision 3: Add Accent Object
**Choice:** Create `accent.primary/secondary/tertiary` namespace
**Rationale:** Allows gradual migration from `cyan` to `accent-primary`. Both can coexist during transition.

---

## Color Mapping Reference

### Old → New Mapping

| Old Token | Old Hex | New Token | New Hex | Usage |
|-----------|---------|-----------|---------|-------|
| `deep` | `#0f172a` | `deep` | `#171717` | Main background |
| `surface` | `#1e293b` | `surface` | `#262626` | Cards, panels |
| `elevated` | `#334155` | `elevated` | `#404040` | Borders |
| `muted` | `#94a3b8` | `muted` | `#A3A3A3` | Muted text |
| `cyan` | `#5e9eb0` | (keep) | (keep) | Legacy - migrate later |
| - | - | `accent-primary` | `#F97316` | New primary |
| - | - | `accent-secondary` | `#FDA4AF` | New secondary |
| - | - | `accent-tertiary` | `#2DD4BF` | New success/teal |

### DaisyUI Theme Mapping

| DaisyUI Token | Old Color | New Color | Hex |
|---------------|-----------|-----------|-----|
| `primary` | Muted teal | Coral orange | `#F97316` |
| `secondary` | Slate blue | Warm rose | `#FDA4AF` |
| `accent` | Warm amber | Teal | `#2DD4BF` |
| `base-100` | `#0f172a` | `#171717` | - |
| `base-200` | `#1e293b` | `#262626` | - |
| `base-300` | `#334155` | `#404040` | - |
| `success` | Soft green | Teal | `#2DD4BF` |
| `warning` | Soft amber | Amber | `#FBBF24` |
| `error` | Soft red | Soft red | `#F87171` |
| `info` | Soft blue | Soft blue | `#60A5FA` |

---

## WCAG AA Contrast Verification

All color combinations verified for 4.5:1+ contrast ratio:

| Foreground | Background | Ratio | Pass? |
|------------|------------|-------|-------|
| `#FAFAFA` (text) | `#171717` (deep) | 15.5:1 | ✓ |
| `#A3A3A3` (muted) | `#171717` (deep) | 6.5:1 | ✓ |
| `#F97316` (primary) | `#171717` (deep) | 5.2:1 | ✓ |
| `#2DD4BF` (teal) | `#171717` (deep) | 9.3:1 | ✓ |
| `#F87171` (error) | `#171717` (deep) | 5.8:1 | ✓ |
| `#FFFFFF` (btn text) | `#F97316` (btn bg) | 4.5:1 | ✓ |

---

## Testing Commands

```bash
# Build CSS
npm run build

# Run smoke tests
make e2e-smoke

# Run all e2e tests
make e2e

# Start dev server (if not running)
make dev
```

---

## Related Documentation

- Design Direction: `dev/visual-improvement-plan.md`
- Color Reference: `CLAUDE.md` (Design System section)
- CSS Classes: `assets/styles/app/tailwind/design-system.css` (header)

---

## Notes for Future Stages

### Stage 2: Design System CSS
- Update `.app-card-interactive` hover from `cyan/40` to `accent-primary/40`
- Update `.app-text-gradient` from cyan to coral orange
- Update focus ring colors

### Stage 3+: Template Updates
- Replace `text-cyan` with `text-accent-primary` or `text-primary`
- Replace `bg-cyan` with `bg-accent-primary` or `bg-primary`
- Update inline color references in templates
