# AI Bot Author Detection - Context

**Last Updated: 2025-12-24**
**Status: COMPLETE**

## Summary

Implemented detection of PRs authored by AI bots (Devin, Dependabot, Renovate, etc.) during GitHub sync. PRs by bot authors are now marked as `is_ai_assisted=True` with the bot type in `ai_tools_detected`.

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | AI tool patterns - `AI_REVIEWER_BOTS`, `AI_TOOL_DISPLAY_NAMES` |
| `apps/metrics/services/ai_detector.py` | Detection functions - `detect_ai_author()`, `detect_ai_reviewer()`, `detect_ai_in_text()` |
| `apps/integrations/services/github_graphql_sync.py` | PR sync - `_process_pr()` applies AI detection |
| `apps/metrics/templatetags/pr_list_tags.py` | `ai_tools_display` filter for friendly names |
| `templates/metrics/pull_requests/partials/table.html` | PR list table with bot badge |

## Implementation Details

### 1. AI Author Detection (`ai_detector.py`)

```python
def detect_ai_author(username: str | None) -> AIReviewerResult:
    """Detect if a PR author username is an AI bot."""
    return _detect_ai_bot_username(username)

# Uses shared internal function with detect_ai_reviewer()
def _detect_ai_bot_username(username: str | None) -> AIReviewerResult:
    if not username:
        return {"is_ai": False, "ai_type": ""}
    username_lower = username.lower()
    if username_lower in AI_REVIEWER_BOTS:
        return {"is_ai": True, "ai_type": AI_REVIEWER_BOTS[username_lower]}
    return {"is_ai": False, "ai_type": ""}
```

### 2. GraphQL Sync Integration

In both `_process_pr()` and `_process_pr_incremental()`:

```python
# Detect AI involvement from author and text
author_ai_result = detect_ai_author(author_login)
text_ai_result = detect_ai_in_text(f"{title}\n{body}")

# Combine AI detection results
ai_tools = list(text_ai_result["ai_tools"])
if author_ai_result["is_ai"] and author_ai_result["ai_type"] not in ai_tools:
    ai_tools.append(author_ai_result["ai_type"])
is_ai_assisted = author_ai_result["is_ai"] or text_ai_result["is_ai_assisted"]

pr_defaults = {
    # ... other fields ...
    "is_ai_assisted": is_ai_assisted,
    "ai_tools_detected": ai_tools,
}
```

### 3. UI Display

Template filter for friendly names:
```python
@register.filter
def ai_tools_display(ai_tools_detected: list[str]) -> str:
    return ", ".join(get_ai_tool_display_name(tool) for tool in ai_tools_detected)
```

Template logic for bot authors without TeamMember:
```html
{% elif pr.is_ai_assisted and pr.ai_tools_detected %}
    <span class="text-primary">{{ pr.ai_tools_detected|ai_tools_display }}</span>
    <span class="badge badge-secondary badge-xs ml-1">Bot</span>
{% endif %}
```

## Known AI Bot Usernames (from ai_patterns.py)

```python
AI_REVIEWER_BOTS = {
    "devin-ai-integration[bot]": "devin",
    "devin[bot]": "devin",
    "devin-ai[bot]": "devin",
    "dependabot[bot]": "dependabot",
    "renovate[bot]": "renovate",
    "github-actions[bot]": "github_actions",
    "coderabbitai": "coderabbit",
    # ... more in file
}
```

## Friendly Display Names

```python
AI_TOOL_DISPLAY_NAMES = {
    "devin": "Devin AI",
    "dependabot": "Dependabot",
    "renovate": "Renovate",
    "copilot": "Copilot",
    "claude_code": "Claude Code",
    # ... more in file
}
```

## Test Coverage

- 10 tests for `detect_ai_author()` function
- 8 tests for AI detection in GraphQL sync
- All 48 AI detector tests passing
- All 56 GraphQL sync tests passing
- All 34 PR list view tests passing
