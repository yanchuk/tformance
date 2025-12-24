# PR Filter UI Fix - Implementation Plan

**Last Updated: 2025-12-24**

## Executive Summary

The Pull Requests data explorer page backend supports 10 filter parameters, but only 6 are displayed in the UI. Additionally, when navigating from the analytics overview with a date range selected, those dates should pre-populate the PR page's date inputs.

## Current State Analysis

### Backend Filter Support (pr_list_service.py)
| Filter | Backend Support | UI Display | Status |
|--------|----------------|------------|--------|
| `repo` | ✅ | ✅ | OK |
| `author` | ✅ | ✅ | OK |
| `reviewer` | ✅ | ❌ | **MISSING** |
| `ai` | ✅ | ✅ | OK |
| `ai_tool` | ✅ | ❌ | **MISSING** |
| `size` | ✅ | ❌ | **MISSING** |
| `state` | ✅ | ✅ | OK |
| `has_jira` | ✅ | ❌ | **MISSING** |
| `date_from` | ✅ | ✅ | OK |
| `date_to` | ✅ | ✅ | OK |

### Size Buckets (already defined)
```python
PR_SIZE_BUCKETS = {
    "XS": (0, 10),      # 0-10 lines
    "S": (11, 50),      # 11-50 lines
    "M": (51, 200),     # 51-200 lines
    "L": (201, 500),    # 201-500 lines
    "XL": (501, None),  # 501+ lines
}
```

### Date Range Inheritance Issue
When user selects "30 Days" on analytics tabs and clicks to PR page, the date filter should carry over and display in the date inputs.

## Proposed Solution

Add 4 missing filter dropdowns to the PR list UI:
1. **Size** - Dropdown with XS, S, M, L, XL options
2. **Reviewer** - Dropdown populated from `filter_options.reviewers`
3. **AI Tool** - Dropdown populated from `filter_options.ai_tools`
4. **Has Jira** - Dropdown with Yes/No options

Also ensure date range from analytics tabs pre-populates the date inputs.

## Implementation Tasks

### Phase 1: Add Missing Filter UI Elements (S effort)

**File:** `templates/metrics/analytics/pull_requests.html`

1. Add Size filter dropdown after State filter
2. Add Reviewer filter dropdown after Author filter
3. Add AI Tool filter dropdown after AI Assisted filter (conditionally shown)
4. Add Has Jira filter dropdown

### Phase 2: Date Range Inheritance (S effort)

1. Ensure `date_from` and `date_to` from analytics tabs are passed to PR page
2. Verify date inputs display selected values correctly

## Success Metrics

- All 10 filters visible and functional in UI
- Filters work correctly with Apply/Clear buttons
- URL params preserved on filter submit
- Date range inherited from analytics overview
- E2E tests pass

## Risks

- Low risk: Simple template changes
- Test existing E2E tests for PR page after changes
