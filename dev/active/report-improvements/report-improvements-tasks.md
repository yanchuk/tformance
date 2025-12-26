# Report Improvements - Tasks

**Last Updated: 2025-12-27**

## Phase 1: HIGH Risk Items (Must Fix)

### 1.1 Add Copilot/ChatGPT Disclosure
- [ ] Add callout box in "AI Tool Evolution" section explaining why Copilot/ChatGPT are absent
- [ ] Text: "Our tool rankings reflect *disclosed* usage patterns in OSS PRs, not total market share. Tools that leave visible artifacts (CodeRabbit, Devin) appear dominant because we can detect them. Silent tools (Copilot autocomplete, ChatGPT for research) are likely underrepresented by 5-10x."

### 1.2 Improve Adoption Gap Explanation
- [ ] Add visual comparison table in "Industry Context" section
- [ ] Show: What each metric measures, why they're not comparable
- [ ] Include "hidden adoption" iceberg analogy
- [ ] Emphasize our 21.4% is the **floor**, real rate likely 40-60%

## Phase 2: MEDIUM Risk Items (Should Fix)

### 2.1 Add Cycle Time Causal Disclaimer
- [ ] Add warning box after "+42% cycle time" finding
- [ ] Text: "The +42% cycle time finding shows correlation, not causation. We cannot determine if AI slows delivery or if teams choose AI for inherently complex work. Controlled studies would be needed to establish causation."
- [ ] List alternative explanations (review iterations, selection bias, discussion volume)

### 2.2 Include Trust Metrics
- [ ] Add to "Key Survey Insights (2025)" section
- [ ] Text: "**Trust Reality:** While AI tool usage grows, trust is declining. Stack Overflow 2025 reports 46% of developers actively distrust AI tool accuracy, up from 2024. Only 3% 'highly trust' outputs."

### 2.3 Clarify Agent Adoption Denominator
- [ ] Rephrase "30.7% agent adoption"
- [ ] New text: "Among detected AI tool mentions, 30.7% came from autonomous agents (Devin, Cubic). This reflects tool visibility, not developer adoption rates. Industry surveys show only 14% of developers use agents daily."

## Phase 3: LOW Risk Items (Nice to Have)

### 3.1 Qualify Sweet Spot Claim
- [ ] Change "40-60% is Sweet Spot" text
- [ ] Add: "Based on our limited sample, this is observational and may reflect team-specific factors rather than an optimal adoption rate."

### 3.2 Expand Selection Bias Discussion
- [ ] Add data point in methodology
- [ ] Text: "Our sample skews toward well-maintained, popular projects (avg 2,300+ PRs/year). Teams with fewer resources or less active maintenance are not represented."

### 3.3 Add False Negative Caveat
- [ ] Add to "Detection Method Comparison" section
- [ ] Text: "While our detection methods agree 96% of the time, we cannot measure false negatives—PRs that used AI but have no detectable mention. The true AI adoption rate is likely 2-3x higher than our detected rate."

## Phase 4: Chart Responsiveness (If Needed)

### 4.1 Fix Blurry Charts
- [ ] Investigate devicePixelRatio handling in Chart.js
- [ ] Add Chart.defaults.devicePixelRatio config if needed
- [ ] Test at multiple breakpoints (375, 768, 1200, 1920)

### 4.2 Improve Resize Behavior
- [ ] Add window resize event handler to trigger chart.resize()
- [ ] Ensure responsive: true is set on all charts
- [ ] Test dynamic container width changes

## Verification

```bash
# View report locally
open docs/index.html

# Check at different viewports in browser dev tools
# Verify all new disclosure sections render correctly
# Test theme toggle (dark/light)
```

## Notes

- All changes to `docs/index.html` only
- No Django/Python code changes
- No migrations needed
- Commit each phase separately for clear history
