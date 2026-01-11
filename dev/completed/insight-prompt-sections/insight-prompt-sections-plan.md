# Insight Prompt Sections Refactoring Plan

**Last Updated:** 2026-01-11
**Status:** PLANNING
**Effort:** M (4-6 hours)

## Executive Summary

Split the monolithic `insight/system.jinja2` (117 lines) into modular sections following the `pr_analysis/` pattern. Add conditional Copilot section that only renders when team has Copilot enabled. This reduces token waste and improves maintainability.

## Current State Analysis

### Problem

1. **Inconsistent Structure:**
   - `pr_analysis/system.jinja2` → 8 section includes ✅
   - `insight/system.jinja2` → Monolithic file ❌

2. **Wasted Tokens:**
   - System prompt always includes Copilot guidance (lines 44-63)
   - Teams without Copilot still receive ~20 lines of irrelevant instructions
   - Wastes ~800-900 characters (~200 tokens) per insight generation

3. **Current Flow:**
   ```
   gather_insight_data() → copilot_metrics = None (if no Copilot)
                        ↓
   render_insight_system_prompt() → Always includes Copilot section
                        ↓
   User prompt has {% if copilot_metrics %} → Conditional ✅
   System prompt is unconditional ❌
   ```

### Current Files

| File | Lines | Description |
|------|-------|-------------|
| `insight/system.jinja2` | 117 | Monolithic, no sections |
| `insight/user.jinja2` | 128 | Has conditional Copilot |
| `render.py:render_insight_system_prompt()` | No params | Always returns full prompt |

## Proposed Future State

### File Structure

```
templates/insight/
├── system.jinja2                    # Main with includes
├── sections/
│   ├── identity.jinja2              # Lines 2-5
│   ├── output_format.jinja2         # Lines 9-11
│   ├── mention_syntax.jinja2        # Lines 13-16
│   ├── writing_rules.jinja2         # Lines 17-43
│   ├── copilot_guidance.jinja2      # Lines 44-63 (CONDITIONAL)
│   ├── action_types.jinja2          # Lines 65-67
│   └── examples.jinja2              # Lines 69-116
└── user.jinja2                      # Unchanged
```

### New system.jinja2

```jinja2
{#- Insight Generation System Prompt -#}
{% include 'insight/sections/identity.jinja2' %}

{% include 'insight/sections/output_format.jinja2' %}

{% include 'insight/sections/mention_syntax.jinja2' %}

{% include 'insight/sections/writing_rules.jinja2' %}

{% if include_copilot %}
{% include 'insight/sections/copilot_guidance.jinja2' %}
{% endif %}

{% include 'insight/sections/action_types.jinja2' %}

{% include 'insight/sections/examples.jinja2' -%}
```

### Updated render.py

```python
@lru_cache(maxsize=2)  # One for each boolean variant
def render_insight_system_prompt(include_copilot: bool = True) -> str:
    """Render insight system prompt with conditional Copilot section."""
    template = _env.get_template("insight/system.jinja2")
    rendered = template.render(include_copilot=include_copilot)
    return _normalize_whitespace(rendered)

def list_template_sections(template_type: str = "pr_analysis") -> list[str]:
    """List template section files for a given template type."""
    sections_dir = _TEMPLATE_DIR / template_type / "sections"
    if not sections_dir.exists():
        return []
    return sorted([f.name for f in sections_dir.glob("*.jinja2")])
```

### Updated insight_llm.py

```python
# REMOVE @lru_cache from get_insight_system_prompt()
# render_insight_system_prompt() already handles caching
def get_insight_system_prompt(include_copilot: bool = True) -> str:
    """Get the insight system prompt (delegates to cached render function)."""
    from apps.metrics.prompts.render import render_insight_system_prompt
    return render_insight_system_prompt(include_copilot)
```

### Updated insight_llm.py

```python
# In generate_insight_from_groq():
has_copilot = data.get("copilot_metrics") is not None
system_prompt = get_insight_system_prompt(include_copilot=has_copilot)
```

## Implementation Phases

### Phase 1: TDD Setup (30 min)

1. Write failing tests for new functionality
2. Test conditional Copilot section behavior
3. Test section file structure

### Phase 2: Split Template (45 min)

