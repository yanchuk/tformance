# Home Page Redesign - Development Plan

**Last Updated:** 2025-12-10

---

## Executive Summary

Redesign the landing page for tformance (AI Impact Analytics Platform) with a **developer-centric, data-forward aesthetic** that speaks directly to CTOs and engineering leaders. The current page uses generic placeholder content and lacks the technical credibility needed to convert our target audience.

### Design Vision: "Terminal Meets Dashboard"

**Aesthetic Direction:** A refined, **monospace-meets-modern** design that evokes:
- Terminal interfaces and code editors (familiar to developers)
- Real-time data dashboards (conveys analytics power)
- Dark-mode-first approach (developer preference)
- Precise typography with generous whitespace (editorial quality)

**Key Visual Elements:**
- **Typography:** JetBrains Mono for code/data, DM Sans for body text
- **Color Palette:** Deep slate backgrounds, electric cyan accents, subtle gradients
- **Motion:** Subtle data visualization animations, typewriter effects
- **Composition:** Asymmetric grids, floating data cards, terminal-style sections

---

## Current State Analysis

### Existing Structure (`templates/web/landing_page.html`)
```
landing_page.html
├── hero.html           - Generic headline + rocket SVG
├── feature_highlight.html - 3 placeholder features
├── landing_section1.html  - Lorem ipsum + generic icons
├── testimonials.html      - Fake testimonials
├── landing_section2.html  - More lorem ipsum
└── cta.html              - Basic signup CTA
```

### Problems Identified:
1. **Generic placeholder content** - Lorem ipsum everywhere
2. **No product-specific messaging** - Doesn't communicate value prop
3. **Boring visual design** - Standard SaaS template aesthetic
4. **Missing credibility signals** - No integration logos, metrics, or proof
5. **Not developer-focused** - Generic marketing speak vs technical clarity

---

## Proposed Future State

### New Component Structure
```
landing_page.html (redesigned)
├── hero_terminal.html     - Terminal-style hero with typewriter effect
├── problem_statement.html - "The AI Productivity Paradox" data visualization
├── integrations.html      - GitHub/Jira/Slack logos with connection lines
├── features_grid.html     - 3 core features with data mockups
├── how_it_works.html      - Simple 3-step flow diagram
├── data_preview.html      - Dashboard preview/mockup screenshot
├── pricing_simple.html    - Per-seat pricing with trial CTA
└── cta_terminal.html      - Terminal-style final CTA
```

---

## Implementation Phases

### Phase 1: Foundation & Typography (S)
Update base styles and fonts for the new aesthetic.

### Phase 2: Hero Section (M)
Replace generic hero with terminal-style, developer-focused hero.

### Phase 3: Problem Statement (M)
Visualize "The AI Productivity Paradox" with compelling data.

### Phase 4: Integration Showcase (S)
Display GitHub, Jira, Slack, Copilot integrations prominently.

### Phase 5: Features & Value Props (L)
Rewrite feature sections with actual product benefits.

### Phase 6: Social Proof & Credibility (M)
Replace fake testimonials with credibility signals.

### Phase 7: Final Polish & Animations (M)
Add subtle animations and micro-interactions.

---

## Technical Approach

### Fonts (Google Fonts)
```css
/* Import via link tag or @import */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap');
```

### Color Variables (CSS Custom Properties)
```css
:root {
  /* Dark theme (primary) */
  --bg-deep: #0f172a;      /* Slate 900 */
  --bg-surface: #1e293b;   /* Slate 800 */
  --bg-elevated: #334155;  /* Slate 700 */

  --text-primary: #f1f5f9; /* Slate 100 */
  --text-secondary: #94a3b8; /* Slate 400 */
  --text-muted: #64748b;   /* Slate 500 */

  --accent-cyan: #06b6d4;  /* Cyan 500 */
  --accent-green: #22c55e; /* Green 500 */
  --accent-purple: #a855f7; /* Purple 500 */

  /* For data viz */
  --chart-positive: #4ade80;
  --chart-negative: #f87171;
  --chart-neutral: #60a5fa;
}
```

### Animation Utilities (CSS)
```css
/* Typewriter effect for terminal text */
@keyframes typewriter {
  from { width: 0; }
  to { width: 100%; }
}

/* Subtle pulse for live data indicators */
@keyframes pulse-subtle {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Staggered fade-in for cards */
@keyframes fade-slide-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
```

### Alpine.js Interactions
- Typewriter text animation on hero
- Scroll-triggered animations using `x-intersect`
- Tab switching for feature previews
- Hover states on integration cards

---

## Content Strategy

### Hero Copy
**Headline:** "Is AI making your team faster—or just busier?"

**Subheadline:** "Connect GitHub, Jira, and Slack to see if AI coding tools are actually improving delivery, or just creating more code to review."

**CTA:** "Start Free Trial" / "See Demo Dashboard"

### Key Messages (Developer-Focused)
1. **Honest Metrics:** "We don't just count commits. We correlate AI usage with actual delivery outcomes."
2. **Privacy-First:** "Your data stays in your Supabase. We only store encrypted API tokens."
3. **Built for Teams:** "From 10 to 50 devs. Per-seat pricing that won't break the budget."

### Feature Descriptions
1. **AI Correlation Dashboard**
   - "See if AI-assisted PRs ship faster—or just get bigger."

2. **PR Quality Surveys**
   - "Quick Slack surveys. Gamified feedback. No spreadsheets."

3. **BYOS (Bring Your Own Storage)**
   - "All data in your Supabase instance. Export or delete anytime."

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Font loading affects performance | Use `font-display: swap`, preload critical fonts |
| Dark theme accessibility issues | Ensure WCAG AA contrast ratios |
| Animation jank on mobile | Use `prefers-reduced-motion` media query |
| Content changes require copy review | Get stakeholder sign-off on messaging |

---

## Success Metrics

- **Bounce rate reduction:** < 50% (from current baseline)
- **Time on page increase:** > 30 seconds average
- **Signup button click rate:** > 3%
- **Mobile usability score:** > 90 (Lighthouse)
- **Performance score:** > 80 (Lighthouse)

---

## Dependencies

- Google Fonts CDN or self-hosted font files
- No new npm packages required (using existing Tailwind/DaisyUI)
- Product screenshots/mockups for dashboard preview section
- Stakeholder approval on copy changes

---

## Files to Create/Modify

### New Files
- `templates/web/components/hero_terminal.html`
- `templates/web/components/problem_statement.html`
- `templates/web/components/integrations.html`
- `templates/web/components/features_grid.html`
- `templates/web/components/how_it_works.html`
- `templates/web/components/data_preview.html`
- `templates/web/components/pricing_simple.html`
- `templates/web/components/cta_terminal.html`
- `assets/styles/app/tailwind/landing-page.css`

### Modified Files
- `templates/web/landing_page.html` - Update includes
- `templates/web/base.html` - Add font imports
- `tailwind.config.js` - Add custom fonts and colors

### Removed/Archived
- `templates/web/components/landing_section1.html`
- `templates/web/components/landing_section2.html`
- `templates/web/components/testimonials.html`
- `templates/web/components/feature_highlight.html`
