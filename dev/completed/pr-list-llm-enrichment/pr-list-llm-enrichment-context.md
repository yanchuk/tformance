# PR List LLM Enrichment - Context & Key Information

**Last Updated: 2025-12-26**

## Key Files

### Models
- `apps/metrics/models/github.py` - PullRequest model with `llm_summary` JSONField

### Views & Services
- `apps/metrics/views/pr_list_views.py` - Main view functions
- `apps/metrics/services/pr_list_service.py` - Filtering and stats logic

### Templates
- `templates/metrics/analytics/pull_requests.html` - Main page (analytics tab version)
- `templates/metrics/pull_requests/list.html` - Standalone PR list page
- `templates/metrics/pull_requests/partials/table.html` - Table partial (shared)

### Template Tags
- `apps/metrics/templatetags/pr_list_tags.py` - Display formatting filters

### LLM Schema
- `apps/metrics/services/llm_prompts.py` - Prompt version and user prompt builder
- `apps/metrics/prompts/templates/` - Jinja2 templates for prompts

## LLM Summary JSON Schema (v7.0.0)

```json
{
  "ai": {
    "is_assisted": boolean,
    "tools": ["string"],
    "usage_type": "authored|assisted|reviewed|brainstorm|null",
    "confidence": 0.0-1.0
  },
  "tech": {
    "languages": ["python", "typescript", ...],
    "frameworks": ["django", "react", ...],
    "categories": ["backend", "frontend", "devops", "mobile", "data"]
  },
  "summary": {
    "title": "string (5-10 words)",
    "description": "string (1-2 sentences)",
    "type": "feature|bugfix|refactor|docs|test|chore|ci"
  },
  "health": {
    "review_friction": "low|medium|high",
    "scope": "small|medium|large|xlarge",
    "risk_level": "low|medium|high",
    "insights": ["string"]
  }
}
```

## Current Filter Options

From `get_filter_options()`:
- `repos` - List of repositories
- `authors` - Team members
- `reviewers` - Team members
- `ai_tools` - Detected AI tools
- `tech_categories` - backend, frontend, devops, mobile, data

## Existing Template Filters

| Filter | Purpose |
|--------|---------|
| `ai_confidence_level` | Maps score to high/medium/low |
| `ai_signals_tooltip` | Formats signal breakdown |
| `tech_abbrev` | FE, BE, DC, MB, DT abbreviations |
| `tech_badge_class` | DaisyUI badge color class |
| `tech_display_name` | Full category name |
| `pr_size_bucket` | XS/S/M/L/XL from line count |
| `ai_tools_display` | Friendly AI tool names |
| `repo_name` | Extract repo from "org/repo" |

## Design Patterns

### LLM Data Priority
Always use `effective_*` model properties that check LLM data first:
- `pr.effective_is_ai_assisted`
- `pr.effective_ai_tools`
- `pr.effective_tech_categories`
- `pr.effective_pr_type`

### JSON Filtering in Django
```python
# PostgreSQL JSONB field filtering
PullRequest.objects.filter(llm_summary__health__risk_level='high')
```

### Alpine.js in Templates
```html
<div x-data="{ open: false }">
  <button @click="open = !open">Toggle</button>
  <div x-show="open" x-collapse>Content</div>
</div>
```

## Key Decisions

1. **Client-side expansion**: Use Alpine.js, no HTMX/server calls for expand/collapse
2. **Graceful fallback**: Show "LLM analysis pending" for PRs without `llm_summary`
3. **Badge colors**: Use DaisyUI semantic colors (success/warning/error)
4. **Filter by JSON**: Use PostgreSQL JSONB operators for efficient filtering

## Dependencies

- Alpine.js (already loaded globally)
- DaisyUI (already using)
- No new npm packages needed

## Database Considerations

- `llm_summary` is a PostgreSQL JSONB field
- Already has GIN index for efficient querying
- ~15,000+ PRs have LLM summaries populated
