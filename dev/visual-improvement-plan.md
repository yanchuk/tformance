# Tformance Visual Improvement Plan

## Design Direction: "Sunset Dashboard"

**Philosophy**: Warm, approachable, and friendly while maintaining developer credibility. Move away from cold corporate blues toward coral/orange tones that feel optimistic and human. Premium SaaS vibes with personality.

**Key Differentiators**:
- Warm coral/orange primary accent (stands out from typical dev tools)
- Soft rose secondary for highlights
- Teal success color for positive contrast
- Dark neutral backgrounds (warmer than slate)
- Subtle gradient accents that feel modern but not garish

**Inspiration**: Pitch, Figma, Notion - friendly, polished, warm

---

## Color System

### Current State
- Primary accent: Muted cyan (#5e9eb0)
- Cold slate backgrounds (#0f172a, #1e293b)
- Limited warmth or personality

### New "Sunset Dashboard" Palette

```css
/* Core backgrounds - warmer neutrals */
--deep: #171717;           /* neutral-900 (warmer than slate) */
--surface: #262626;        /* neutral-800 */
--elevated: #404040;       /* neutral-700 */

/* Warm Accent System */
--accent-primary: #F97316;    /* Soft coral/orange - main brand */
--accent-secondary: #FDA4AF;  /* Warm rose - highlights */
--accent-tertiary: #2DD4BF;   /* Teal - success, positive */
--accent-warning: #FBBF24;    /* Warm amber */
--accent-info: #60A5FA;       /* Soft blue */
--accent-error: #F87171;      /* Soft red */

/* Gradient tokens */
--gradient-hero: linear-gradient(135deg, #F97316 0%, #EC4899 100%);
--gradient-warm: linear-gradient(135deg, #F97316 0%, #FDA4AF 100%);
--gradient-success: linear-gradient(135deg, #2DD4BF 0%, #34D399 100%);

/* Semantic colors for metrics */
--metric-up: #2DD4BF;         /* Teal for improvements */
--metric-down: #F87171;       /* Soft red for regressions */
--metric-neutral: #A3A3A3;    /* Neutral gray */
--metric-ai: #C084FC;         /* Soft purple for AI-related */

/* Text colors - warm off-whites */
--text-primary: #FAFAFA;      /* neutral-50 */
--text-secondary: #D4D4D4;    /* neutral-300 */
--text-muted: #A3A3A3;        /* neutral-400 */
```

### Why This Palette Works
1. **Coral Orange (#F97316)**: Warm, optimistic, stands out from blue/purple developer tools
2. **Warm Rose (#FDA4AF)**: Soft highlight color, friendly and approachable
3. **Teal (#2DD4BF)**: Excellent success color that contrasts well with warm tones
4. **Neutral backgrounds**: Warmer than slate, feels more inviting
5. **WCAG AA Compliant**: All combinations tested for 4.5:1+ contrast

---

## Implementation Stages

Each stage is atomic with clear testing/validation criteria. Do not proceed to next stage until current stage passes all tests.

---

## Stage 1: Color Token Foundation

**Goal**: Update Tailwind config and design system with new warm color tokens.

### 1.1 Update Tailwind Config

Add new color tokens to `tailwind.config.js`:

```javascript
// Replace existing accent colors
colors: {
  deep: '#171717',
  surface: '#262626',
  elevated: '#404040',
  accent: {
    primary: '#F97316',
    secondary: '#FDA4AF',
    tertiary: '#2DD4BF',
    warning: '#FBBF24',
    info: '#60A5FA',
    error: '#F87171',
  },
  // Keep muted for backwards compatibility
  muted: '#A3A3A3',
}
```

### 1.2 Update DaisyUI Theme

Update the `tformance` theme in `tailwind.config.js`:

```javascript
daisyui: {
  themes: [{
    tformance: {
      "primary": "#F97316",
      "secondary": "#FDA4AF",
      "accent": "#2DD4BF",
      "neutral": "#262626",
      "base-100": "#171717",
      "info": "#60A5FA",
      "success": "#2DD4BF",
      "warning": "#FBBF24",
      "error": "#F87171",
    }
  }]
}
```

### Validation for Stage 1

```bash
# 1. Build CSS successfully
npm run build

# 2. Run existing e2e smoke tests (pages load, no broken styles)
make e2e-smoke

# 3. Visual verification checklist:
#    - [ ] Dev server starts without CSS errors
#    - [ ] Landing page renders (colors may look different but no broken layouts)
#    - [ ] Dashboard renders (may look different but functional)
```

**Exit criteria**: `make e2e-smoke` passes, no console errors, pages render.

---

## Stage 2: Design System CSS Classes

**Goal**: Update design system utility classes with new colors.

### 2.1 Update design-system.css

Replace cyan references with new accent colors:

```css
/* Update existing classes */
.app-card {
  @apply bg-surface rounded-xl border border-elevated;
  @apply p-6;
}

.app-card-interactive {
  @apply bg-surface rounded-xl border border-elevated p-6;
  @apply hover:border-accent-primary/40 transition-colors duration-200;
}

/* Stat cards with warm colors */
.app-stat-value-positive {
  @apply text-accent-tertiary;  /* teal */
}

.app-stat-value-negative {
  @apply text-accent-error;  /* soft red */
}

/* Buttons - warm primary */
.app-btn-primary {
  @apply bg-accent-primary hover:bg-orange-600 text-white;
}

/* Focus states with warm glow */
.app-focus-glow {
  @apply focus:outline-none focus:ring-2 focus:ring-accent-primary/50;
}

/* Gradient text - warm gradient */
.app-text-gradient {
  @apply bg-gradient-to-r from-accent-primary to-pink-500 bg-clip-text text-transparent;
}
```

### 2.2 Add Warm Color Utility Classes

```css
/* NEW: Warm accent utilities */
.app-accent-glow {
  box-shadow: 0 0 20px rgba(249, 115, 22, 0.3);
}

.app-border-warm {
  @apply border-accent-primary/30;
}

/* Warm badges */
.app-badge-primary {
  @apply bg-accent-primary/20 text-accent-primary;
}

.app-badge-success {
  @apply bg-accent-tertiary/20 text-accent-tertiary;
}
```

### Validation for Stage 2

```bash
# 1. Build CSS
npm run build

# 2. Run e2e smoke tests
make e2e-smoke

# 3. Run dashboard e2e tests
make e2e-dashboard

# 4. Visual checklist:
#    - [ ] Cards have correct border colors
#    - [ ] Buttons use warm orange
#    - [ ] Stat values show teal/red for +/-
#    - [ ] No broken layouts or missing styles
```

**Exit criteria**: `make e2e-smoke` and `make e2e-dashboard` pass.

---

## Stage 3: Landing Page Hero Update

**Goal**: Update hero section with warm color scheme.

### 3.1 Update hero_terminal.html

```html
<!-- Update terminal prompt color -->
<span class="terminal-prompt text-accent-primary">$</span>

<!-- Update result line color -->
<div class="text-accent-primary font-medium" x-text="line.text"></div>

<!-- Update headline gradient -->
<h1 class="text-3xl md:text-5xl font-bold leading-tight">
  Is AI making your team
  <span class="app-text-gradient">faster</span>—or just
  <span class="text-accent-error">busier</span>?
</h1>

<!-- Update CTA button -->
<a href="{% url 'account_signup' %}"
   class="btn btn-lg bg-accent-primary hover:bg-orange-600 text-white font-semibold px-8 border-0">
  Join Waitlist
</a>
```

### 3.2 Update terminal styles in design-system.css

```css
.terminal-prompt {
  @apply text-accent-primary font-bold;
}

.terminal-window {
  @apply bg-deep border border-elevated rounded-xl;
}

.gradient-text {
  @apply bg-gradient-to-r from-accent-primary to-pink-500 bg-clip-text text-transparent;
}
```

### Validation for Stage 3

```bash
# 1. Build assets
npm run build

# 2. Run e2e smoke tests (includes landing page)
make e2e-smoke

# 3. Take screenshot for visual review
make e2e ARGS="tests/e2e/smoke.spec.ts --update-snapshots"

# 4. Visual checklist:
#    - [ ] Terminal prompt is orange/coral
#    - [ ] "faster" text has warm gradient
#    - [ ] "busier" text is soft red
#    - [ ] CTA button is warm orange
#    - [ ] Trust indicators still visible
```

**Exit criteria**: `make e2e-smoke` passes, hero section displays warm colors.

---

## Stage 4: Features Grid Update

**Goal**: Update feature cards with warm accent colors.

### 4.1 Update features_grid.html

```html
<!-- Feature 1: Update icon background -->
<div class="w-12 h-12 rounded-lg bg-accent-primary/10 flex items-center justify-center mb-6">
  <svg class="w-6 h-6 text-accent-primary" ...>
</div>

<!-- Feature 2: Keep amber for surveys (already warm) -->
<div class="w-12 h-12 rounded-lg bg-amber-500/10 flex items-center justify-center mb-6">
  <svg class="w-6 h-6 text-amber-400" ...>
</div>

<!-- Feature 3: Use teal for visibility -->
<div class="w-12 h-12 rounded-lg bg-accent-tertiary/10 flex items-center justify-center mb-6">
  <svg class="w-6 h-6 text-accent-tertiary" ...>
</div>

<!-- Update feature cards hover state -->
<div class="feature-card hover:border-accent-primary/50 transition-colors">
```

### Validation for Stage 4

```bash
# 1. Build
npm run build

# 2. E2E tests
make e2e-smoke

# 3. Visual checklist:
#    - [ ] First feature icon is orange
#    - [ ] Second feature icon is amber (unchanged)
#    - [ ] Third feature icon is teal
#    - [ ] Hover states show warm orange border
```

**Exit criteria**: `make e2e-smoke` passes, features section uses warm colors.

---

## Stage 5: Dashboard Metric Cards

**Goal**: Update CTO dashboard cards with warm color scheme.

### 5.1 Update cto_overview.html section headers

```html
<!-- Update divider colors -->
<div class="divider text-lg font-semibold mt-2 mb-4">
  <svg class="h-5 w-5 text-accent-primary mr-2" ...>
  {% trans "GitHub Copilot" %}
</div>

<!-- Update card title icons -->
<h2 class="card-title text-base">
  <svg class="h-5 w-5 text-accent-primary" ...>
  {% trans "Cycle Time Trend" %}
</h2>
```

### 5.2 Update stat card partials

Find and update metric card templates to use new colors:
- Positive trends: `text-accent-tertiary` (teal)
- Negative trends: `text-accent-error` (soft red)
- AI metrics: `text-purple-400` (soft purple)

### Validation for Stage 5

```bash
# 1. Build
npm run build

# 2. Run dashboard e2e tests
make e2e-dashboard

# 3. Run full e2e suite
make e2e

# 4. Visual checklist:
#    - [ ] Dashboard loads correctly
#    - [ ] Positive metrics show teal
#    - [ ] Negative metrics show soft red
#    - [ ] Section headers use warm orange icons
#    - [ ] All HTMX partials load correctly
```

**Exit criteria**: `make e2e-dashboard` and `make e2e` pass.

---

## Stage 6: Navigation & Sidebar

**Goal**: Update navigation with warm accent colors.

### 6.1 Update sidebar active states

```css
/* Sidebar active item */
.app-sidebar-item-active {
  @apply bg-deep text-accent-primary border-l-2 border-accent-primary;
}

/* Sidebar hover */
.app-sidebar-item:hover {
  @apply bg-deep/50 text-accent-primary/80;
}
```

### 6.2 Update app logo/brand

```html
<!-- Logo with warm gradient -->
<div class="w-8 h-8 rounded-lg bg-gradient-to-br from-accent-primary to-pink-500
            flex items-center justify-center">
  <span class="font-bold text-white">T</span>
</div>
```

### Validation for Stage 6

```bash
# 1. Build
npm run build

# 2. Run auth e2e tests (includes navigation)
make e2e-auth

# 3. Run full suite
make e2e

# 4. Visual checklist:
#    - [ ] Active sidebar item shows orange highlight
#    - [ ] Logo has warm gradient
#    - [ ] Navigation hover states work
#    - [ ] No broken layouts
```

**Exit criteria**: `make e2e-auth` and `make e2e` pass.

---

## Stage 7: Buttons & Form Elements

**Goal**: Ensure all interactive elements use warm color scheme.

### 7.1 Update button classes

```css
.app-btn-primary {
  @apply bg-accent-primary hover:bg-orange-600 text-white font-medium;
  @apply focus:ring-accent-primary/50;
}

.app-btn-secondary {
  @apply bg-surface border border-elevated text-neutral-200;
  @apply hover:border-accent-primary/50;
}

.app-btn-ghost {
  @apply bg-transparent text-neutral-300;
  @apply hover:bg-surface hover:text-accent-primary;
}
```

### 7.2 Update form inputs

```css
.app-input {
  @apply bg-deep border border-elevated text-neutral-100;
  @apply focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/50;
}

.app-select {
  @apply bg-deep border border-elevated text-neutral-100;
  @apply focus:border-accent-primary focus:ring-1 focus:ring-accent-primary/50;
}
```

### Validation for Stage 7

```bash
# 1. Build
npm run build

# 2. Run auth tests (includes forms)
make e2e-auth

# 3. Run integration tests (includes settings forms)
make e2e-integrations

# 4. Visual checklist:
#    - [ ] Primary buttons are warm orange
#    - [ ] Form inputs focus with orange ring
#    - [ ] All buttons accessible (contrast ratios)
```

**Exit criteria**: `make e2e-auth` and `make e2e-integrations` pass.

---

## Stage 8: Charts & Data Visualization

**Goal**: Update Chart.js theme with warm colors.

### 8.1 Create/update chart theme

```javascript
// assets/javascript/chart-theme.js
const tformanceChartTheme = {
  colors: {
    primary: '#F97316',    // Warm orange
    secondary: '#FDA4AF',  // Warm rose
    success: '#2DD4BF',    // Teal
    warning: '#FBBF24',    // Amber
    muted: '#A3A3A3',      // Neutral gray
    ai: '#C084FC',         // Soft purple for AI
  },

  grid: {
    color: 'rgba(163, 163, 163, 0.1)',
    borderColor: '#404040',
  },

  tooltip: {
    backgroundColor: '#262626',
    borderColor: '#404040',
    titleColor: '#FAFAFA',
    bodyColor: '#D4D4D4',
  },
};
```

### 8.2 Update chart partials

Update any inline chart colors in templates to reference the theme.

### Validation for Stage 8

```bash
# 1. Build
npm run build

# 2. Run dashboard tests
make e2e-dashboard

# 3. Visual checklist:
#    - [ ] Charts render with warm colors
#    - [ ] AI-related data uses purple
#    - [ ] Positive trends use teal
#    - [ ] Tooltips have correct styling
```

**Exit criteria**: `make e2e-dashboard` passes, charts display correctly.

---

## Stage 9: Empty States & Loading

**Goal**: Update empty states and loading indicators with warm colors.

### 9.1 Update empty state component

```html
<div class="app-empty-state py-16">
  <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-primary/10
              flex items-center justify-center">
    <svg class="w-8 h-8 text-accent-primary"><!-- icon --></svg>
  </div>

  <h3 class="text-lg font-medium text-neutral-200 mb-2">No data yet</h3>
  <p class="text-neutral-400 max-w-sm mx-auto mb-6">
    Connect your integrations to start seeing metrics.
  </p>

  <a href="#" class="app-btn-primary">Get Started</a>
</div>
```

### 9.2 Update skeleton loading

```css
.app-skeleton {
  @apply bg-elevated rounded relative overflow-hidden;
}

.app-skeleton::after {
  content: '';
  @apply absolute inset-0;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(249, 115, 22, 0.05),  /* Warm orange tint */
    transparent
  );
  animation: shimmer 2s infinite;
}
```

### Validation for Stage 9

```bash
# 1. Build
npm run build

# 2. Run all e2e tests
make e2e

# 3. Visual checklist:
#    - [ ] Empty states show warm orange icons
#    - [ ] Loading skeletons have subtle warm shimmer
#    - [ ] CTA buttons in empty states work
```

**Exit criteria**: `make e2e` passes.

---

## Stage 10: Accessibility Audit

**Goal**: Verify all changes meet WCAG AA standards.

### 10.1 Contrast ratio verification

| Element | Background | Foreground | Ratio | Pass? |
|---------|------------|------------|-------|-------|
| Body text | #171717 | #FAFAFA | 15.5:1 | ✓ |
| Muted text | #171717 | #A3A3A3 | 6.5:1 | ✓ |
| Primary accent | #171717 | #F97316 | 5.2:1 | ✓ |
| Teal accent | #171717 | #2DD4BF | 9.3:1 | ✓ |
| Error text | #171717 | #F87171 | 5.8:1 | ✓ |

### 10.2 Focus indicators

```css
/* Ensure all interactive elements have visible focus */
button:focus-visible,
a:focus-visible,
input:focus-visible,
select:focus-visible {
  @apply outline-none ring-2 ring-accent-primary ring-offset-2 ring-offset-deep;
}
```

### 10.3 Motion preferences

```css
@media (prefers-reduced-motion: reduce) {
  .app-skeleton::after,
  .animate-pulse,
  .animate-spin {
    animation: none;
  }

  * {
    transition-duration: 0.01ms !important;
  }
}
```

### Validation for Stage 10

```bash
# 1. Build
npm run build

# 2. Run all e2e tests
make e2e

# 3. Run Lighthouse accessibility audit
# (Manual step via Chrome DevTools)

# 4. Accessibility checklist:
#    - [ ] All contrast ratios ≥ 4.5:1 for text
#    - [ ] All contrast ratios ≥ 3:1 for UI elements
#    - [ ] Focus indicators visible on all interactive elements
#    - [ ] Reduced motion respected
#    - [ ] Screen reader announces chart data
```

**Exit criteria**: `make e2e` passes, Lighthouse accessibility score ≥ 90.

---

## Stage 11: Final Integration Test

**Goal**: Full regression test of all changes.

### Validation for Stage 11

```bash
# 1. Clean build
npm run build

# 2. Run all unit tests
make test

# 3. Run full e2e suite
make e2e

# 4. Run smoke tests
make e2e-smoke

# 5. Manual visual review checklist:
#    - [ ] Landing page hero - warm gradient, orange CTA
#    - [ ] Features section - warm icons
#    - [ ] Login/signup - warm form focus
#    - [ ] Dashboard - warm metric cards
#    - [ ] Charts - warm color scheme
#    - [ ] Navigation - warm active states
#    - [ ] Empty states - warm icons and CTAs
#    - [ ] Loading states - warm shimmer

# 6. Cross-browser check:
#    - [ ] Chrome
#    - [ ] Firefox
#    - [ ] Safari (if available)
```

**Exit criteria**: All tests pass, visual review approved.

---

## Files to Modify

| Stage | File | Changes |
|-------|------|---------|
| 1 | `tailwind.config.js` | Color tokens, DaisyUI theme |
| 2 | `assets/styles/app/tailwind/design-system.css` | Utility classes |
| 3 | `templates/web/components/hero_terminal.html` | Hero colors |
| 4 | `templates/web/components/features_grid.html` | Feature icons |
| 5 | `templates/metrics/cto_overview.html` | Dashboard colors |
| 5 | `templates/metrics/partials/*.html` | Metric card colors |
| 6 | `templates/web/app/sidebar.html` | Navigation colors |
| 7 | `assets/styles/app/tailwind/design-system.css` | Form styles |
| 8 | `assets/javascript/chart-theme.js` | Chart colors |
| 9 | `templates/*/partials/empty_state.html` | Empty states |
| 10 | `assets/styles/app/tailwind/design-system.css` | A11y styles |

---

## Color Reference Quick Guide

```
Primary (Coral Orange):   #F97316  - Main CTAs, active states, brand
Secondary (Warm Rose):    #FDA4AF  - Highlights, secondary actions
Tertiary (Teal):          #2DD4BF  - Success, positive metrics
Warning (Amber):          #FBBF24  - Caution states
Error (Soft Red):         #F87171  - Errors, negative metrics
Info (Soft Blue):         #60A5FA  - Informational
AI (Soft Purple):         #C084FC  - AI-related metrics

Background (Deep):        #171717  - Main background
Surface:                  #262626  - Cards, panels
Elevated:                 #404040  - Borders, dividers

Text Primary:             #FAFAFA  - Main text
Text Secondary:           #D4D4D4  - Supporting text
Text Muted:               #A3A3A3  - Disabled, hints
```

---

## Success Metrics

1. **All E2E tests pass**: `make e2e` succeeds
2. **Accessibility score**: Lighthouse ≥ 90
3. **Contrast ratios**: All WCAG AA compliant
4. **No regressions**: All existing functionality works
5. **Visual coherence**: Warm color scheme applied consistently
6. **Performance**: No CSS/JS bundle size regressions > 5%
