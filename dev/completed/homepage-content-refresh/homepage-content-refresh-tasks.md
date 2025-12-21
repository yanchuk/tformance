# Homepage Content Refresh - Tasks

**Last Updated:** 2025-12-20
**Status:** COMPLETE (v2 - ICP-focused redesign)

## Summary

Completely restructured homepage to answer ICP (CTO) questions clearly:
- WHAT is this? → "AI Coding Tool Analytics"
- HOW does it work? → 3-step process (Connect, Track, See)
- WHAT data do you collect? → Transparency section
- WHY should I trust you? → Security + Founder story
- HOW do I start? → Clear CTAs

---

## Completed Tasks

### Phase 1: Hero Section ✅
- [x] Added category label: "AI Coding Tool Analytics"
- [x] New headline: "See if Copilot is actually helping your team ship"
- [x] Concrete subheadline explaining the flow
- [x] CTAs: "Start Free" + "See How It Works"
- [x] Trust indicators: Free while in beta, No credit card, 5 min setup
- [x] Removed logo placeholders (from v1)

### Phase 2: How It Works Section ✅
- [x] 3-step process with colored numbered circles
- [x] Step 1: Connect (GitHub, Jira, Slack via OAuth)
- [x] Step 2: We Track (PR metrics, Jira links, Slack surveys)
- [x] Step 3: You See (Dashboard, trends, weekly digest)
- [x] Specific details under each step

### Phase 3: Data Transparency Section ✅
- [x] Created new `data_transparency.html` component
- [x] What We Collect (PR metadata, review counts, Jira status, surveys)
- [x] What We Don't Touch (NO code, NO diffs, NO Slack DMs, NO individual tracking)
- [x] Two-column layout with + and - indicators

### Phase 4: Security Section ✅
- [x] Created new `security.html` component
- [x] Render Hosting (SOC 2)
- [x] Django Framework (trusted by Instagram/Pinterest/Dropbox)
- [x] Encrypted data (team-isolated)
- [x] Code Quality (Ruff, security scans)
- [x] Code Reviews (Senior Django devs, public summaries)
- [x] BYOD Coming (bring your own PostgreSQL) - "Coming Soon" badge

### Phase 5: Founder Section ✅
- [x] Rewrote `built_with_you.html` as "Who's Building This"
- [x] Personal story: Oleksii Ianchuk, Technical Product Manager
- [x] Background: 8 years dev tools, ex-Mailtrap (Email API/SMTP)
- [x] Social links: GitHub, LinkedIn, Discord
- [x] Values: Bootstrapped, Free Until It Works, Feedback = Roadmap
- [x] Looking for: CTOs, engineering leads, co-founders
- [x] CTA: "Join Discord to connect" (removed email per user request)

### Phase 6: Final CTA ✅
- [x] "Try It Free" headline
- [x] Concrete next step: "See your first dashboard in 10 minutes"
- [x] Trust reassurance: "No credit card. Free while in beta."

### Phase 7: Page Structure ✅
- [x] Updated `landing_page.html` with new section order
- [x] Removed: problem_statement, features_grid, integrations, pricing_simple
- [x] Final order: Hero → How It Works → Data Transparency → Security → Founder → CTA

---

## Files Modified

| File | Status | Change |
|------|--------|--------|
| `hero_terminal.html` | Modified | Category label, new headline, concrete subheadline |
| `how_it_works.html` | Rewritten | 3-step process with details |
| `data_transparency.html` | NEW | What we collect/don't collect |
| `security.html` | NEW | 6 security cards |
| `built_with_you.html` | Rewritten | Founder story + values |
| `cta_terminal.html` | Modified | Simplified with concrete next step |
| `landing_page.html` | Modified | New section order (6 sections) |

---

## Testing Status

- [x] Smoke tests: 6/6 passing
- [x] Visual review: Screenshot saved to `.playwright-mcp/homepage-v2-final.png`
- [ ] Mobile responsive testing (not done this session)
- [ ] Cross-browser testing (not done this session)

---

## Future Tasks (Not Started)

- [ ] Add real company logos when available
- [ ] Add contact email/form when ready
- [ ] Add X (Twitter) link for founder if available
- [ ] Consider adding testimonials section when available
- [ ] A/B test headline variations
- [ ] Mobile-specific optimizations if needed

---

## No Django Changes

This task was pure frontend/content. No migrations needed.
