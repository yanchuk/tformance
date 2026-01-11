# Prompt Single Source of Truth - Context

**Last Updated:** 2026-01-11

## Key Files

### Files to Modify

| File | Lines | Purpose | Changes Needed |
|------|-------|---------|----------------|
| `apps/metrics/services/llm_prompts.py` | 1043 | Main prompt module | Remove hardcoded string, add wrapper |
| `apps/metrics/tasks.py` | 400+ | Celery tasks | Update import |
| `apps/integrations/services/groq_batch.py` | 800+ | Batch LLM processing | Update import |
| `apps/metrics/prompts/__init__.py` | 40 | Module exports | Update exports |
| `apps/metrics/management/commands/run_llm_analysis.py` | 150 | CLI command | Update import |
| `apps/metrics/management/commands/compare_llm_models.py` | 180 | Model comparison | Update import |

### Files to Keep (No Changes)

| File | Lines | Purpose | Status |
|------|-------|---------|--------|
| `apps/metrics/prompts/render.py` | 200 | Jinja2 rendering | Source of truth - keep as-is |
| `apps/metrics/prompts/templates/system.jinja2` | 15 | Main system template | Source of truth |
| `apps/metrics/prompts/templates/user.jinja2` | 182 | User prompt template | Source of truth |
| `apps/metrics/prompts/templates/sections/*.jinja2` | ~800 | Section templates | Source of truth |

### Test Files to Update

| File | Tests | Changes |
|------|-------|---------|
| `apps/metrics/tests/test_llm_prompts.py` | 80+ | Update to use `get_system_prompt()` |
| `apps/metrics/prompts/tests/test_render.py` | 30+ | Remove comparison tests (no longer needed) |
| `apps/metrics/prompts/tests/test_export.py` | 10+ | Update import |

## Key Decisions

### Decision 1: Wrapper vs Direct Import

**Options:**
1. Direct import from `render.py` everywhere
2. Wrapper function in `llm_prompts.py` for backward compatibility

**Chosen:** Option 2 - Wrapper function

**Rationale:**
- Minimal changes to existing imports
- Centralized caching with `@lru_cache`
- Easier to add deprecation warnings later
- Maintains `llm_prompts.py` as the public API

### Decision 2: Caching Strategy

**Options:**
1. No caching - render every time
2. `@lru_cache(maxsize=1)` - cache single result
3. Module-level cache variable

**Chosen:** Option 2 - `@lru_cache(maxsize=1)`

**Rationale:**
- Simple, standard Python pattern
- Prompt rarely changes during runtime
- Easy to invalidate if needed (`get_system_prompt.cache_clear()`)
- Thread-safe

### Decision 3: get_user_prompt() Handling

**Options:**
1. Keep full implementation, add equivalence tests
2. Replace with wrapper to `render_user_prompt()`
3. Deprecate and point to `render_user_prompt()`

**Chosen:** Option 2 - Replace with wrapper

**Rationale:**
- Eliminates code duplication
- Single source of truth for user prompts too
- Backward compatible API
- `render_user_prompt()` already has all parameters

### Decision 4: Backward Compatibility Period

**Options:**
1. Break immediately - update all imports
2. Keep `PR_ANALYSIS_SYSTEM_PROMPT` as computed property with deprecation warning
3. Keep as constant, compute at module load

**Chosen:** Option 3 - Compute at module load

**Rationale:**
- Simplest implementation
- No deprecation noise in logs
- Can convert to function later if needed
- Existing code using the constant continues to work

## Dependencies

### Runtime Dependencies

```
render.py
    └── jinja2 (always available)
    └── PROMPT_VERSION from llm_prompts.py (circular import risk!)

llm_prompts.py
    └── render.py (new dependency)
```

### Circular Import Solution

Current: `render.py` imports `PROMPT_VERSION` from `llm_prompts.py`

Solution: Keep `PROMPT_VERSION` in `llm_prompts.py`, import only in `get_system_prompt()`:

```python
def get_system_prompt() -> str:
    # Late import to avoid circular dependency
    from apps.metrics.prompts.render import render_system_prompt
    return render_system_prompt()
```

## Code Snippets

### Before (llm_prompts.py)

```python
# Line 38-416 - REMOVE THIS
PROMPT_VERSION = "8.2.0"

PR_ANALYSIS_SYSTEM_PROMPT = """# Identity
You are a senior engineering analyst...
[375 lines of hardcoded prompt]
"""

def get_user_prompt(pr_body, pr_title="", ...):
    """Generate user prompt with full PR context."""
    sections = []
    # 171 lines of Python string building
    ...
```

### After (llm_prompts.py)

```python
from functools import lru_cache

PROMPT_VERSION = "8.2.0"

@lru_cache(maxsize=1)
def get_system_prompt() -> str:
    """Get the system prompt from Jinja2 templates (cached).

    The SINGLE SOURCE OF TRUTH is: apps/metrics/prompts/templates/
    Edit those templates, not this function.
    """
    from apps.metrics.prompts.render import render_system_prompt
    return render_system_prompt()

# Backward compatibility - computed at module load
PR_ANALYSIS_SYSTEM_PROMPT = get_system_prompt()

def get_user_prompt(
    pr_body: str,
    pr_title: str = "",
    # ... all existing parameters
) -> str:
    """Generate user prompt with full PR context.

    Delegates to render_user_prompt() - the Jinja2 template is the source of truth.
    """
    from apps.metrics.prompts.render import render_user_prompt
    return render_user_prompt(
        pr_body=pr_body,
        pr_title=pr_title,
        # ... pass all parameters
    )
```

## Testing Strategy

### Baseline Tests (Must Pass Before Changes)

```bash
# Run all prompt-related tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Run tasks tests
.venv/bin/pytest apps/metrics/tests/test_llm_tasks.py -v
```

### New Tests (TDD - Write First)

```python
class TestSingleSourceOfTruth(TestCase):
    def test_no_hardcoded_prompt_string(self):
        """Verify PR_ANALYSIS_SYSTEM_PROMPT is not a string literal."""
        import inspect
        source = inspect.getsource(llm_prompts)
        # Should not have multi-line string assignment
        self.assertNotIn('PR_ANALYSIS_SYSTEM_PROMPT = """', source)

    def test_get_system_prompt_matches_templates(self):
        """get_system_prompt() should return rendered template."""
        from apps.metrics.prompts.render import render_system_prompt
        result = get_system_prompt()
        expected = render_system_prompt()
        self.assertEqual(result, expected)

    def test_get_user_prompt_matches_render(self):
        """get_user_prompt() should match render_user_prompt()."""
        from apps.metrics.prompts.render import render_user_prompt
        context = {"pr_body": "Test", "pr_title": "Title"}
        result = get_user_prompt(**context)
        expected = render_user_prompt(**context)
        self.assertEqual(result, expected)
```

## Rollback Plan

If issues arise:

1. Revert the commit
2. `PR_ANALYSIS_SYSTEM_PROMPT` hardcoded string is restored
3. All imports continue to work

Low risk due to:
- All changes are in Python (no migrations)
- Comprehensive test coverage
- Backward-compatible API
