# Visual Stage 2: Design System CSS Classes

**Last Updated:** 2025-12-20
**Status:** NOT STARTED
**Depends On:** Stage 1 (COMPLETED)

## Executive Summary

Stage 2 updates the CSS utility classes in `design-system.css` to use the new warm color tokens established in Stage 1. This involves replacing 60+ legacy color references (cyan, slate-*, emerald-*, rose-*) with the new accent color system while maintaining backwards compatibility and WCAG AA accessibility compliance.

## Current State Analysis

### Stage 1 Findings

From the design review, 60+ CSS classes still reference legacy colors:

| Legacy Token | Count | Replacement |
|--------------|-------|-------------|
| `cyan` (all variants) | 22 | `accent-primary` |
| `slate-*` | 32 | `neutral-*` or DaisyUI semantic |
| `emerald-*` | 4 | `accent-tertiary` |
| `rose-*` | 6 | `accent-error` |

### Key Classes Requiring Updates

1. **Interactive Elements**: `.app-card-interactive`, `.app-stat-card` - hover states
2. **Buttons**: `.app-btn-primary`, `.app-btn-secondary` - colors and focus rings
3. **Form Inputs**: `.app-input`, `.app-select`, `.app-textarea` - focus states
4. **Navigation**: `.app-sidebar-item-active` - active states
5. **Badges**: `.app-badge-primary`, `.app-badge-success` - background colors
6. **Alerts**: `.app-alert-info`, `.app-alert-success` - colors
7. **Progress**: `.app-progress-bar`, `.app-step-indicator` - fill colors
8. **Text**: `.app-text-accent`, `.app-text-gradient` - accent colors

## Proposed Future State

All CSS utility classes will use the new warm color system:
- `cyan` → `accent-primary` (coral orange #F97316)
- `cyan-dark` → `orange-600` (darker coral)
- `cyan-light` → `pink-500` (for gradients)
- `emerald-400` → `accent-tertiary` (teal #2DD4BF)
- `rose-400` → `accent-error` (soft red #F87171)
- `slate-*` → `neutral-*` (warm neutrals)

## Implementation Phases

### Phase 1: Interactive Hover States (10 min)
Update hover effects on cards and interactive elements.

### Phase 2: Buttons & Focus Rings (15 min)
Update button colors and focus ring styles.

### Phase 3: Form Inputs (10 min)
Update input focus states and checkbox colors.

### Phase 4: Navigation (5 min)
Update sidebar active states.

### Phase 5: Badges & Alerts (10 min)
Update badge and alert color schemes.

### Phase 6: Progress & Steps (5 min)
Update progress bar and step indicator colors.

### Phase 7: Text Utilities (5 min)
Update text accent and gradient classes.

### Phase 8: Slate to Neutral Migration (15 min)
Replace all slate-* references with neutral-* equivalents.

### Phase 9: Validation (10 min)
Build and test all changes.

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing templates | Low | Medium | Slate→Neutral maintains same visual appearance |
| WCAG contrast failures | Low | High | All new colors pre-verified for 4.5:1+ |
| CSS build errors | Low | Low | Run `npm run build` after each phase |
| Flaky e2e tests | Medium | Low | Run failing tests in isolation |

## Success Metrics

1. `npm run build` succeeds without errors
2. `make e2e-smoke` passes (6/6 tests)
3. `make e2e` passes (185+ tests)
4. No browser console CSS errors
5. Visual verification: warm colors applied consistently

## Required Resources

- **File to Modify**: `assets/styles/app/tailwind/design-system.css`
- **Testing**: `make e2e-smoke`, `make e2e`
- **Time Estimate**: ~85 minutes total
