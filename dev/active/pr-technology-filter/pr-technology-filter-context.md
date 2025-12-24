# PR Technology Filter - Context

**Last Updated: 2025-12-24**

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/models/github.py` | PRFile model with `file_category` field |
| `apps/metrics/services/pr_list_service.py` | PR list filtering logic |
| `apps/metrics/views/pr_list_views.py` | PR list view handlers |
| `apps/metrics/templatetags/pr_list_tags.py` | Template filters for PR display |
| `templates/metrics/pull_requests/list.html` | PR list page with filters |
| `templates/metrics/pull_requests/partials/table.html` | PR table template |

## File Category System

From `PRFile.CATEGORY_CHOICES`:

```python
CATEGORY_CHOICES = [
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("javascript", "JS/TypeScript"),  # Ambiguous - could be frontend or backend
    ("test", "Test"),
    ("docs", "Documentation"),
    ("config", "Configuration"),
    ("other", "Other"),
]
```

**Display Abbreviations:**
- `FE` - Frontend (blue)
- `BE` - Backend (green)
- `JS` - JavaScript/TypeScript (amber)
- `TS` - Test (gray)
- `DC` - Documentation
- `CF` - Configuration
- `OT` - Other

## Current Filter Options

From `get_filter_options()` in `pr_list_service.py`:
- repos
- authors
- reviewers
- ai_tools
- size_buckets
- states

## Database Relationships

```
PullRequest
    └── files (PRFile) [0..many]
         └── file_category
```

## Annotation Approach

To get categories per PR, use:

```python
from django.db.models import ArrayAgg
from django.contrib.postgres.aggregates import ArrayAgg as PgArrayAgg

# Get unique categories per PR
qs = qs.annotate(
    tech_categories=PgArrayAgg(
        'files__file_category',
        distinct=True,
        filter=~Q(files__file_category=''),
    )
)
```

Note: PostgreSQL's `array_agg` with `distinct` is more efficient.

## Filter Logic

Multi-select filter should use `IN` lookup with `distinct()`:

```python
if filters.get("tech"):
    tech_list = filters["tech"] if isinstance(filters["tech"], list) else [filters["tech"]]
    qs = qs.filter(files__file_category__in=tech_list).distinct()
```

## Template Integration

Column position: After "AI" column (index 8), before "Merged" (index 9).

Badge styling pattern from existing code:
```html
<span class="badge badge-primary badge-sm" title="tooltip">Text</span>
```

## Test Coverage

Existing tests in:
- `apps/metrics/tests/test_pr_list_service.py` - Service tests
- `apps/metrics/tests/test_pr_list_views.py` - View tests
- `apps/metrics/tests/models/test_pr_file.py` - PRFile model tests
- `apps/metrics/tests/dashboard/test_file_categories.py` - Category breakdown tests
