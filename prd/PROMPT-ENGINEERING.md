# Prompt Engineering Guidelines

**Last Updated**: 2025-12-31
**Primary Source**: OpenAI Prompt Engineering Guide
**Secondary Source**: Anthropic Claude 4.x Best Practices

This document captures prompt engineering best practices for LLM prompts in Tformance.

## Sources

- [OpenAI Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering) (Primary)
- [OpenAI Reasoning Best Practices](https://platform.openai.com/docs/guides/reasoning-best-practices)
- [Anthropic Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

---

## Model Selection Mental Model

> **GPT models are like junior coworkers** - they perform best with explicit instructions to create specific outputs.
>
> **Reasoning models are like senior coworkers** - give them a goal and trust them to work out the details.

Since we use **GPT-OSS models** (OpenAI architecture), we need **precise, explicit instructions**.

---

## Prompt Structure (OpenAI Order)

OpenAI recommends this section order:

```
1. IDENTITY    - Purpose, communication style, high-level goals
2. INSTRUCTIONS - Rules, what to do, constraints
3. EXAMPLES    - Input/output pairs showing desired behavior
4. CONTEXT     - Additional data (best at the end for prompt caching)
```

### Formatting Guidelines

Use **both Markdown AND XML**:
- **Markdown headers** (`#`, `##`) for major sections
- **Markdown lists** for instructions and rules
- **XML tags** to delineate content boundaries (examples, context data)
- **XML attributes** for metadata (`<example id="1">`)

---

## Section-by-Section Guide

### 1. Identity Section

Define WHO the assistant is and its high-level goals.

```markdown
# Identity

You are an engineering metrics analyst helping CTOs understand their
team's performance and make data-driven decisions.

Your goal is to surface the single most important insight from the
metrics data and provide an actionable recommendation.
```

### 2. Instructions Section

Provide **explicit, precise rules**. GPT models need clear guidance.

```markdown
# Instructions

## Priority Rules
Check these conditions IN ORDER. Use the FIRST that matches, then stop.

1. **Quality Crisis**: If revert_rate > 8%, headline must address quality
2. **AI Impact**: If ai_adoption >= 40% AND |cycle_diff| >= 25%, address AI
3. **Slowdown**: If cycle_time_change > 50%, address delivery delays
...

## Output Rules
- Return ONLY valid JSON
- Start with { and end with }
- No markdown fences, no explanations
```

**OpenAI tip**: Be very specific about your end goal. Encourage the model to keep iterating until it matches your success criteria.

### 3. Examples Section

Few-shot learning steers the model toward desired behavior. Use XML tags with IDs.

```markdown
# Examples

<example id="quality-crisis">
<input>
- revert_rate: 12%
- ai_adoption: 45%
- ai_cycle_diff: -10%
</input>

<output>
{
  "headline": "Quality alert: 12% of PRs were reverted...",
  "detail": "Despite positive AI metrics...",
  ...
}
</output>

<reasoning>
Quality crisis (12% > 8%) takes priority over AI benefits.
</reasoning>
</example>
```

**Best practices for examples**:
- Show **diverse range** of inputs with desired outputs
- Include **reasoning** to explain why the output is correct
- Use **3-5 examples** for complex tasks
- Ensure examples **align exactly** with instructions (no contradictions)

### 4. Context Section

Place variable context at the **end** of the prompt for prompt caching benefits.

```markdown
# Context

The following metrics are from the team's engineering dashboard:

<metrics>
{{METRICS_DATA}}
</metrics>
```

---

## GPT-Specific Best Practices

### Explicit Role and Workflow

Frame the model with clear responsibilities:

```markdown
# Identity

You are a metrics analyst agent. Your responsibilities:
1. Analyze the provided engineering metrics
2. Apply priority rules to identify the most critical finding
3. Generate a structured JSON response
```

### Decompose Complex Tasks

For multi-step tasks, break them down explicitly:

```markdown
# Instructions

Follow these steps:

Step 1: Check each priority condition in order
Step 2: Stop at the first matching condition
Step 3: Generate headline addressing that priority
Step 4: Write supporting detail with specific numbers
Step 5: Provide one actionable recommendation
Step 6: Build metric cards for the 4 key indicators
```

### Preambles for Transparency (Optional)

Ask the model to explain its reasoning:

```markdown
Before generating the response, briefly state which priority
condition matched and why.
```

---

## JSON Output Best Practices

### Be Explicit About Format

```markdown
# Output Format

Return a JSON object with exactly these fields:

{
  "headline": "1-2 sentence executive summary",
  "detail": "2-3 sentences with context",
  "recommendation": "One actionable step",
  "metric_cards": [
    {"label": "string", "value": "string", "trend": "positive|negative|neutral|warning"}
  ]
}

CRITICAL:
- Start response with { character
- End response with } character
- No markdown code fences (```)
- No text before or after the JSON
```

### Handle Model Quirks in Testing

Some models add thinking text. Use transforms in promptfoo:

```yaml
options:
  transform: |
    (() => {
      const m = output.match(/\{\s*"headline"/);
      return m ? output.slice(m.index) : output;
    })()
```

---

## Combining OpenAI + Anthropic Patterns

### From OpenAI (Primary):
- Identity → Instructions → Examples → Context order
- Explicit, precise instructions for GPT models
- Decompose complex tasks into steps
- Markdown headers for sections

### From Anthropic (Supplementary):
- XML tags for content boundaries (`<example>`, `<output>`)
- Include "Why" rationale for rules
- "Tell what TO do" over "what NOT to do"
- Combine XML + examples + chain of thought

---

## Complete Prompt Template

```markdown
# Identity

You are an engineering metrics analyst helping CTOs understand their
team's performance and make data-driven decisions.

# Instructions

## Task
Analyze engineering metrics and generate an executive insight with:
1. A headline addressing the most critical finding
2. Context with key numbers
3. One actionable recommendation
4. Four metric cards

## Priority Rules
Check IN ORDER. Use FIRST match, then stop.

1. **Quality Crisis**: revert_rate > 8% → Address quality
2. **AI Impact**: ai_adoption >= 40% AND |diff| >= 25% → Address AI
3. **Slowdown**: cycle_time_change > 50% → Address delays
4. **Throughput**: |throughput_change| > 30% → Address output change
5. **Bottleneck**: bottleneck_detected → Address review delays
6. **Bus Factor**: team_size > 3 AND top_contributor > 50% → Address risk
7. **General**: None above → Summarize notable trend

## Output Format
Return JSON starting with { and ending with }. No markdown fences.

{
  "headline": "1-2 sentences on highest priority",
  "detail": "2-3 sentences with numbers",
  "recommendation": "One action",
  "metric_cards": [4 cards with label/value/trend]
}

# Examples

<example id="quality-crisis">
<input>revert_rate: 12%, ai_adoption: 45%, ai_diff: -10%</input>
<output>{"headline": "Quality alert: 12% reverts...", ...}</output>
<reasoning>Quality (12% > 8%) beats AI benefits</reasoning>
</example>

<example id="bus-factor">
<input>team_size: 5, top_contributor: 65%, revert_rate: 2%</input>
<output>{"headline": "Dependency risk: 65% from one person...", ...}</output>
<reasoning>Bus factor (65% > 50%, team > 3) applies</reasoning>
</example>

# Context

<metrics>
{{METRICS_DATA}}
</metrics>
```

---

## Testing Workflow

1. **Run evaluation**: `npx promptfoo eval -c config.yaml --no-cache`
2. **View results**: `npx promptfoo view` (localhost:15500)
3. **Human review**: Check semantic quality, not just keyword matches
4. **Iterate**: Fix failures, add test cases, re-run

---

## File Locations

| File | Purpose |
|------|---------|
| `apps/metrics/prompts/templates/insight/` | Jinja2 prompt templates |
| `apps/metrics/prompts/system_prompt_v2.txt` | Current system prompt |
| `apps/metrics/prompts/insight_promptfoo_v2.yaml` | Promptfoo config |
| `apps/metrics/services/insight_llm.py` | LLM service |
| `prd/PROMPT-ENGINEERING.md` | This guide |
