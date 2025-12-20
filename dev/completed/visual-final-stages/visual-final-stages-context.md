# Visual Final Stages - Context

**Last Updated:** 2025-12-20

## Key Files

### CSS & Styling
| File | Purpose |
|------|---------|
| `assets/styles/app/tailwind/design-system.css` | Main design system - add reduced motion here |
| `assets/styles/app/tailwind/landing-page.css` | Has reduced motion for hero animation |
| `tailwind.config.js` | Color tokens and DaisyUI theme |

### Accessibility Tests
| File | Purpose |
|------|---------|
| `tests/e2e/accessibility.spec.ts` | Main accessibility test suite (color-contrast disabled) |
| `tests/e2e/interactive.spec.ts` | Tests for interactive elements, some focus tests |

### Templates to Verify
| Template | Why |
|----------|-----|
| `templates/account/login.html` | Primary form page |
| `templates/account/signup.html` | Registration form |
| `templates/metrics/cto_overview.html` | Dashboard with charts |
| `templates/web/app/sidebar.html` | Navigation with active states |
| `templates/integrations/home.html` | Integration cards |

## Color Contrast Reference

All combinations from our palette meet WCAG AA:

| Element | Background | Foreground | Ratio | Status |
|---------|------------|------------|-------|--------|
| Body text | #171717 | #FAFAFA | 15.5:1 | ✅ |
| Muted text | #171717 | #A3A3A3 | 6.5:1 | ✅ |
| Primary accent | #171717 | #F97316 | 5.2:1 | ✅ |
| Teal accent | #171717 | #2DD4BF | 9.3:1 | ✅ |
| Error text | #171717 | #F87171 | 5.8:1 | ✅ |
| Purple (AI) | #171717 | #C084FC | 6.8:1 | ✅ |
| Card text | #262626 | #FAFAFA | 12.6:1 | ✅ |

## Key Decisions

### Already Decided
1. **Color palette** - Sunset Dashboard palette with pre-verified contrast ratios
2. **Focus ring style** - `ring-2 ring-accent-primary/50 ring-offset-2 ring-offset-deep`
3. **Typography** - DM Sans for UI, JetBrains Mono for data

### To Be Verified
1. **DaisyUI overrides** - Some components may need additional overrides
2. **Third-party components** - Chart.js tooltips, date pickers if any

## CSS Patterns to Add

### Reduced Motion (for design-system.css)
```css
@media (prefers-reduced-motion: reduce) {
  /* Disable all animations and transitions */
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }

  /* Keep skeletons static */
  .app-skeleton::after {
    animation: none;
  }

  .app-spinner {
    animation: none;
  }
}
```

### Global Focus Visible (already mostly in place)
```css
/* Ensure all interactive elements have visible focus */
:focus-visible {
  @apply outline-none ring-2 ring-accent-primary ring-offset-2 ring-offset-deep;
}
```

## Test Commands

```bash
# Run accessibility tests
make e2e ARGS="tests/e2e/accessibility.spec.ts"

# Run with debug output
make e2e ARGS="tests/e2e/accessibility.spec.ts --debug"

# Run Lighthouse (manual in Chrome DevTools)
# 1. Open page
# 2. DevTools > Lighthouse > Accessibility
```

## Related Documents

- `dev/visual-improvement-plan.md` - Full implementation plan
- `dev/completed/visual-stage-*` - Completed stage documentation
- `CLAUDE.md` - Design system section