1. Create sections/ directory
2. Extract each section to its own file
3. Update system.jinja2 with includes
4. Add conditional logic for Copilot

### Phase 3: Update Render Functions (30 min)

1. Add `include_copilot` parameter to `render_insight_system_prompt()`
2. Update caching strategy (2 cached versions)
3. Update `get_insight_system_prompt()` in `insight_llm.py`

### Phase 4: Integration (30 min)

1. Pass Copilot flag from `generate_insight_from_groq()`
2. Verify user prompt still works with conditional
3. Run full test suite

### Phase 5: Verification (30 min)

1. Green tests
2. Manual verification of both paths
3. Token count comparison

## Task Breakdown

### Phase 1: TDD Tests (Write First)

| Task | Est | Acceptance Criteria |
|------|-----|---------------------|
| 1.1 Test sections directory exists | S | `list_template_sections('insight')` returns 7 files |
| 1.2 Test with Copilot | S | Prompt contains "Copilot Metrics Guidance" |
| 1.3 Test without Copilot | S | Prompt does NOT contain "Copilot" |
| 1.4 Test cache works | S | Two calls with same flag return identical strings |
| 1.5 Test token savings | S | Without Copilot is ~200 chars shorter |

### Phase 2: Template Split

| Task | Est | Acceptance Criteria |
|------|-----|---------------------|
| 2.1 Create sections directory | S | `templates/insight/sections/` exists |
| 2.2 Extract identity.jinja2 | S | Contains "# Identity" section |
| 2.3 Extract output_format.jinja2 | S | Contains "## Output Format" |
| 2.4 Extract mention_syntax.jinja2 | S | Contains "## Mention Syntax" |
| 2.5 Extract writing_rules.jinja2 | S | Contains "## Writing Rules" + "## Special Cases" |
| 2.6 Extract copilot_guidance.jinja2 | S | Contains "## Copilot Metrics Guidance" |
| 2.7 Extract action_types.jinja2 | S | Contains "## Action Types" |
| 2.8 Extract examples.jinja2 | M | Contains all `<example>` blocks |
| 2.9 Update system.jinja2 | M | Uses includes with conditional |

### Phase 3: Render Functions

| Task | Est | Acceptance Criteria |
|------|-----|---------------------|
| 3.1 Update render_insight_system_prompt | S | Accepts `include_copilot: bool` |
| 3.2 Update caching | S | Uses `maxsize=2` for bool variants |
| 3.3 Update get_insight_system_prompt | S | Accepts `include_copilot: bool` |
| 3.4 Update _LazyInsightPrompt | M | Defaults to `include_copilot=True` |

### Phase 4: Integration

| Task | Est | Acceptance Criteria |
|------|-----|---------------------|
| 4.1 Update generate_insight_from_groq | S | Passes flag based on data |
| 4.2 Verify existing tests pass | M | All 37 insight tests green |
| 4.3 Manual verification | S | Both paths render correctly |

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Template syntax errors | High | TDD - write tests first |
| Nested caching bug | High | Remove cache from `get_insight_system_prompt()` |
| Breaking backward compat | Medium | Default `include_copilot=True` |
| Missing section in split | Low | Add content equivalence test |
| Copilot example without guidance | Medium | Add conditional around example |
| `list_template_sections()` signature | Medium | Update to accept `template_type` param |

## Success Metrics

1. **Tests:** All new tests pass (5+ new tests)
2. **Consistency:** Structure matches `pr_analysis/` pattern
3. **Token Savings:** ~200 chars fewer without Copilot
4. **Behavior:** Both Copilot paths generate valid insights
5. **Coverage:** Existing 37 insight tests still pass

## Dependencies

- No new packages required
- Existing Jinja2 infrastructure
- Existing test patterns to follow

## Verification Commands

```bash
# Run insight tests
.venv/bin/pytest apps/metrics/prompts/tests/test_render.py -v

# Check token difference
.venv/bin/python -c "
from apps.metrics.prompts.render import render_insight_system_prompt
with_cop = render_insight_system_prompt(include_copilot=True)
without = render_insight_system_prompt(include_copilot=False)
print(f'With Copilot: {len(with_cop)} chars')
print(f'Without: {len(without)} chars')
print(f'Savings: {len(with_cop) - len(without)} chars')
"
```
