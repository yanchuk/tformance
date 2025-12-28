# AI Tool Categories - Context & Reference

**Last Updated:** 2025-12-27 (Session 3 - ALL PHASES COMPLETE)

## Current Implementation State

### ALL Phases COMPLETED

| Phase | Status | Key Files |
|-------|--------|-----------|
| Phase 1: Core Service | **DONE** | `apps/metrics/services/ai_categories.py` |
| Phase 2: Model Properties | **DONE** | `apps/metrics/models/github.py` |
| Phase 3: PR List Filter | **DONE** | `apps/metrics/services/pr_list_service.py`, template, view |
| Phase 4: Dashboard Charts | **DONE** | `dashboard_service.py`, tool breakdown template |
| Phase 5: PR Row Display | **DONE** | `pr_list_tags.py`, table.html, expanded_row.html |

### Implementation Summary

**Total Tests:** 102 category-specific tests passing
- 38 tests for category service
- 11 tests for model properties
- 14 tests for PR list filter/stats/options
- 12 tests for dashboard service
- 12 tests for template tags
- 15 additional subtests

## Key Files Modified

| File | Changes |
|------|---------|
| `apps/metrics/services/ai_categories.py` | **NEW** - Complete tool categorization service |
| `apps/metrics/models/github.py` | Added `ai_code_tools`, `ai_review_tools`, `ai_category` properties |
| `apps/metrics/services/pr_list_service.py` | Added category filter, stats, and filter options |
| `apps/metrics/views/pr_list_views.py` | Added `ai_category` to filter_keys |
| `apps/metrics/services/dashboard_service.py` | Updated `get_ai_tool_breakdown()`, added `get_ai_category_breakdown()` |
| `apps/metrics/templatetags/pr_list_tags.py` | Added `ai_category_display`, `ai_category_badge_class` filters |
| `templates/metrics/analytics/pull_requests.html` | Added AI Category dropdown, category stats badges |
| `templates/metrics/partials/ai_tool_breakdown_chart.html` | Grouped tools by category with badges |
| `templates/metrics/pull_requests/partials/table.html` | Shows category badge in AI column |
| `templates/metrics/pull_requests/partials/expanded_row.html` | Shows AI category in expanded details |

## Test Files Created/Modified

| File | Tests Added |
|------|-------------|
| `apps/metrics/tests/test_ai_categories.py` | 38 tests for category service |
| `apps/metrics/tests/test_ai_model_fields.py` | 11 tests for category properties |
| `apps/metrics/tests/test_pr_list_service.py` | 14 tests for category filter/stats/options |
| `apps/metrics/tests/dashboard/test_ai_metrics.py` | 12 tests for tool/category breakdown |
| `apps/metrics/tests/test_pr_list_tags.py` | 12 tests for category template filters |

## Key Decisions Made

### Decision 1: Mixed Tools Default to "code"
- Tools like Ellipsis, Bito, Qodo that can do both are counted as code
- Rationale: If a tool CAN write code, the impact is higher

### Decision 2: LLM Priority in Category Filter
- The `ai_category` filter checks both `ai_tools_detected` AND `llm_summary.ai.tools`
- Uses OR logic: matches if category tools found in either field

### Decision 3: Stats Computed in Python
- `get_pr_stats()` iterates PRs to count categories (not SQL aggregate)
- Reason: `ai_category` is computed from `effective_ai_tools` which considers LLM priority

### Decision 4: Exclude Tools Filtered Out
- `get_ai_tool_breakdown()` now excludes snyk, mintlify, etc.
- They don't appear in charts at all

## Implementation Patterns Established

### Category Filter in QuerySet (pr_list_service.py:_apply_ai_category_filter)

