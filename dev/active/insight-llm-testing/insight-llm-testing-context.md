# Dashboard Insight LLM Testing - Context

**Last Updated**: 2025-12-31 (Session 3 - Prompt Quality Improvements)

## Related Work

**Actionable Insight Links** - Now complete! See `dev/active/dashboard-insights/` for full documentation.
The schema now includes an `actions` array with enum-based action types that resolve to PR list URLs.

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/services/insight_llm.py` | LLM service with model config, JSON schema, system prompt | Active |
| `apps/metrics/prompts/templates/insight/user.jinja2` | User prompt template (metrics data injection) | Active |
| `apps/metrics/prompts/insight_golden_tests.py` | 16 golden test scenarios with expected behaviors | Active |
| `apps/metrics/prompts/insight_promptfoo.yaml` | Promptfoo evaluation configuration | Active |

## Model Configuration

```python
# Primary model - fast, cheap, good JSON output
INSIGHT_MODEL = "openai/gpt-oss-20b"

# Fallback model - reliable reasoning
INSIGHT_FALLBACK_MODEL = "llama-3.3-70b-versatile"

# Schema enforcement
response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "insight_response",
        "strict": True,
        "schema": INSIGHT_SCHEMA
    }
}
```

## JSON Schema

```python
INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string", "description": "1-sentence executive summary"},
        "detail": {"type": "string", "description": "2-3 sentences of context"},
        "recommendation": {"type": "string", "description": "1 actionable next step"},
        "metric_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "trend": {"type": "string", "enum": ["positive", "negative", "neutral", "warning"]}
                }
            }
        },
        "actions": {  # Added in Session 2, minItems changed to 2 in Session 3
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "enum": ["view_ai_prs", "view_non_ai_prs", "view_slow_prs", "view_reverts", "view_large_prs", "view_contributors", "view_review_bottlenecks"]},
                    "label": {"type": "string"}
                }
            },
            "minItems": 2,  # Changed from 1 to ensure richer insights
            "maxItems": 3
        }
    },
    "required": ["headline", "detail", "recommendation", "metric_cards", "actions"],
    "additionalProperties": False
}
```

## Priority Order for Headlines

The system prompt enforces this CTO-relevant priority:

1. **Quality crisis** - `revert_rate > 8%`
2. **AI impact significant** - `adoption > 40% AND |cycle_time_diff| > 25%`
3. **Severe slowdown** - `cycle_time pct_change > 50%`
4. **Major throughput change** - `|pct_change| > 30%`
5. **Bottleneck detected** - review/deploy delays
6. **Bus factor risk** - `top_contributor_pct > 50%`
7. **Otherwise** - summarize notable change

## Golden Test Categories

| Category | Test IDs | Expected Keywords |
|----------|----------|-------------------|
| Cycle Time | cycle_time_regression | "slow", "cycle" |
| Throughput | throughput_drop | "throughput", "drop" |
| AI Impact | ai_helping, ai_not_helping | "ai", "faster/slower" |
| Quality | high_revert_rate | "revert", "quality" |
| Bottlenecks | bottleneck_detected | "bottleneck", "review/deploy" |
| Bus Factor | bus_factor_risk | "contributor", "risk" |
| Edge Cases | stagnation, no_ai_adoption, low_activity | various |

## Promptfoo Assertion Format

**Critical**: JavaScript assertions must be single-line. Multiline causes parse errors.

```yaml
# CORRECT - single line
assert:
  - type: javascript
    value: "JSON.parse(output).headline.toLowerCase().includes('revert')"

# WRONG - multiline (causes "must return boolean" error)
assert:
  - type: javascript
    value: |
      const result = JSON.parse(output);
      return result.headline.toLowerCase().includes('revert');
```

## Dependencies

### Python
- `groq` - Groq API SDK
- `jinja2` - Prompt templating

### NPM
- `promptfoo` - LLM evaluation framework

### Environment
- `GROQ_API_KEY` - Required for LLM API calls

## Session 3: Quality Improvements (2025-12-31)

After validating insights across 10 random teams, identified 3 improvement areas:

### Quality Grades Before Improvements
| Component | Grade | Issue |
|-----------|-------|-------|
| Headlines | A | Good - concise, actionable |
| Detail Text | A- | Good - uses specific numbers |
| Possible Causes | B+ | Sometimes vague, missing data references |
| Recommendation | B | Sometimes generic, lacks specific targets |
| Metric Cards | A | Uses exact pre-computed values |
| Actions | B- | Often only 1 action (should be 2-3) |

### Changes Made
1. **Actions minimum increased**: `minItems: 1` → `minItems: 2` in JSON schema
2. **Rule 2 enhanced**: Possible causes must include specific numbers from data
3. **Rule 3 enhanced**: Recommendations must include person name, number, or measurable goal
4. **Rule 4 enhanced**: Added examples for action selection, emphasized minimum 2 required
5. **Fallback function updated**: Always returns at least 2 actions

### Prompt Examples Added
```
BAD: "Large PRs may cause delays" (no specific numbers)
GOOD: "Large PRs (32% over 500 lines) are adding 40h to average cycle time"

BAD: "Consider improving code review practices" (vague)
GOOD: "Redistribute reviews from crazywoola (22 pending) to balance workload"
```

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Primary model | GPT-OSS-20B | Fast, cheap ($0.04/1M tokens), good JSON |
| Fallback model | Llama-3.3-70B | More reliable reasoning when primary fails |
| Schema enforcement | strict + additionalProperties:false | Prevent hallucinated fields |
| include_reasoning | false | Suppress thinking tokens for cleaner output |
| Test framework | Promptfoo | Industry standard, supports multiple providers |
| Minimum actions | 2 | Ensure insights are actionable with multiple paths |

## Known Issues

1. **Promptfoo pass rate (25%)** - GPT-OSS-20B produces different wording than expected in some tests
2. **Model variability** - Same prompt can produce different outputs across runs
3. **Assertion specificity** - Need looser matching (synonyms) or tighter prompts

## Related Documentation

- [AI-DETECTION-TESTING.md](../../../prd/AI-DETECTION-TESTING.md) - AI detection patterns
- [insight_llm.py](../../../apps/metrics/services/insight_llm.py) - Service implementation
- [Promptfoo docs](https://www.promptfoo.dev/docs/) - Evaluation framework
