# Homepage Content Refresh - Context

**Last Updated:** 2025-12-20
**Status:** COMPLETE (v2 - ICP-focused redesign)

## Key Files

### Templates Modified
- `templates/web/landing_page.html` - Main landing page structure (6 sections)
- `templates/web/components/hero_terminal.html` - Hero with category label, concrete value prop
- `templates/web/components/how_it_works.html` - 3-step process (Connect, Track, See)
- `templates/web/components/data_transparency.html` - NEW: What we collect/don't collect
- `templates/web/components/security.html` - NEW: 6 security cards
- `templates/web/components/built_with_you.html` - Founder story + community
- `templates/web/components/cta_terminal.html` - Simplified final CTA

### Templates Removed from Landing Page
- `templates/web/components/problem_statement.html` - Stats section (still exists, not used)
- `templates/web/components/features_grid.html` - Old features (still exists, not used)
- `templates/web/components/integrations.html` - Logos section (still exists, not used)
- `templates/web/components/pricing_simple.html` - Pricing card (still exists, not used)

## Key Decisions

### Content Strategy (ICP-First)
**Decision**: Restructure page to answer CTO questions in order
**Rationale**: Previous version was too abstract. CTOs need to know WHAT/HOW/WHY quickly.

| Question | Section | Answer |
|----------|---------|--------|
| What is this? | Hero | "AI Coding Tool Analytics" |
| How does it work? | How It Works | Connect → We Track → You See |
| What data do you collect? | Data Transparency | PR metadata, surveys (NO code) |
| Why should I trust you? | Security | Render, Django, code reviews, BYOD |
| Who's building this? | Founder | Oleksii Ianchuk, ex-Mailtrap |
| How do I start? | CTA | "Start Free" |

### Headline Change
**Decision**: "See if Copilot is actually helping your team ship"
**Rationale**: Direct, concrete, mentions Copilot (recognizable)

### CTA Strategy
**Decision**: "Start Free" everywhere, "See How It Works" as secondary
**Rationale**: Consistent, action-oriented, no "waitlist" language

### Security Messaging
**Decision**: Include specific details (Render, Django, Ruff, senior dev reviews, BYOD coming)
**Rationale**: CTOs want technical specifics, not vague claims

### Founder Info
- Name: Oleksii Ianchuk
- Role: Technical Product Manager
- Background: 8 years dev tools, Technical Product Lead at Mailtrap
- Links: GitHub (github.com/yanchuk), LinkedIn (linkedin.com/in/yanch), Discord
- Email: NOT published (will add later)

## Content Guidelines

1. **Concrete > Abstract** - Say exactly what happens
2. **Short sentences** - Scannable for busy CTOs
3. **Technical credibility** - Specific tools/frameworks named
4. **Transparency** - Show what we collect AND don't collect
5. **Human element** - Founder story builds trust

## ICP (Ideal Customer Profile)

**Primary**: CTO / VP Engineering
- Tired of guessing if AI tools help
- Needs data for executive decisions
- Values transparency over hype
- Has limited time to evaluate tools
- Skeptical of "revolutionary" claims

## Page Structure (Final)

```
1. Hero (category label + value prop + CTAs)
2. How It Works (3 steps with details)
3. Data Transparency (what we see/don't see)
4. Security (6 cards)
5. Who's Building This (founder + values)
6. Final CTA
```

## Screenshots

- `.playwright-mcp/homepage-v2-final.png` - Full page screenshot

## Dependencies

None. Pure frontend/content changes. No migrations needed.

## Testing

- Smoke tests: 6/6 passing
- No Django changes, no migrations needed
- CSS uses existing design system tokens
