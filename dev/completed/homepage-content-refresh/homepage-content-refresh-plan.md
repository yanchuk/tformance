# Homepage Content Refresh - Implementation Plan

**Last Updated:** 2025-12-20

## Executive Summary

Refresh tformance homepage to better communicate value to CTOs. Based on competitor analysis (Linear, Railway, Notion, Axiom, Raycast). Changes include content, structure, and simple visual improvements. **No new tech** - using existing Django templates, Tailwind, DaisyUI, Alpine.js.

## Current State Analysis

### What's Working
- Hero headline is provocative ("Is AI making your team faster—or just busier?")
- Terminal animation differentiates
- Problem stats are compelling
- Dark design is polished

### What Needs Improvement

| Issue | Current | Impact |
|-------|---------|--------|
| Weak CTA | "Join Waitlist" | Sounds like vaporware |
| Too wordy | Long paragraphs | Devs don't read |
| No human element | Generic copy | No connection |
| Missing "why us" | Just features | No differentiation |
| No social proof | Nothing | Low trust |
| Long page | 7 sections | Too much scrolling |

### Competitor Patterns
- **Linear**: Direct "what it IS" + product screenshot
- **Railway**: Emotional benefit + visual demo
- **Notion**: Pain point headline + social proof logos
- **Raycast**: 4-word headline + immediate download
- **Axiom**: Category claim + customer logos

## Proposed Changes

### Content Changes (Copy)

| Section | Current | New |
|---------|---------|-----|
| Hero CTA | "Join Waitlist" | "Start Free" |
| Hero subheadline | 30 words | 15 words |
| Trust indicator | "Free during beta" | "Free until it works for you" |
| Pricing header | "Free During Beta" | "Free Until It Works" |

### Structural Changes

| Change | Rationale |
|--------|-----------|
| Add "Built With You" section | Human element, differentiation |
| Merge/simplify sections | Reduce scroll, faster to value |
| Add social proof placeholder | Build trust (even if empty initially) |
| Move pricing into hero trust area | One less section to scroll |

### Visual Improvements (Simple)

| Change | How | Stack |
|--------|-----|-------|
| Larger hero stats preview | Bigger terminal output | CSS only |
| Customer logos placeholder | "Teams using tformance" | Static HTML |
| Simpler features layout | 2 columns not 3 | Tailwind grid |
| Remove "How It Works" | Redundant with features | Delete include |

## Implementation Phases

### Phase 1: Hero Section Overhaul
**Effort: M** | **Files: hero_terminal.html**

Changes:
- Shorter subheadline
- "Start Free" CTA (primary) + "Book a Call" (secondary)
- Trust indicators: "Free until it works" / "No credit card" / "10 min setup"
- Add small "Used by teams at [logo placeholders]" below trust

### Phase 2: New "Built With You" Section
**Effort: M** | **Files: built_with_you.html (new), landing_page.html**

New section after hero (replace problem statement position):
```
## Built With You, Not For You

We're a small team who got tired of guessing if AI tools help.

→ Bootstrapped. No VC pressure.
→ Free until it actually works for you.
→ Your feedback = our roadmap.

[Talk to Us] [Start Free]
```

### Phase 3: Simplify Problem + Stats
**Effort: S** | **Files: problem_statement.html**

- Cut text by 60%
- Make stats BIGGER and more visual
- Remove code comment styling (too clever)
- Single question: "Is AI actually helping your team deliver?"

### Phase 4: Features Consolidation
**Effort: M** | **Files: features_grid.html**

- Reduce from 3 cards to 2 main value props:
  1. "See if AI helps" (correlation dashboard)
  2. "Get the data you're missing" (surveys + visibility)
- Remove mini-visualizations (add clutter)
- Simpler, text-focused cards

### Phase 5: Remove/Merge Sections
**Effort: S** | **Files: landing_page.html**

Remove or merge:
- ❌ **How It Works** - redundant, everyone knows OAuth
- ❌ **Integrations** logos in own section - move to hero or footer
- ✅ **Pricing** - simplify, merge key message into hero trust area
- ✅ **CTA** - keep but shorter

### Phase 6: Final CTA Simplification
**Effort: S** | **Files: cta_terminal.html**

Shorter:
```
## Ready to find out?

Start free. No credit card. Cancel anytime.

[Start Free]
```

## Proposed Page Structure (After)

```
1. Hero (with terminal, CTA, trust indicators, logo placeholders)
2. Built With You (human element, bootstrapped message)
3. Problem Stats (visual, punchy)
4. Features (2 value props, simple)
5. Final CTA (short)
Footer
```

**Removed:**
- How It Works section
- Standalone Integrations section
- Standalone Pricing card section

## Tech Constraints

| Allowed | Not Allowed |
|---------|-------------|
| Django templates | New JS frameworks |
| Tailwind CSS | External CSS libraries |
| DaisyUI components | New component libraries |
| Alpine.js (existing) | React/Vue additions |
| Static HTML/CSS | Complex animations |
| Heroicons/FontAwesome | New icon libraries |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Removing too much | Keep original files, easy rollback |
| Breaking mobile | Test each phase on mobile |
| Logo placeholders look empty | Use "Teams like yours" or hide until real |

## Success Metrics

1. Page sections: 7 → 5
2. Total word count: -40%
3. Time to CTA: <2 scroll actions
4. Mobile: All content above fold in 2 scrolls
