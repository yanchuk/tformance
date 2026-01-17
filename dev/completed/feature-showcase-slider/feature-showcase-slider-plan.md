# Feature Showcase Slider - Implementation Plan

**Last Updated**: 2025-01-15

## Executive Summary

Add an interactive feature showcase slider to the Tformance homepage to highlight key platform capabilities. The slider presents feature cards on the left with corresponding screenshots on the right, auto-rotating with pause-on-hover behavior.

**Key Decision**: Insert **after `pain_points.html`** (not replace `features_grid.html` which isn't currently used) - follows problem → solution narrative flow.

## Current State Analysis

### Landing Page Structure
```
templates/web/landing_page.html
├── report_banner.html
├── hero_terminal.html
├── pain_points.html        ← INSERT SLIDER HERE
├── how_it_works.html
├── what_you_get.html
├── data_transparency.html
├── security.html
├── built_with_you.html
├── faq.html
└── cta_terminal.html
```

### Relevant Patterns Found
- **Hero Terminal**: Uses promise-based `delay()` for rotation (better than `setInterval`)
- **Thumbs Rating**: Shows component registration pattern with `window.Alpine.data()`
- **PR Table**: Uses `x-transition` for smooth enter/leave animations
- **Design System**: DaisyUI theme tokens, no hardcoded colors

## Proposed Future State

### Features to Highlight (4 cards)

| # | Feature | Description | Screenshot |
|---|---------|-------------|------------|
| 1 | Team Performance & Load | Track each contributor's throughput, cycle time, and review load | `team-performance.webp` |
| 2 | Insights | Surface key trends and catch anomalies before they become problems | `insights.webp` |
| 3 | AI Adoption | Track AI tool usage and measure its impact on delivery | `ai-adoption.webp` |
| 4 | Integrations | *Coming Soon* - Connect Slack, Jira, and more | `integrations.webp` |

### Component Behavior
- Auto-rotates every 5 seconds
- Pauses on hover
- Click card to jump to feature
- Smooth crossfade transitions (x-transition)
- Respects `prefers-reduced-motion`
- Keyboard accessible (arrow keys)
- Screen reader friendly (ARIA)

## Implementation Phases

### Phase 1: Alpine.js Component (Effort: M)

**File**: `assets/javascript/components/feature-slider.js`

```javascript
export function registerFeatureSlider() {
  if (!window.Alpine) {
    console.warn('Alpine not found, skipping featureSlider registration');
    return;
  }

  window.Alpine.data('featureSlider', () => ({
    slides: [],
    currentSlide: 0,
    isPaused: false,
    autoplayActive: false,

    init() {
      // Parse slides from data attribute
      try {
        this.slides = this.$el.dataset.slides
          ? JSON.parse(this.$el.dataset.slides)
          : [];
      } catch (e) {
        console.warn('Failed to parse slides:', e);
        this.slides = [];
      }

      // Preload all images
      this.preloadImages();

      // Respect reduced motion preference
      if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        this.isPaused = true;
        return;
      }

      this.startAutoplay();
    },

    preloadImages() {
      this.slides.forEach(slide => {
        const img = new Image();
        img.src = slide.image;
      });
    },

    async startAutoplay() {
      this.autoplayActive = true;
      while (this.autoplayActive) {
        await this.delay(5000);
        if (!this.isPaused && this.autoplayActive) {
          this.next();
        }
      }
    },

    delay(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    },

    next() {
      this.currentSlide = (this.currentSlide + 1) % this.slides.length;
    },

    prev() {
      this.currentSlide = (this.currentSlide - 1 + this.slides.length) % this.slides.length;
    },

    goToSlide(index) {
      this.currentSlide = index;
    },

    pauseAutoplay() {
      this.isPaused = true;
    },

    resumeAutoplay() {
      this.isPaused = false;
    },

    destroy() {
      this.autoplayActive = false;
    }
  }));
}
```

### Phase 2: Template Partial (Effort: M)

**File**: `templates/web/components/feature_showcase.html`

Key requirements:
- Two-column grid (`lg:grid-cols-2`)
- Left: Feature cards with active state
- Right: Screenshot with crossfade
- ARIA attributes for accessibility
- Responsive (stack on mobile)

### Phase 3: Asset Setup (Effort: S)

**Directory**: `static/images/features/`

```
static/images/features/
├── team-performance.webp    (optimized)
├── team-performance.png     (fallback)
├── insights.webp
├── insights.png
├── ai-adoption.webp
├── ai-adoption.png
└── integrations.webp        (mockup)
```

**Image Requirements**:
- Primary: WebP format (50-70% smaller than PNG)
- Fallback: PNG for older browsers
- Dimensions: 1200×800px (16:10 aspect ratio)
- Mobile: Consider 600×400px variants

### Phase 4: Integration (Effort: S)

1. Register component in `assets/javascript/alpine.js`
2. Add include to `templates/web/landing_page.html` after `pain_points.html`
3. Verify Vite builds correctly

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Image loading causes layout shift | High | Medium | Fixed aspect ratio container + skeleton |
| Autoplay annoys users | Medium | Low | Honor `prefers-reduced-motion` |
| Component breaks after HTMX swap | Low | High | Use `destroy()` cleanup method |
| Screenshots become stale | Medium | Medium | Document update process |
| Mobile performance | Medium | Medium | WebP + lazy loading |

## Accessibility Requirements

- `role="region"` on container
- `aria-roledescription="carousel"`
- `aria-label="Feature showcase"`
- `aria-live="polite"` (off when paused)
- `role="tablist"` on card container
- `role="tab"` + `aria-selected` on each card
- Keyboard: Arrow keys for navigation
- Focus visible states

## Success Metrics

- [ ] Auto-rotate works (5s interval)
- [ ] Hover pauses rotation
- [ ] Click selects correct feature
- [ ] Keyboard navigation works
- [ ] Screen reader announces changes
- [ ] Respects reduced motion preference
- [ ] Images preload without flash
- [ ] Works after HTMX navigation
- [ ] Responsive on mobile

## Verification Plan

Use Playwright MCP to verify:
1. Navigate to homepage
2. Wait for slider to load
3. Verify auto-rotation (wait 6s, check slide changed)
4. Hover and verify pause
5. Click different card and verify selection
6. Check accessibility tree for ARIA
7. Test on mobile viewport
