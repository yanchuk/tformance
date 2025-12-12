# Home Page Redesign - Task Checklist

**Last Updated:** 2025-12-10

---

## Phase 1: Foundation & Typography [S]

### 1.1 Font Setup
- [ ] Add Google Fonts import to `templates/web/base.html`
  - JetBrains Mono (400, 500, 700)
  - DM Sans (400, 500, 700)
- [ ] Update `tailwind.config.js` with custom font families
- [ ] Create `assets/styles/app/tailwind/landing-page.css` with custom variables

**Acceptance Criteria:**
- Fonts load correctly on page
- `font-mono` and `font-sans` classes work
- No FOUT (flash of unstyled text)

### 1.2 Color System Extension
- [ ] Add custom colors to Tailwind config (deep, surface, elevated, cyan)
- [ ] Add animation keyframes to config
- [ ] Test dark mode compatibility with new colors

**Acceptance Criteria:**
- New color classes available (`bg-deep`, `text-cyan`, etc.)
- Animation classes work (`animate-typewriter`, `animate-fade-up`)
- DaisyUI themes not broken

---

## Phase 2: Hero Section [M]

### 2.1 Create Terminal-Style Hero
- [ ] Create `templates/web/components/hero_terminal.html`
- [ ] Implement terminal window design with title bar
- [ ] Add typewriter animation for main headline using Alpine.js
- [ ] Add "fake" terminal output lines with stats
- [ ] Style CTA buttons (primary + outline)

**Content:**
```
Headline: "Is AI making your team faster—or just busier?"
Subtext: Terminal-style analysis output
CTAs: "Start Free Trial" | "See Demo Dashboard"
```

**Acceptance Criteria:**
- Terminal aesthetic matches design vision
- Typewriter animation works smoothly
- Mobile responsive (stacks properly)
- CTAs link to signup/demo pages

### 2.2 Replace Hero Include
- [ ] Update `landing_page.html` to use new hero component
- [ ] Remove reference to old `hero.html`

---

## Phase 3: Problem Statement Section [M]

### 3.1 Create Problem Visualization
- [ ] Create `templates/web/components/problem_statement.html`
- [ ] Design "AI Productivity Paradox" section
- [ ] Add two stat cards side by side:
  - "+21% code output"
  - "+91% review time"
- [ ] Add explanatory copy about the problem

**Content:**
```
Section title: "The AI Productivity Paradox"
Stat 1: "21%" / "increase in code output with AI tools"
Stat 2: "91%" / "increase in code review time"
Copy: "AI coding assistants boost individual output, but PRs pile up faster than teams can review. CTOs have no visibility into whether AI adoption correlates with better outcomes."
```

**Acceptance Criteria:**
- Stats are visually prominent
- Section clearly communicates the problem
- Visual hierarchy guides the eye

---

## Phase 4: Integrations Section [S]

### 4.1 Create Integration Showcase
- [ ] Create `templates/web/components/integrations.html`
- [ ] Add SVG logos for GitHub, Jira, Slack (use official brand colors)
- [ ] Design connection line visual (or animated dots)
- [ ] Add brief description of what each integration provides

**Content:**
```
Section title: "Connect Your Stack"
GitHub: PRs, commits, reviews, team members
Jira: Issues, story points, sprint velocity
Slack: Surveys, leaderboards, notifications
```

**Acceptance Criteria:**
- Logos are crisp and recognizable
- Visual conveys "these tools connect to us"
- Hover states on logos

---

## Phase 5: Features & Value Props [L]

### 5.1 Create Feature Grid Component
- [ ] Create `templates/web/components/features_grid.html`
- [ ] Design three feature cards with icons
- [ ] Add mini data visualizations or mockups to each card

**Feature 1: AI Correlation Dashboard**
```
Icon: Chart/graph
Title: "AI Correlation Dashboard"
Description: "See if AI-assisted PRs ship faster—or just get bigger. Correlate AI usage with cycle time, review load, and quality ratings."
Visual: Mini line chart mockup
```

**Feature 2: Gamified PR Surveys**
```
Icon: Sparkles/game
Title: "Gamified PR Surveys"
Description: "One-click Slack surveys after every merge. Guess if PRs were AI-assisted. Weekly leaderboards keep engagement high."
Visual: Slack message mockup
```

**Feature 3: BYOS Security**
```
Icon: Shield/database
Title: "Your Data, Your Database"
Description: "All metrics stay in your Supabase instance. We only store encrypted API tokens. Export or delete anytime."
Visual: Database icon with lock
```

