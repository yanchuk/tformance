# Repository Name Display - Context

**Last Updated: 2025-12-24**

## Key Files

### Files to Modify

| File | Purpose |
|------|---------|
| `apps/metrics/templatetags/pr_list_tags.py` | Add `repo_name` filter |
| `templates/metrics/pull_requests/partials/table.html` | Apply filter to table column |
| `templates/metrics/pull_requests/list.html` | Apply filter to dropdown display |

### Test Files

| File | Purpose |
|------|---------|
| `apps/metrics/tests/test_pr_list_tags.py` | Unit tests for template filters |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `apps/metrics/models/github.py` | PullRequest model with `github_repo` field |
| `apps/metrics/services/pr_list_service.py` | `get_filter_options()` returns repos list |

## Current Data Format

The `github_repo` field stores the full repository path:
- Format: `owner/repo`
- Example: `antiwork/gumroad`, `facebook/react`, `vercel/next.js`

## Template Filter Pattern

Existing filters in `pr_list_tags.py`:
```python
@register.filter
def ai_tools_display(value):
    """Convert AI tools list to display string."""
    ...

@register.filter
def tech_abbrev(category):
    """Get abbreviation for technology category."""
    ...
```

## Key Decisions

1. **Keep full name in database** - Required for GitHub API URLs
2. **Display short name only** - Less redundant, cleaner UI
3. **Filter uses full name internally** - `value="{{ repo }}"` unchanged
4. **Simple split logic** - `split("/")[-1]` handles all cases

## Test Cases

1. `"antiwork/gumroad"` -> `"gumroad"`
2. `"facebook/react"` -> `"react"`
3. `"org/sub-repo-name"` -> `"sub-repo-name"`
4. `""` -> `""`
5. `None` -> `""`
6. `"no-slash-repo"` -> `"no-slash-repo"` (edge case)
