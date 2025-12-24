# PR List Size Column & Author Ellipsis - Context

**Last Updated:** 2025-12-24

## Key Files

### Template
- `templates/metrics/pull_requests/partials/table.html` - PR list table partial (lines 106-109 for Lines column, lines 69-81 for Author column)

### Template Tags
- `apps/metrics/templatetags/pr_list_tags.py` - Custom filters for PR list display

### Service
- `apps/metrics/services/pr_list_service.py` - Contains `PR_SIZE_BUCKETS` constant (lines 13-19)

### Tests
- `apps/metrics/tests/test_pr_list_service.py` - Service tests
- `apps/metrics/tests/test_pr_list_views.py` - View tests
- `apps/metrics/tests/test_pr_list_tags.py` - Template tag tests (26 existing tests)

## Key Decisions

1. **Reuse existing PR_SIZE_BUCKETS** - Same buckets used for filtering
2. **Keep "lines" sort key** - Sorting still works on total lines, just display changes
3. **Use native tooltips** - Simple `title` attribute vs complex tooltip component
4. **Badge colors match PR size chart** - Visual consistency across app

## Size Bucket Reference

```python
PR_SIZE_BUCKETS = {
    "XS": (0, 10),      # Extra small: 0-10 lines
    "S": (11, 50),      # Small: 11-50 lines
    "M": (51, 200),     # Medium: 51-200 lines
    "L": (201, 500),    # Large: 201-500 lines
    "XL": (501, None),  # Extra large: 501+ lines
}
```

## Badge Color Scheme

| Bucket | Badge Class | Color |
|--------|-------------|-------|
| XS | badge-success | Green |
| S | badge-info | Blue |
| M | badge-warning | Yellow |
| L | badge-error | Red |
| XL | badge-error | Red |

## Test Commands

```bash
# Run template tag tests
make test ARGS='apps.metrics.tests.test_pr_list_tags'

# Run all PR list tests
make test ARGS='apps.metrics.tests.test_pr_list_service apps.metrics.tests.test_pr_list_views apps.metrics.tests.test_pr_list_tags'
```

## Dependencies

- DaisyUI badge component
- Tailwind `truncate` utility class
