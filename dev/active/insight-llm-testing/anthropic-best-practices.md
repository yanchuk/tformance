# Anthropic Claude 4.x Prompt Engineering Best Practices

**Research Date**: 2025-12-31
**Sources**:
- [Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

## Key Principles for Our Dashboard Insight Prompts

### 1. Be Explicit and Specific
Claude 4.x takes instructions literally. Previous models inferred intent; new models do exactly what asked.

**Apply to our prompts:**
- Instead of: "pick the first priority that applies"
- Use: Explicit step-by-step checking with clear conditions

### 2. Provide Context/Motivation
Explain WHY rules exist - Claude generalizes from explanations.

**Apply to our prompts:**
```
Quality crises (>8% reverts) must be flagged first because they indicate
customer-facing issues that require immediate attention, regardless of
other positive metrics.
```

### 3. Use Structured Prompts with XML Tags
Claude was trained on structured prompts. Use semantic sections:
- `<priority_rules>` - Decision logic
- `<examples>` - Canonical examples
- `<output_format>` - JSON schema
- `<context>` - Background information

### 4. Be Vigilant with Examples
Claude 4.x pays VERY close attention to examples. Use:
- Diverse, canonical examples (not edge case laundry lists)
- Examples that show correct priority ordering
- Examples that demonstrate what NOT to do

### 5. Tell Claude What To Do (Not What Not To Do)
Instead of: "Don't mention AI when quality is bad"
Use: "When revert_rate > 8%, your headline must address quality concerns"

### 6. Match Prompt Style to Output Style
- If you want JSON without markdown, don't use markdown in prompt
- Keep prompt formatting minimal and clean

### 7. Right Altitude for Instructions
Avoid extremes:
- ❌ Too specific: Complex hardcoded logic
- ❌ Too vague: "Prioritize important things"
- ✅ Just right: "Check revert_rate first. If > 8%, focus on quality"

### 8. Minimal High-Signal Tokens
Every token uses attention budget. Include only what's necessary.

## Applied Changes for Dashboard Insights

### System Prompt Structure
```xml
<role>
You are an engineering metrics analyst helping CTOs understand team performance.
</role>

<priority_rules>
<!-- Explicit sequential rules with conditions -->
</priority_rules>

<examples>
<!-- 2-3 canonical examples showing correct priority -->
</examples>

<output_format>
<!-- JSON schema with field descriptions -->
</output_format>
```

### Priority Checking Pattern
Instead of numbered list, use explicit conditional logic:
```
STEP 1: Check revert_rate
- Condition: revert_rate > 8%
- Action: Headline MUST address quality crisis
- Rationale: Quality issues affect customers directly
- If TRUE: Stop here. Focus on quality.
- If FALSE: Continue to STEP 2

STEP 2: Check AI impact significance
- Conditions: ai_adoption > 40% AND |cycle_time_diff| > 25%
- Action: Headline MUST address AI impact on velocity
...
```

### Few-Shot Examples Format
```
<example priority="quality_crisis">
Input metrics:
- revert_rate: 12%
- ai_adoption: 45%
- ai_cycle_time_diff: -10% (AI helps)

Correct headline: "Quality concern: 12% of PRs were reverted this period"
NOT: "AI adoption at 45% is helping reduce cycle time by 10%"

Rationale: Quality crisis (12% > 8%) takes priority over AI benefits.
</example>
```

### JSON Output Enforcement
```
Return ONLY a JSON object. No markdown fences, no explanations, no thinking.
The response must start with { and end with } - nothing before or after.
```

## Test Strategy Based on Best Practices

1. **Canonical Examples Test**: Does model follow the example patterns?
2. **Priority Conflict Test**: When multiple conditions apply, does model follow order?
3. **Boundary Test**: Test exact threshold values (8.0% vs 8.1%)
4. **Context Generalization Test**: Does model generalize from rationales?
