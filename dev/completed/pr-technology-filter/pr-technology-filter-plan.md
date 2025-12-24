# PR Technology Filter - Plan

**Last Updated: 2025-12-24**

## Executive Summary

Add a "Tech" column and filter to the PR list page to show which technology areas each PR touches (frontend, backend, config, etc.). Display as compact colored badges to minimize horizontal space while providing quick visual insight.

## Current State Analysis

### Existing Infrastructure

1. **PRFile model** already tracks `file_category` per file:
   - Categories: `frontend`, `backend`, `javascript`, `test`, `docs`, `config`, `other`
   - Automatically categorized during sync based on file extensions
   - Dashboard already uses this for file category breakdown charts

2. **PR List Page** (`templates/metrics/pull_requests/list.html`):
   - 6 existing filters: Repository, Author, AI Assisted, State, Date From, Date To
   - Table columns: Title, Repository, Author, State, Cycle Time, Review Time, Lines, Comments, AI, Merged
   - HTMX-powered with partial updates

3. **PR List Service** (`apps/metrics/services/pr_list_service.py`):
   - `get_prs_queryset()` - filtering
   - `get_filter_options()` - available filter values
   - `get_pr_stats()` - aggregate statistics

## Proposed Future State

### Display Format: Compact Badges

Show 2-letter abbreviations as small badges:

| Category | Badge | Color |
|----------|-------|-------|
| Frontend | `FE` | `badge-info` (blue) |
| Backend | `BE` | `badge-success` (green) |
| JS/TypeScript | `JS` | `badge-warning` (amber) |
| Test | `TS` | `badge-secondary` (gray) |
| Docs | `DC` | `badge-ghost` |
| Config | `CF` | `badge-accent` |
| Other | `OT` | `badge-ghost` |

**Layout**: Stack badges vertically in a narrow column or show as a single tooltip on hover.

### Filter Behavior

Multi-select checkbox filter - show PRs that touch ANY of the selected categories.

## Implementation Phases

### Phase 1: Data Annotation (S effort)
Add queryset annotation to aggregate file categories per PR.

### Phase 2: Filter Implementation (S effort)
Add technology filter to PR list service and view.

### Phase 3: Template Display (S effort)
Add Tech column with badge display.

### Phase 4: Testing (S effort)
Add unit tests for filter and display logic.

## Technical Design

### 1. Queryset Annotation

```python
# In pr_list_service.py
from django.db.models import ArrayAgg

qs = qs.annotate(
    tech_categories=ArrayAgg(
        'files__file_category',
        distinct=True,
        default=Value([])
    )
)
```

### 2. Filter Logic

```python
# Filter by technology category (multi-select)
tech = filters.get("tech")
if tech:
    tech_list = tech if isinstance(tech, list) else [tech]
    qs = qs.filter(files__file_category__in=tech_list).distinct()
```

### 3. Template Display

```html
<td class="text-center">
  {% for cat in pr.tech_categories %}
    <span class="badge badge-xs {{ cat|tech_badge_class }}" title="{{ cat|tech_display_name }}">
      {{ cat|tech_abbrev }}
    </span>
  {% endfor %}
</td>
```

### 4. Template Tags

```python
@register.filter
def tech_abbrev(category: str) -> str:
    """Convert category to 2-letter abbreviation."""
    ABBREVS = {
        "frontend": "FE",
        "backend": "BE",
        "javascript": "JS",
        "test": "TS",
        "docs": "DC",
        "config": "CF",
        "other": "OT",
    }
    return ABBREVS.get(category, category[:2].upper())

@register.filter
def tech_badge_class(category: str) -> str:
    """Get DaisyUI badge class for category."""
    CLASSES = {
        "frontend": "badge-info",
        "backend": "badge-success",
        "javascript": "badge-warning",
        "test": "badge-secondary",
        "docs": "badge-ghost",
        "config": "badge-accent",
        "other": "badge-ghost",
    }
    return CLASSES.get(category, "badge-ghost")
```

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Query performance with annotation | Use `Prefetch` for files or cache categories |
| Column width on mobile | Use stacked vertical badges or tooltip |
| Too many badges clutter | Limit to top 3, show "+N" for more |

## Success Metrics

1. Tech column visible on PR list page
2. Filter by technology working
3. All tests passing
4. No significant performance degradation

## Dependencies

- PRFile model with file_category (already exists)
- DaisyUI badge components (already available)