**Acceptance Criteria:**
- Each feature clearly communicates value
- Visuals reinforce the message
- Responsive grid (3 cols desktop, 1 col mobile)

### 5.2 Create How It Works Section
- [ ] Create `templates/web/components/how_it_works.html`
- [ ] Design simple 3-step numbered flow
- [ ] Add connecting line/arrow between steps

**Content:**
```
Step 1: "Connect" - Link GitHub, Jira, and Slack in minutes
Step 2: "Analyze" - We sync data and correlate AI usage with delivery
Step 3: "Improve" - See what's working and optimize your workflow
```

**Acceptance Criteria:**
- Steps are numbered and clear
- Visual flow is obvious
- Not cluttered

---

## Phase 6: Social Proof & CTA [M]

### 6.1 Create Data Preview Section
- [ ] Create `templates/web/components/data_preview.html`
- [ ] Add dashboard screenshot or stylized mockup
- [ ] Frame in browser/app window chrome
- [ ] Add caption about what users will see

**Acceptance Criteria:**
- Preview gives sense of actual product
- Professional presentation
- Mobile: Image scales appropriately

### 6.2 Create Simple Pricing Section
- [ ] Create `templates/web/components/pricing_simple.html`
- [ ] Show per-seat pricing model
- [ ] Highlight free trial
- [ ] Compare to competitors implicitly ("A fraction of enterprise tool costs")

**Content:**
```
Title: "Simple Per-Seat Pricing"
Trial: "Free 14-day trial, up to 5 seats"
Pricing: "$XX/seat/month" (or "Pricing coming soon")
Note: "No credit card required to start"
```

**Acceptance Criteria:**
- Pricing is clear and transparent
- Free trial is prominent
- CTA to sign up

### 6.3 Create Terminal-Style CTA Section
- [ ] Create `templates/web/components/cta_terminal.html`
- [ ] Match hero terminal aesthetic
- [ ] Simple command prompt with signup CTA

**Content:**
```
$ ready to see if ai is actually helping?
> [Start Your Free Trial]
```

**Acceptance Criteria:**
- Matches hero aesthetic
- Strong, clear CTA
- Appropriate contrast for accessibility

---

## Phase 7: Integration & Polish [M]

### 7.1 Update Landing Page Template
- [ ] Update `templates/web/landing_page.html` with new includes:
  ```django
  {% include "web/components/hero_terminal.html" %}
  {% include "web/components/problem_statement.html" %}
  {% include "web/components/integrations.html" %}
  {% include "web/components/features_grid.html" %}
  {% include "web/components/how_it_works.html" %}
  {% include "web/components/data_preview.html" %}
  {% include "web/components/pricing_simple.html" %}
  {% include "web/components/cta_terminal.html" %}
  ```

### 7.2 Remove Old Components
- [ ] Archive or delete `landing_section1.html`
- [ ] Archive or delete `landing_section2.html`
- [ ] Archive or delete `testimonials.html`
- [ ] Archive or delete `feature_highlight.html`

### 7.3 Add Scroll Animations
- [ ] Add `x-intersect` scroll triggers to sections
- [ ] Implement staggered fade-in for feature cards
- [ ] Add `prefers-reduced-motion` media query fallback

### 7.4 Testing & QA
- [ ] Test on desktop (Chrome, Firefox, Safari)
- [ ] Test on mobile (iOS Safari, Android Chrome)
- [ ] Run Lighthouse audit (target: 80+ performance, 90+ accessibility)
- [ ] Verify dark mode toggle works correctly
- [ ] Check all links work (signup, login, demo)

**Acceptance Criteria:**
- All sections render correctly
- No console errors
- Performance budget met
- Accessible (keyboard nav, screen reader)

---

## Optional Enhancements (Post-MVP)

- [ ] Add particle/noise background effect
- [ ] Implement smooth scroll to sections
- [ ] Add animated SVG illustrations
- [ ] Create video demo embed
- [ ] Add customer logos section (when available)
- [ ] Implement A/B test variants

---

## Effort Legend
- **[S]** Small - ~1-2 hours
- **[M]** Medium - ~2-4 hours
- **[L]** Large - ~4-8 hours
- **[XL]** Extra Large - 8+ hours

---

## Notes

- **Dependencies:** Font loading must complete before hero animation starts
- **Copy Review:** Get stakeholder sign-off on all messaging before implementation
- **Screenshots:** Will need actual dashboard mockups for data preview section
