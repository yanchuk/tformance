# Insight Prompt Sections - Context

**Last Updated:** 2026-01-11

## Key Files

### Templates (Modify)

| File | Purpose | Changes |
|------|---------|---------|
| `apps/metrics/prompts/templates/insight/system.jinja2` | Main system prompt | Split into includes |
| `apps/metrics/prompts/templates/insight/sections/` | NEW directory | Create 7 section files |

### Python (Modify)

| File | Purpose | Changes |
|------|---------|---------|
| `apps/metrics/prompts/render.py` | Template rendering | Add `include_copilot` param |
| `apps/metrics/services/insight_llm.py` | LLM service | Pass Copilot flag |

### Tests (Modify)

| File | Purpose | Changes |
|------|---------|---------|
| `apps/metrics/prompts/tests/test_render.py` | Render tests | Add Copilot conditional tests |

## Section Mapping

| Section File | Source Lines | Content |
|--------------|--------------|---------|
| `identity.jinja2` | 2-5 | "You are a senior engineering manager..." |
| `output_format.jinja2` | 9-11 | JSON format specification |
| `mention_syntax.jinja2` | 13-16 | @username and @@username rules |
| `writing_rules.jinja2` | 17-43 | DO/DON'T, number conversions, special cases |
| `copilot_guidance.jinja2` | 44-63 | Copilot thresholds and prioritization |
| `action_types.jinja2` | 65-67 | Action type enum list |
| `examples.jinja2` | 69-116 | Good/bad examples with scenarios |

## Key Decisions

### 1. Cache Strategy

**Decision:** Use `maxsize=2` for cached prompt (True/False variants)

**Rationale:**
- Only 2 possible values for `include_copilot`
- First call caches, subsequent calls are instant
- Clear invalidation semantics

### 2. Default Behavior

**Decision:** `include_copilot=True` by default

**Rationale:**
- Backward compatible with existing code
- Explicit opt-out for no-Copilot teams
- Safer default (more info > less info)

### 3. Conditional Location

**Decision:** Conditional in `system.jinja2`, not individual sections

**Rationale:**
- Single point of control
- Easier to understand flow
- Matches existing user.jinja2 pattern

## Data Flow

```
Team.has_copilot_seats (≥5)
        ↓
gather_insight_data() → copilot_metrics = {...} or None
        ↓
generate_insight_from_groq()
        ↓
has_copilot = data.get("copilot_metrics") is not None
        ↓
get_insight_system_prompt(include_copilot=has_copilot)
        ↓
render_insight_system_prompt(include_copilot=has_copilot)
        ↓
{% if include_copilot %}
{% include 'insight/sections/copilot_guidance.jinja2' %}
{% endif %}
```

## Test Scenarios

### Scenario A: Team with Copilot (≥5 seats)

```python
data = gather_insight_data(team, start, end)
# data["copilot_metrics"] = {"avg_acceptance_rate": 35.2, ...}
# System prompt INCLUDES Copilot guidance
```

### Scenario B: Team without Copilot (<5 seats or none)

```python
data = gather_insight_data(team, start, end)
# data["copilot_metrics"] = None
# System prompt EXCLUDES Copilot guidance (~200 chars shorter)
```

## Dependencies

### Upstream (These feed into our code)

- `CopilotSeatSnapshot` model - determines Copilot availability
- `gather_insight_data()` - populates `copilot_metrics` key

### Downstream (Our code feeds into these)

- `generate_insight_from_groq()` - consumes system prompt
- Dashboard insight display - unchanged

## Reference Implementation

### PR Analysis Pattern (to follow)

```jinja2
{#- PR Analysis System Prompt (v{{ version }}) -#}
{% include 'pr_analysis/sections/intro.jinja2' %}
{% include 'pr_analysis/sections/ai_detection.jinja2' %}
...
{% include 'pr_analysis/sections/enums.jinja2' -%}
```

### User Template Conditional (already working)

```jinja2
{% if copilot_metrics %}
### GitHub Copilot Usage
{% include 'sections/copilot_metrics.jinja2' %}
{% endif %}
```

## Related Documentation

- `dev/active/type-hints-refactor/` - Recent type hints work
- `prd/AI-DETECTION-TESTING.md` - Prompt testing guidelines
- `CLAUDE.md` - Coding guidelines
