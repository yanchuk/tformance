# Home Page Redesign - Context & References

**Last Updated:** 2025-12-10

---

## Target Audience

### Primary: CTOs of 10-50 Developer Teams
- **Pain Point:** "Is AI actually helping my team deliver better, or are we just generating more code that creates more review burden?"
- **Decision Maker:** Controls tool budgets, cares about ROI
- **Technical Level:** Can read code, understands engineering metrics
- **Aesthetic Preferences:** Clean, data-driven, no marketing fluff

### Secondary: Engineering Managers / Team Leads
- **Pain Point:** Need visibility into team performance for 1:1s
- **Technical Level:** Very high, daily GitHub/Jira users
- **Aesthetic Preferences:** Terminal/IDE familiarity, dark mode

---

## Key Product Differentiators (From PRD)

1. **AI Correlation Analysis** - Connect AI tool usage with delivery outcomes (competitors don't do this)
2. **Gamified PR Surveys** - "AI Detective" game to capture quality feedback (unique approach)
3. **BYOS (Bring Your Own Storage)** - Client data stays in their Supabase (security differentiator)
4. **Affordable Pricing** - $10-25/seat vs $40-60 competitors

---

## Integrations to Showcase

| Service | Logo Needed | What We Pull |
|---------|-------------|--------------|
| GitHub | Yes | PRs, commits, reviews, org members |
| Jira | Yes | Issues, story points, sprints |
| Slack | Yes | Bot for surveys + leaderboard |
| GitHub Copilot | Via GitHub | Usage metrics |

---

## Key Files Reference

### Templates
```
templates/web/
├── base.html              # Base template (font imports go here)
├── landing_page.html      # Main landing page structure
└── components/
    ├── top_nav.html       # Navigation (keep existing)
    ├── footer.html        # Footer (keep existing)
    ├── hero.html          # Current hero (to replace)
    ├── feature_highlight.html  # Current features (to replace)
    ├── landing_section1.html   # Placeholder (to remove)
    ├── landing_section2.html   # Placeholder (to remove)
    ├── testimonials.html       # Fake testimonials (to remove)
    └── cta.html                # Current CTA (to replace)
```

### Styles
```
assets/styles/
├── site-tailwind.css      # Main Tailwind entry (DaisyUI, Flowbite)
└── app/
    └── tailwind/
        ├── app-components.css
        └── subscription-components.css
```

### Config
```
tailwind.config.js         # Custom theme extensions
```

---

## Design System Reference

### Current Stack
- **CSS Framework:** Tailwind CSS v4
- **Component Library:** DaisyUI
- **Icons:** Font Awesome 6, Heroicons (inline SVGs)
- **JS Interactivity:** Alpine.js, HTMX

### Existing Color Classes (DaisyUI)
- `bg-base-100`, `bg-base-200`, `bg-base-300`
- `text-primary`, `text-secondary`, `text-accent`
- `btn-primary`, `btn-outline`, `btn-ghost`

### New Custom Classes to Add
- `.font-mono` - JetBrains Mono
- `.font-sans` - DM Sans
- `.bg-deep`, `.bg-surface`, `.bg-elevated`
- `.text-cyan`, `.text-green-accent`
- `.animate-typewriter`, `.animate-fade-up`

---

## Content Sources

### Metrics to Feature (From PRD)
| Category | Metric | Visualization Idea |
|----------|--------|-------------------|
| Delivery | PR Throughput | Line chart |
| Delivery | Cycle Time | Bar comparison |
| AI Usage | AI-assisted PRs | Pie chart |
| Quality | PR Quality Rating | Star system |

### Copy Inspiration
- **Vercel:** Clean, developer-focused, dark aesthetic
- **Linear:** Terminal vibes, keyboard shortcuts displayed
- **Raycast:** Data-forward, productivity metrics
- **Posthog:** Open about data ownership

---

## Technical Decisions

### Font Strategy
```html
<!-- In base.html <head> -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
```

### Tailwind Config Updates
```js
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      colors: {
        deep: '#0f172a',
        surface: '#1e293b',
        elevated: '#334155',
        cyan: {
          DEFAULT: '#06b6d4',
          light: '#22d3ee',
        },
      },
      animation: {
        'typewriter': 'typewriter 2s steps(40) forwards',
        'fade-up': 'fade-up 0.5s ease-out forwards',
      },
    },
  },
}
```

### Alpine.js Patterns

**Typewriter Effect:**
```html
<span x-data="{ text: '', fullText: 'Is AI making your team faster?' }"
      x-init="let i = 0; setInterval(() => { if (i <= fullText.length) { text = fullText.slice(0, i++); } }, 50)"
      x-text="text">
</span>
```

**Scroll-Triggered Fade:**
```html
<div x-data="{ visible: false }"
     x-intersect="visible = true"
     :class="visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'"
     class="transition-all duration-500">
  Content
</div>
```

---

## Visual Mockup References

### Hero Section Layout
```
┌──────────────────────────────────────────────────────────────┐
│  ┌─ terminal ─────────────────────────────────────────────┐  │
│  │ $ tformance analyze --team=engineering                  │  │
│  │                                                          │  │
│  │ Is AI making your team faster—or just busier?           │  │
│  │                                                          │  │
│  │ > Analyzing 1,247 PRs from last quarter...              │  │
│  │ > AI-assisted: 43% | Avg cycle time: -2.3 days          │  │
│  │                                                          │  │
│  │ [Start Free Trial]  [See Demo]                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Feature Cards Layout
```
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ AI Correlation  │  │ PR Surveys      │  │ BYOS            │
│ ═══════════════ │  │ ═══════════════ │  │ ═══════════════ │
│                 │  │                 │  │                 │
│ [chart mockup]  │  │ [slack mockup]  │  │ [db icon]       │
│                 │  │                 │  │                 │
│ See if AI PRs   │  │ Gamified        │  │ Your data,      │
│ ship faster...  │  │ feedback via... │  │ your Supabase   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

## Related PRD Sections

- `prd/PRD-MVP.md` - Full product spec
- `prd/DASHBOARDS.md` - Dashboard mockups for preview section
- `prd/ONBOARDING.md` - User flow (for understanding conversion path)
- `prd/ARCHITECTURE.md` - BYOS explanation for copy
