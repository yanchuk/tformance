# PR Filter UI Fix - Context

**Last Updated: 2025-12-24**

## Current State

### What's Done
- Added 4 missing filter dropdowns to PR list page (Reviewer, AI Tool, PR Size, Jira Link)
- Backend already supported all 10 filters, this was UI-only
- Added `days` URL parameter handling in view to convert to date_from/date_to
- Adjusted table column widths (Title 30%, State 6%)
- Commits: `d982830`, `90e68c3`

### What's Broken
**BUG: Time range button (7d/30d/90d) highlighting doesn't update on HTMX click**
- User clicks "7d" button, URL changes to `?days=7`, but "30d" stays highlighted
- Only fixes on manual browser refresh
- Root cause: HTMX `hx-target="#page-content"` only replaces inner content, not the time range buttons which are in `base_analytics.html`

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/views/pr_list_views.py` | View with `_get_filters_from_request()` and `pr_list()` |
| `templates/metrics/analytics/pull_requests.html` | PR list page template with filters |
| `templates/metrics/analytics/base_analytics.html` | **Base template with time range buttons - NEEDS FIX** |
| `templates/metrics/pull_requests/partials/table.html` | PR table partial |
| `apps/metrics/services/pr_list_service.py` | Backend filter logic |

## Bug Fix Approach

### Option 1: JavaScript URL Watcher (Recommended)
Add JS in `base_analytics.html` to watch for URL changes and update button classes:
```javascript
function updateTimeRangeButtons() {
  const params = new URLSearchParams(window.location.search);
  const days = parseInt(params.get('days')) || 30;
  document.querySelectorAll('.join a[href^="?days="]').forEach(btn => {
    const btnDays = parseInt(btn.href.split('days=')[1]);
    if (btnDays === days) {
      btn.classList.add('btn-primary');
      btn.classList.remove('btn-ghost');
    } else {
      btn.classList.remove('btn-primary');
      btn.classList.add('btn-ghost');
    }
  });
}
// Listen for HTMX URL changes
document.body.addEventListener('htmx:pushedIntoHistory', updateTimeRangeButtons);
document.body.addEventListener('htmx:replacedInHistory', updateTimeRangeButtons);
```

### Option 2: Larger HTMX Target
Change `hx-target` to include the time range buttons, but this requires template restructuring.

## Filter Options Available

```python
filter_options = {
    "repos": [...],           # List of repo names
    "authors": [{"id": "", "name": ""}],
    "reviewers": [{"id": "", "name": ""}],
    "ai_tools": [...],        # List of detected AI tools
    "size_buckets": PR_SIZE_BUCKETS,  # XS/S/M/L/XL
    "states": ["open", "merged", "closed"],
}
```

## PR Size Buckets

```python
PR_SIZE_BUCKETS = {
    "XS": (0, 10),      # 0-10 lines
    "S": (11, 50),      # 11-50 lines
    "M": (51, 200),     # 51-200 lines
    "L": (201, 500),    # 201-500 lines
    "XL": (501, None),  # 501+ lines
}
```

## Tests Needed

### Unit Tests (`apps/metrics/tests/test_pr_list_views.py`)
```python
def test_get_filters_from_request_with_days_param():
    """Test days parameter converts to date_from/date_to."""

def test_pr_list_sets_days_context_from_url():
    """Test days context variable set from URL param."""

def test_pr_list_renders_all_filter_dropdowns():
    """Test all 4 new dropdowns render with options."""
```

### E2E Tests (`tests/e2e/pr_filters.spec.ts`)
```typescript
test('time range buttons highlight correctly on click', async ({ page }) => {
  await page.goto('/app/metrics/pull-requests/');
  await page.click('a[href="?days=7"]');
  await expect(page.locator('a[href="?days=7"]')).toHaveClass(/btn-primary/);
  await expect(page.locator('a[href="?days=30"]')).not.toHaveClass(/btn-primary/);
});

test('all filter dropdowns are visible', async ({ page }) => {
  await page.goto('/app/metrics/pull-requests/');
  await expect(page.locator('select[name="reviewer"]')).toBeVisible();
  await expect(page.locator('select[name="size"]')).toBeVisible();
  await expect(page.locator('select[name="has_jira"]')).toBeVisible();
});
```

## Next Steps (Priority Order)

1. **Fix the time range button highlighting bug** (JavaScript in base_analytics.html)
2. **Add unit tests** for days parameter and filter rendering
3. **Add E2E tests** for button highlighting and filter functionality
4. Run full test suite to verify no regressions

## Commands to Run

```bash
# Run PR list tests
make test ARGS='apps/metrics/tests/test_pr_list_views.py -v'

# Run E2E tests
make e2e

# Check for lint issues
make ruff
```

## Uncommitted Changes

None - all changes committed. Task moved back to active for bug fix.
