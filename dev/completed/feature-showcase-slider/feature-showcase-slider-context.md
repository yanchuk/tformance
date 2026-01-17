# Feature Showcase Slider - Context

**Last Updated**: 2025-01-15

## Key Files

### Files to Create
| File | Purpose |
|------|---------|
| `assets/javascript/components/feature-slider.js` | Alpine.js component |
| `templates/web/components/feature_showcase.html` | Template partial |
| `static/images/features/*.webp` | Screenshot assets |

### Files to Modify
| File | Change |
|------|--------|
| `assets/javascript/alpine.js` | Register featureSlider component |
| `templates/web/landing_page.html` | Include new component |

### Reference Files (Patterns)
| File | Pattern |
|------|---------|
| `assets/javascript/components/thumbs-rating.js` | Component registration |
| `templates/web/components/hero_terminal.html` | Promise-based rotation |
| `templates/metrics/pull_requests/partials/table.html:217` | x-transition usage |
| `dev/guides/DESIGN-SYSTEM.md` | Color tokens |
| `dev/guides/FRONTEND-PATTERNS.md` | Alpine.js patterns |

## Key Decisions

### 1. Page Placement
**Decision**: Insert after `pain_points.html`
**Rationale**: Follows problem → solution narrative flow. `features_grid.html` is NOT currently included in landing page (plan reviewer finding).

### 2. Image Format
**Decision**: WebP primary + PNG fallback
**Rationale**: WebP is 50-70% smaller, supported by 97%+ browsers. PNG fallback for Safari < 14.

### 3. Rotation Timing
**Decision**: Promise-based `delay()` instead of `setInterval`
**Rationale**: Matches `hero_terminal.html` pattern, cleaner async flow, easier to pause/resume.

### 4. Transition Approach
**Decision**: Alpine.js `x-transition`
**Rationale**: Consistent with existing codebase patterns (PR table uses this).

### 5. Accessibility
**Decision**: Full ARIA support + keyboard nav + reduced motion
**Rationale**: Required for professional product, matches WCAG guidelines.

## Dependencies

### External
- User provides 4 screenshots (1200×800px PNG)
- Screenshots need WebP conversion

### Internal
- Alpine.js must be loaded (already is)
- Vite build must include new component
- Design system tokens available

## Technical Notes

### Alpine Component Registration Pattern
```javascript
// From thumbs-rating.js
export function registerFeatureSlider() {
  if (!window.Alpine) {
    console.warn('Alpine not found');
    return;
  }
  window.Alpine.data('featureSlider', () => ({ ... }));
}
```

### Data Attribute Pattern
```html
<div x-data="featureSlider"
     data-slides='{{ slides_json|escapejs }}'>
```

### Transition Pattern (from PR table)
```html
x-transition:enter="transition ease-out duration-200"
x-transition:enter-start="opacity-0"
x-transition:enter-end="opacity-100"
x-transition:leave="transition ease-in duration-150"
x-transition:leave-start="opacity-100"
x-transition:leave-end="opacity-0"
```

### Color Tokens (DO use)
- `text-base-content` - primary text
- `text-base-content/80` - secondary text
- `bg-base-200` - card backgrounds
- `border-base-300` - borders
- `text-primary` / `border-primary` - active state

### Color Tokens (DON'T use)
- `text-white`, `text-gray-*` - hardcoded
- `bg-accent-primary/10` - wrong format

## Open Items

- [ ] User provides screenshots
- [ ] Decide on mobile behavior (stack vs scroll)
- [ ] Finalize "Coming Soon" badge design
