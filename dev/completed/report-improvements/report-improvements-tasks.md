# Report Improvements - Tasks

**Last Updated: 2025-12-27**
**Status: COMPLETE** ✅

## Phase 1: HIGH Risk Items (Must Fix) ✅

### 1.1 Add Copilot/ChatGPT Disclosure ✅
- [x] Add callout box in "AI Tool Evolution" section explaining why Copilot/ChatGPT are absent
- [x] Text: "Our tool rankings reflect *disclosed* usage patterns in OSS PRs, not total market share. Tools that leave visible artifacts (CodeRabbit, Devin) appear dominant because we can detect them. Silent tools (Copilot autocomplete, ChatGPT for research) are likely underrepresented by 5-10x."

### 1.2 Improve Adoption Gap Explanation ✅
- [x] Add visual comparison table in "Industry Context" section
- [x] Show: What each metric measures, why they're not comparable
- [x] Include "hidden adoption" iceberg analogy
- [x] Emphasize our 21.4% is the **floor**, real rate likely 40-60%

### 1.3 Data Consistency Fixes ✅
- [x] Fix "28 teams" → "26 teams" in About section and trend section
- [x] Fix "~54,000 PRs" → align with "60,545 PRs"
- [x] Standardize "21.4%" across all sections

## Phase 2: MEDIUM Risk Items (Should Fix) ✅

### 2.1 Add Cycle Time Causal Disclaimer ✅
- [x] Add warning box after "+42% cycle time" finding
- [x] Text: "The +42% cycle time finding shows correlation, not causation. We cannot determine if AI slows delivery or if teams choose AI for inherently complex work."

### 2.2-2.3 Deferred
- [ ] Include Trust Metrics (deferred - covered in legal disclaimers)
- [ ] Clarify Agent Adoption Denominator (deferred - low impact)

## Phase 3: LOW Risk Items - Deferred

### Deferred for future iteration
- [ ] Qualify Sweet Spot Claim
- [ ] Expand Selection Bias Discussion
- [ ] Add False Negative Caveat

Note: These are now partially addressed in the comprehensive legal disclaimers section.

## Phase 4: Copy Improvements - Partially Done

### Completed
- [x] Iceberg analogy included in adoption gap section

### Deferred
- [ ] Headline scannable format
- [ ] Jargon reduction
- [ ] +42% label reframe

## Additional Completed Items ✅

### CTAs Added
- [x] Sidebar CTA at bottom of table of contents
- [x] Inline CTA after Key Takeaways section
- [x] Mid-content CTA after Detection Methods section

### Interactive Features
- [x] Team selection filter for Monthly Adoption Trends chart
- [x] Checkboxes for 5 teams (Antiwork, Cal.com, Plane, Formbricks, PostHog)
- [x] Select All / Clear All buttons

### Legal/Footer
- [x] "Open to Share" citation note in footer
- [x] Trademark disclaimer
- [x] Comprehensive legal disclaimers (7 sections)

### Tech Stack
- [x] Add Tailwind CSS CDN
- [x] Add Alpine.js CDN
- [x] Custom Tailwind config with project colors

### Other
- [x] Update LLM model name: "Groq Batch API" → "ChatGPT OSS 20B model" (3 locations)

## Verification

```bash
# View report locally
open docs/index.html

# Verify:
# 1. Theme toggle works (dark/light)
# 2. Team filter checkboxes work
# 3. Legal disclaimers visible at bottom
# 4. CTAs visible in sidebar and body
# 5. Data shows "26 teams" and "21.4%" consistently
# 6. Cycle time disclaimer visible
```

## Commit Reference

```
29f3477 Complete report improvements: disclosures, CTAs, legal, modern stack
```
