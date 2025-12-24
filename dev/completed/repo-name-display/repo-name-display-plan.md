# Repository Name Display - Implementation Plan

**Last Updated: 2025-12-24**

## Executive Summary

Display repository names without the organization prefix throughout the application. Instead of showing "antiwork/gumroad", display just "gumroad". The organization prefix is redundant since all repositories within a team typically belong to the same organization.

## Current State Analysis

### Data Storage

**Model**: `apps/metrics/models/github.py` - `PullRequest.github_repo`
- Stores full repository name: `owner/repo` format (e.g., "antiwork/gumroad")
- Used for GitHub API calls and URL construction
- Should NOT be changed - keep full name in database

### Display Locations

1. **PR List Table** (`templates/metrics/pull_requests/partials/table.html:68`)
   - `{{ pr.github_repo }}` - shows full name

2. **PR List Filter Dropdown** (`templates/metrics/pull_requests/list.html:30-31`)
   - `{{ repo }}` - shows full name in dropdown options

3. **Filter Options Service** (`apps/metrics/services/pr_list_service.py:222`)
   - Returns full `github_repo` values for filter dropdown

## Proposed Future State

### Display Logic

Create a template filter to extract repo name from full path:
- Input: `antiwork/gumroad`
- Output: `gumroad`

Apply the filter in both display locations:
1. PR table Repository column
2. Repository filter dropdown options

### Filter Behavior

The filter parameter should continue to use full names internally for database queries, but display short names to users.

## Implementation Phases

### Phase 1: Create Template Filter [S]

**Effort**: Small (10 min)

Create a simple template filter to extract repo name:

```python
@register.filter
def repo_name(full_repo):
    """Extract repository name from 'owner/repo' format."""
    if not full_repo:
        return ""
    return full_repo.split("/")[-1] if "/" in full_repo else full_repo
```

### Phase 2: Update Templates [S]

**Effort**: Small (10 min)

Apply the filter to both locations:
1. `table.html:68` - `{{ pr.github_repo|repo_name }}`
2. `list.html:31` - `{{ repo|repo_name }}`

Note: Keep `value="{{ repo }}"` unchanged so filtering works correctly.

### Phase 3: Testing [S]

**Effort**: Small (10 min)

1. Unit tests for the template filter
2. Manual verification on PR List page

## Technical Details

### Template Filter Location

Add to existing `apps/metrics/templatetags/pr_list_tags.py`:

```python
@register.filter
def repo_name(full_repo):
    """Extract repository name from 'owner/repo' format.

    Example: 'antiwork/gumroad' -> 'gumroad'
    """
    if not full_repo:
        return ""
    return full_repo.split("/")[-1] if "/" in full_repo else full_repo
```

### Template Changes

**PR Table** (`templates/metrics/pull_requests/partials/table.html`):
```html
<!-- Before -->
<td class="text-sm text-base-content/70">{{ pr.github_repo }}</td>

<!-- After -->
<td class="text-sm text-base-content/70">{{ pr.github_repo|repo_name }}</td>
```

**Filter Dropdown** (`templates/metrics/pull_requests/list.html`):
```html
<!-- Before -->
<option value="{{ repo }}" ...>{{ repo }}</option>

<!-- After - keep value, change display -->
<option value="{{ repo }}" ...>{{ repo|repo_name }}</option>
```

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Filter breaks with malformed data | Low | Low | Handle edge cases in filter |
| Users confused by shorter name | Very Low | Low | Tooltip with full name optional |
| Database changes break filter | N/A | N/A | No DB changes needed |

## Success Metrics

- [ ] PR table shows "gumroad" instead of "antiwork/gumroad"
- [ ] Filter dropdown shows short names
- [ ] Filtering still works correctly (uses full name internally)
- [ ] No regressions in PR list functionality

## Dependencies

- None - purely display change using existing infrastructure

## Effort Estimate

**Total**: ~30 minutes
- Template filter: 10 min
- Template updates: 10 min
- Testing: 10 min
