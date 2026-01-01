# Dashboard Insight Prompt Improvement Strategy

**Created**: 2025-12-31
**Status**: In Progress

## Problem Analysis

### Failure Types Identified

| Problem | Affected Models | Root Cause | Impact |
|---------|----------------|------------|--------|
| JSON truncation/trailing content | OSS-20B, OSS-120B | Model adds text after JSON closing `}` | 4/24 failures |
| Priority order violation | Llama-3.3-70B | Always defaults to AI impact headline | 2/24 failures |
| Schema placeholder copying | OSS-20B | Model copies example text literally | 1/24 failures |

### Current Pass Rates
- GPT-OSS-20B: 62.5% (5/8)
- GPT-OSS-120B: 87.5% (7/8)
- Llama-3.3-70B: 75.0% (6/8)

### Detailed Failure Examples

**Priority Violation (Llama-3.3)**:
- **Test 3**: 12% reverts (quality crisis threshold = 8%)
  - Expected: "Quality crisis: 12% of PRs reverted"
  - Actual: "AI-assisted PRs being 9.5% faster"

- **Test 13**: 65% top contributor (bus factor threshold = 50%)
  - Expected: "Work concentration risk - 65% from one contributor"
  - Actual: "AI-assisted PRs being 12% faster"

**JSON Issues (OSS models)**:
- Model outputs valid JSON but adds trailing period/text
- Position 800-900 has extra content after `}`

## Hypotheses

### H1: Priority Order Needs Explicit Sequential Checking
Models don't naturally follow priority cascades. They need to be forced to check each condition explicitly and STOP when first match is found.

### H2: Few-Shot Examples Enforce Priority Better Than Rules
Showing concrete examples of "when X, output Y not Z" is more effective than abstract priority rules.

### H3: Structured Reasoning Field Forces Justification
Adding a `priority_reason` field forces the model to explain why it chose that priority, making it more likely to follow the rules.

### H4: Stop Sequences Prevent JSON Trailing Content
Explicit "STOP after closing brace" instructions or stop sequences can prevent trailing content.

## Prompt Variants to Test

### Variant A: Chain-of-Thought Priority (CoT)
Force explicit sequential checking with early termination.

```
Before generating output, check these conditions IN ORDER. Use the FIRST that applies and STOP:

STEP 1: Is revert_rate > 8%?
- If YES: Your headline MUST start with quality/revert concern. STOP checking.
- If NO: Continue to STEP 2.

STEP 2: Is AI adoption > 40% AND |cycle_time_difference| > 25%?
- If YES: Your headline MUST focus on AI impact. STOP checking.
...
```

### Variant B: Few-Shot Examples
Add 2-3 concrete examples showing correct priority handling.

```
EXAMPLES OF CORRECT PRIORITY:

Example 1:
- Data: revert_rate=12%, AI adoption=45%, AI cycle time 10% faster
- Correct headline: "Quality crisis: 12% of PRs were reverted this month"
- WRONG: "AI tools are helping with 10% faster cycle time"
- WHY: Quality crisis (>8% reverts) takes priority over AI impact

Example 2:
- Data: revert_rate=2%, top_contributor=65%, AI adoption=30%
- Correct headline: "High bus factor risk: one engineer owns 65% of PRs"
- WRONG: "Team is making steady progress with 30% AI adoption"
- WHY: Bus factor risk (>50%) applies; AI adoption is below threshold
```

### Variant C: Structured Reasoning Output
Add explicit priority tracking fields.

```json
{
  "priority_check": {
    "quality_crisis": false,
    "ai_impact": true,
    "slowdown": false,
    "throughput_change": false,
    "bottleneck": false,
    "bus_factor": false
  },
  "priority_applied": "ai_impact",
  "priority_reason": "AI adoption is 70% (>40%) and cycle time difference is 46% (>25%)",
  "headline": "...",
  "detail": "...",
  "recommendation": "...",
  "metric_cards": [...]
}
```

### Variant D: Negative Examples (Anti-patterns)
Explicitly show what NOT to do.

```
COMMON MISTAKES TO AVOID:

MISTAKE 1: Mentioning AI when quality is poor
- If revert_rate > 8%, NEVER lead with AI metrics
- Quality problems are more urgent than AI benefits

MISTAKE 2: Focusing on positive trends when risks exist
- If top_contributor > 50%, this is a RISK that must be highlighted
- Don't bury risks behind positive metrics
```

## Test Matrix

### Priority Isolation Tests (one condition at a time)
| Test ID | Priority | Trigger Condition | Expected Headline Keywords |
|---------|----------|-------------------|---------------------------|
| P1 | Quality Crisis | revert_rate = 12% | revert, quality, 12% |
| P2 | AI Impact Positive | adoption=70%, diff=-46% | AI, faster, 46% |
| P3 | AI Impact Negative | adoption=70%, diff=+100% | AI, slower, twice |
| P4 | Severe Slowdown | cycle_time +80% | cycle, slow, 80% |
| P5 | Throughput Drop | throughput -64% | throughput, drop, 64% |
| P6 | Bus Factor | top_contributor = 65% | concentration, risk, 65% |

### Priority Conflict Tests (multiple conditions, test cascade)
| Test ID | Conditions | Expected Priority | Trap |
|---------|------------|-------------------|------|
| C1 | revert=12% AND AI=45% | Quality Crisis | Don't mention AI benefits |
| C2 | bus_factor=65% AND AI=30% | Bus Factor | AI adoption is low anyway |
| C3 | slowdown=80% AND throughput=+10% | Slowdown | Don't focus on throughput |
| C4 | revert=9% AND AI=50% diff=+30% | Quality Crisis | AI is hurting, but quality first |

### Edge Case Tests
| Test ID | Scenario | Expected Behavior |
|---------|----------|-------------------|
| E1 | revert_rate = 8.0% (at threshold) | Should NOT trigger quality crisis |
| E2 | revert_rate = 8.1% (just over) | SHOULD trigger quality crisis |
| E3 | All metrics healthy | General summary, positive tone |
| E4 | Zero AI adoption | Don't mention AI impact |

## Evaluation Plan

### Phase 1: Automated Assertions
- JSON validity
- Required fields present
- Keyword matching for priority compliance

### Phase 2: Human Evaluation in Promptfoo UI
**HUMAN REVIEWER INSTRUCTIONS:**

1. Open promptfoo view: `npx promptfoo view`
2. Navigate to the evaluation results
3. For each test, evaluate:
   - [ ] Is the headline genuinely useful for a CTO?
   - [ ] Does the priority feel correct given the data?
   - [ ] Is the recommendation actionable?
   - [ ] Is the tone professional and concise?

4. Rate each response:
   - 3 = Excellent (would ship to production)
   - 2 = Good (acceptable with minor issues)
   - 1 = Poor (wrong priority, confusing, or unhelpful)
   - 0 = Fail (JSON issues, placeholder text, nonsensical)

5. Add comments explaining any rating below 3

### Success Criteria
- Pass rate >= 90% across all providers
- Human rating average >= 2.5
- Zero JSON parsing failures
- 100% priority order compliance on conflict tests

## Implementation Order

1. Create new promptfoo config with all variants
2. Add comprehensive test matrix (priority + conflict + edge)
3. Run evaluation with --no-cache
4. Human review in promptfoo UI
5. Iterate on best-performing variant