```python
def _apply_ai_category_filter(qs, category):
    """Filter by AI category using Q objects for both LLM and regex sources."""
    # Build contains queries for tool sets
    all_code_tools = CODE_TOOLS | MIXED_TOOLS

    # Check both LLM tools and regex tools
    has_code = llm_has_code | regex_has_code
    has_review = llm_has_review | regex_has_review

    if category == "code":
        qs = qs.filter(has_code)
    elif category == "review":
        qs = qs.filter(has_review)
    elif category == "both":
        qs = qs.filter(has_code & has_review)
```

### Model Properties (github.py)

```python
@property
def ai_category(self) -> str | None:
    """Get AI category based on effective tools."""
    from apps.metrics.services.ai_categories import get_ai_category
    return get_ai_category(self.effective_ai_tools)
```

## No Migrations Required

All new functionality uses computed properties, not stored fields.

## Commands to Verify Work

```bash
# Run all related tests
.venv/bin/pytest apps/metrics/tests/test_ai_categories.py -v
.venv/bin/pytest apps/metrics/tests/test_ai_model_fields.py -v
.venv/bin/pytest apps/metrics/tests/test_pr_list_service.py -v
.venv/bin/pytest apps/metrics/tests/dashboard/test_ai_metrics.py -v

# Format check
make ruff

# No new migrations needed
make migrations  # Should show "No changes detected"
```

## Next Steps

**All implementation complete!** Only manual QA remaining:

1. Start the dev server: `make dev`
2. Navigate to PR list page
3. Verify:
   - AI Category dropdown filter works
   - Category stats badges show in summary row
   - AI column shows Code/Review/Both badges
   - Tooltip shows tool names on hover
   - Expanded row shows "Category: Code AI" or similar
   - Dashboard tool breakdown chart groups by category

4. If all works, move to `dev/completed/`

## Tool Category Mappings

### CODE_TOOLS (Write/Generate Code)

```python
CODE_TOOLS = {
    # Market leaders
    "cursor", "copilot", "github copilot",
    "claude", "claude_code", "claude-code",
    # AI Agents
    "devin",
    # Chat-based
    "chatgpt", "gpt4", "gpt-4", "gpt-5", "gpt5",
    "gemini", "gemini-code-assist",
    # IDEs
    "windsurf", "codeium", "jetbrains_ai", "jetbrains ai",
    # Terminal/CLI
    "aider", "continue",
    # Code completion
    "cody", "tabnine", "supermaven", "amazon_q", "amazon q",
    "codewhisperer", "codex",
    # Open source
    "goose", "openhands",
    # Generic
    "ai_generic", "ai assistant", "codegen",
}
```

### REVIEW_TOOLS (Analyze/Comment Only)

```python
REVIEW_TOOLS = {
    "coderabbit", "code rabbit",
    "cubic", "greptile", "sourcery",
    "codacy", "sonarqube", "deepcode",
    "kodus", "graphite", "codeant",
}
```

### MIXED_TOOLS (Both) → Default to CODE

```python
MIXED_TOOLS = {
    "ellipsis", "bito", "qodo", "codium", "augment",
}
```

### EXCLUDED_TOOLS (Not AI Coding)

```python
EXCLUDED_TOOLS = {
    "snyk", "mintlify", "lingohub",
    "dependabot", "renovate",
    "unknown", "ai",
}
```

## UI Changes Made

### PR List Page (`pull_requests.html`)

1. Added `ai_category` to Alpine.js state tracking
2. Added AI Category dropdown filter after AI Tool filter
3. Updated stats row to show category breakdown badges:
   ```html
   <span class="badge badge-primary badge-xs">{{ stats.code_ai_count }} Code</span>
   <span class="badge badge-secondary badge-xs">{{ stats.review_ai_count }} Review</span>
   ```

### AI Tool Breakdown Chart

Updated to group tools by category:
```html
{% regroup chart_data by category as category_list %}
{% for category in category_list %}
  <span class="badge badge-{{ category.grouper == 'code' ? 'primary' : 'secondary' }}">
    {{ category.grouper|title }} AI
  </span>
  {% for item in category.list %}...{% endfor %}
{% endfor %}
```
