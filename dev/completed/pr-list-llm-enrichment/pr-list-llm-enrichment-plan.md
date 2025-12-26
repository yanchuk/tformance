# PR List LLM Data Enrichment - Implementation Plan

**Last Updated: 2025-12-26**

## Executive Summary

Enhance the PR list page (`/app/metrics/pull-requests/`) with expandable rows showing LLM-generated insights. When clicking a PR row, it expands to reveal the full LLM analysis including summary, health assessment, and detailed AI/tech breakdowns. Additionally, add new badges and filters based on available LLM data.

## Current State Analysis

### What's Displayed Now (11 Columns)
| Column | Source |
|--------|--------|
| Title | `pr.title` + Jira badge |
| Repository | `pr.github_repo` |
| Author | `pr.author.display_name` + Self/Bot badges |
| State | merged/open |
| Cycle Time | `pr.cycle_time_hours` |
| Review Time | `pr.review_time_hours` |
| Size | XS/S/M/L/XL bucket |
| Comments | `pr.total_comments` |
| AI | Confidence level badge + signals tooltip |
| Tech | Category badges (max 3) |
| Merged | Date |

### Available LLM Data NOT Currently Displayed

```json
{
  "summary": {
    "title": "Brief CTO-friendly title",
    "description": "1-2 sentence business impact summary",
    "type": "feature|bugfix|refactor|docs|test|chore|ci"
  },
  "health": {
    "review_friction": "low|medium|high",
    "scope": "small|medium|large|xlarge",
    "risk_level": "low|medium|high",
    "insights": ["Observation about PR process..."]
  },
  "ai": {
    "usage_type": "authored|assisted|reviewed|brainstorm|null"
  },
  "tech": {
    "languages": ["python", "typescript"],
    "frameworks": ["django", "react"]
  }
}
```

## Proposed Future State

### 1. Expandable PR Rows
- Click on PR title → row expands below
- Shows LLM summary, health assessment, and detailed breakdowns
- Collapsible with another click
- Uses Alpine.js for client-side toggle (no server round-trip)

### 2. New Table Badges
| Badge | Location | Value |
|-------|----------|-------|
| PR Type | After title | `feature` `bugfix` `refactor` etc. |
| Risk Level | Near Size | `low` `medium` `high` |
| Review Friction | Near Review Time | `low` `medium` `high` |

### 3. New Filters
- **PR Type** - feature/bugfix/refactor/docs/test/chore/ci
- **Risk Level** - low/medium/high
- **Review Friction** - low/medium/high

### 4. Expanded Row Content
```
┌─────────────────────────────────────────────────────────────────┐
│ 📋 Summary                                                       │
│ [LLM Title]: [LLM Description]                                  │
├─────────────────────────────────────────────────────────────────┤
│ 🏥 Health Assessment                                             │
│ Scope: [badge]  Risk: [badge]  Friction: [badge]                │
│ Insights: • [insight 1]                                          │
│           • [insight 2]                                          │
├─────────────────────────────────────────────────────────────────┤
│ 🤖 AI Details                          │ 💻 Tech Stack           │
│ Usage: [authored/assisted/etc]         │ Languages: Py, TS       │
│ Tools: Claude, Cursor                  │ Frameworks: Django, Vue │
│ Confidence: 0.85                       │                         │
└─────────────────────────────────────────────────────────────────┘
```

## Implementation Phases

### Phase 1: Expandable Rows with Alpine.js (S)
- Add click handler to PR title
- Create hidden expandable row below each PR
- Toggle visibility with Alpine `x-show`
- Style the expanded content area

### Phase 2: Expanded Row Template (M)
- Create partial template for expanded content
- Display LLM summary (title, description)
- Display health assessment (scope, risk, friction, insights)
- Display AI details (usage type, tools, confidence)
- Display tech stack (languages, frameworks)
- Handle cases where `llm_summary` is null

### Phase 3: New Badges in Table (S)
- Add PR Type badge next to title
- Add Risk Level indicator
- Create template filters for badge styling
- Handle null/missing LLM data gracefully

### Phase 4: New Filters (M)
- Add PR Type filter dropdown
- Add Risk Level filter dropdown
- Add Review Friction filter dropdown
- Update service layer to filter by LLM JSON fields
- Update HTMX partial to include new filters

### Phase 5: UI Polish (S)
- Animation for row expansion
- Consistent badge styling
- Mobile responsiveness
- Loading states if needed

## Technical Approach

### Alpine.js Row Expansion
```html
<tr x-data="{ expanded: false }" @click="expanded = !expanded">
  <!-- Normal row columns -->
</tr>
<tr x-show="expanded" x-collapse>
  <td colspan="11">
    {% include 'metrics/pull_requests/partials/expanded_row.html' %}
  </td>
</tr>
```

### JSON Field Filtering (PostgreSQL)
```python
# Filter by LLM summary.type
if pr_type := filters.get('pr_type'):
    qs = qs.filter(llm_summary__summary__type=pr_type)

# Filter by LLM health.risk_level
if risk := filters.get('risk_level'):
    qs = qs.filter(llm_summary__health__risk_level=risk)
```

### Template Filters for LLM Data
```python
@register.filter
def llm_pr_type(pr):
    """Get PR type from LLM summary with fallback."""
    if pr.llm_summary and 'summary' in pr.llm_summary:
        return pr.llm_summary['summary'].get('type')
    return None

@register.filter
def llm_risk_badge_class(risk_level):
    """Return DaisyUI badge class for risk level."""
    return {
        'low': 'badge-success',
        'medium': 'badge-warning',
        'high': 'badge-error'
    }.get(risk_level, 'badge-ghost')
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM data missing for many PRs | Medium | Show graceful fallback UI, run backfill |
| Performance with many expanded rows | Low | Alpine collapse handles DOM efficiently |
| JSON filter performance | Low | PostgreSQL JSONB has efficient indexing |
| Mobile layout | Medium | Test and add responsive breakpoints |

## Success Metrics

1. **Functional**: All LLM data visible when row expanded
2. **Coverage**: Display fallback for PRs without LLM data
3. **Performance**: No noticeable lag on expansion
4. **Filters**: All three new filters work correctly
5. **Tests**: Unit tests for new template filters and service methods

## Dependencies

- Existing LLM processing pipeline (already in place)
- Alpine.js collapse plugin (may need to add)
- DaisyUI badge components (already using)

## Files to Modify/Create

### Modify
- `templates/metrics/pull_requests/partials/table.html` - Add expandable rows
- `apps/metrics/services/pr_list_service.py` - Add new filters
- `apps/metrics/views/pr_list_views.py` - Pass new filter options
- `apps/metrics/templatetags/pr_list_tags.py` - Add LLM display filters

### Create
- `templates/metrics/pull_requests/partials/expanded_row.html` - Expanded content

### Tests
- `apps/metrics/tests/test_pr_list_tags.py` - Test new template filters
- `apps/metrics/tests/test_pr_list_service.py` - Test new filter options
