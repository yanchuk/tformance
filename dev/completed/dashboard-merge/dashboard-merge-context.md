# Dashboard Merge - Technical Context

**Last Updated:** 2024-12-30
**Current Phase:** Phase 3 (Templates) - Starting with TDD

---

## Implementation Progress

### Phase 1: Service Layer ✅ COMPLETE
All 4 service functions implemented with TDD (59 new tests):
- `get_needs_attention_prs()` - 16 tests in `test_needs_attention.py`
- `get_ai_impact_stats()` - 15 tests in `test_ai_impact.py`
- `get_team_velocity()` - 13 tests in `test_team_velocity.py`
- `detect_review_bottleneck()` - 15 tests in `test_bottleneck.py`

### Phase 2: HTMX Endpoints ✅ COMPLETE
All 4 endpoints implemented with TDD (30 new tests):
- `needs_attention_view()` - URL: `metrics:needs_attention`
- `ai_impact_view()` - URL: `metrics:ai_impact`
- `team_velocity_view()` - URL: `metrics:team_velocity`
- `review_distribution_chart()` - Modified to include bottleneck alert

### Templates Created (Phase 2)
- `templates/metrics/partials/needs_attention.html`
- `templates/metrics/partials/ai_impact.html`
- `templates/metrics/partials/team_velocity.html`

---

## Key Discoveries This Session

### 1. Date Filtering for Bottleneck Detection
The `detect_review_bottleneck()` function accepts date parameters for API consistency but doesn't use them. Reason: We look at ALL currently open PRs for pending review work - the creation date is irrelevant for detecting current workload imbalance.

### 2. BaseModel created_at Limitation
`BaseModel.created_at` has `auto_now_add=True`, which means it cannot be overridden in test factories. This caused date filtering tests to fail initially. Solution: Design functions appropriately (bottleneck uses open PRs regardless of date) or use different fields for date filtering.

### 3. Service Return Structure
`get_needs_attention_prs()` returns `items`, `total`, `per_page`, `has_next`, `has_prev` - not `prs`, `total_count`, `total_pages`. The view transforms this to template-friendly format.

### 4. Review Distribution Bug Fix
Fixed bug in `review_distribution_chart()` - was passing `repo=repo` to `get_review_distribution()` which doesn't support that parameter.

---

## Files to Modify

### Views

| File | Changes |
|------|---------|
| `apps/web/views.py` | Enhance `team_home()` to use new dashboard service methods |
| `apps/metrics/views/dashboard_views.py` | Add redirect for `team_dashboard()`, mark for deletion |
| `apps/metrics/views/chart_views.py` | Add new endpoints: `needs_attention`, `ai_impact`, `team_velocity` |

### Services

| File | Changes |
|------|---------|
| `apps/metrics/services/dashboard_service.py` | Add: `get_needs_attention_prs()`, `get_ai_impact_stats()`, `get_team_velocity()`, `detect_review_bottleneck()` |
| `apps/metrics/services/quick_stats.py` | May deprecate or merge into dashboard_service |

### Templates

| File | Action |
|------|--------|
| `templates/web/app_home.html` | **REWRITE** - New unified dashboard layout |
| `templates/metrics/team_dashboard.html` | **DELETE** after migration |
| `templates/web/components/quick_stats.html` | **DEPRECATE** - Replace with key_metrics_cards |
| `templates/web/components/recent_activity.html` | **DELETE** - Replaced by needs_attention |
| `templates/metrics/partials/key_metrics_cards.html` | **REUSE** - Move to shared location |
| `templates/metrics/partials/recent_prs_table.html` | **MODIFY** - Add issue badges |
| `templates/metrics/partials/review_distribution_chart.html` | **MODIFY** - Add bottleneck alert |

### New Templates to Create

| File | Purpose |
|------|---------|
| `templates/web/components/needs_attention.html` | Prioritized issue list |
| `templates/web/components/ai_impact.html` | AI comparison card |
| `templates/web/components/team_velocity.html` | Top contributors card |
| `templates/web/components/bottleneck_alert.html` | Reviewer bottleneck warning |
| `templates/web/components/integration_health.html` | Conditional integration alerts |

### URLs

| File | Changes |
|------|---------|
| `apps/metrics/urls.py` | Add new HTMX endpoints, add deprecation redirect |
| `apps/web/urls.py` | No changes needed |

### Tests

| File | Action |
|------|---------|
| `apps/metrics/tests/dashboard/` | Add tests for new service methods |
| `apps/metrics/tests/test_chart_views.py` | Add tests for new endpoints |
| `apps/web/tests/test_views.py` | Update team_home tests |
| `tests/e2e/dashboard.spec.ts` | Update for new layout |

---

## Key Decisions Log

| Decision | Rationale | Date |
|----------|-----------|------|
| Delete team_dashboard instead of keeping as "advanced" | Reduces maintenance, single source of truth | 2024-12-30 |
| Fixed 320px height for cards | Consistent visual rhythm, prevents layout shift | 2024-12-30 |
| Pagination over infinite scroll | Better performance, clearer mental model | 2024-12-30 |
| 30-day default time range | More signal than 7 days, aligns with sprint cycles | 2024-12-30 |
| Remove AI Detective Leaderboard | Data takes time to collect, not immediately actionable | 2024-12-30 |
| Bottleneck threshold at 3x avg | Balance between noise and actionability | 2024-12-30 |

---

## Data Dependencies

### For "Needs Attention" Section

```python
PullRequest.objects.filter(
    team=team,
    merged_at__range=(start_date, end_date)
).annotate(
    has_issue=Case(
        When(is_revert=True, then=Value(1)),
        When(is_hotfix=True, then=Value(2)),
        When(cycle_time__gt=team_avg_cycle * 2, then=Value(3)),
        When(lines_changed__gt=500, then=Value(4)),
        When(jira_issue__isnull=True, then=Value(5)),
        default=Value(0),
    )
).filter(has_issue__gt=0).order_by('has_issue', '-merged_at')
```

**Required Fields:**
- `is_revert` - Boolean (exists)
- `is_hotfix` - Boolean (exists)
- `cycle_time` - Duration (exists, computed)
- `lines_changed` - Integer (exists)
- `jira_issue` - FK to JiraIssue (exists)

### For "AI Impact" Section

```python
# Get cycle time grouped by AI assistance
PullRequest.objects.filter(
    team=team,
    merged_at__range=(start_date, end_date),
    cycle_time__isnull=False
).values('effective_is_ai_assisted').annotate(
    avg_cycle=Avg('cycle_time'),
    count=Count('id')
)
```

**Required Fields:**
- `effective_is_ai_assisted` - Property using LLM priority rule (exists)
- `cycle_time` - Duration (exists)

### For "Team Velocity" Section

```python
TeamMember.objects.filter(
    team=team
).annotate(
    pr_count=Count('authored_prs', filter=Q(
        authored_prs__merged_at__range=(start_date, end_date)
    )),
    avg_cycle=Avg('authored_prs__cycle_time', filter=Q(
        authored_prs__merged_at__range=(start_date, end_date)
    ))
).filter(pr_count__gt=0).order_by('-pr_count')[:limit]
```

**Required Fields:**
- `TeamMember.authored_prs` - Reverse relation (exists)
- `display_name`, `avatar_url` - Display fields (exist)

### For "Bottleneck Detection"

```python
# Get pending review counts per reviewer
PRReview.objects.filter(
    pull_request__team=team,
    pull_request__state='open',  # Only open PRs
    state='pending'
).values('reviewer').annotate(
    pending_count=Count('id')
)
```

**Required Fields:**
- `PRReview.reviewer` - FK to TeamMember (exists)
- `PRReview.state` - Choice field (exists)

---

## Integration Points

### HTMX Loading Pattern

Each dashboard section uses lazy loading:

```html
<div id="needs-attention-container"
     hx-get="{% url 'metrics:needs_attention' %}?days={{ days }}&page=1"
     hx-trigger="load"
     hx-swap="innerHTML">
  <div class="skeleton h-80 w-full"></div>
</div>
```

### Time Range Persistence

Use Alpine.js store for time range:

```javascript
Alpine.store('dateRange', {
  days: 30,  // Default
  setDays(d) {
    this.days = d;
    // Trigger HTMX refresh for all sections
    htmx.trigger('#page-content', 'refresh-metrics');
  }
});
```

### Pagination Pattern

```html
<!-- In partial response -->
<div class="flex justify-between items-center mt-4 pt-4 border-t border-base-300">
  <span class="text-sm text-base-content/60">
    Showing {{ start }}-{{ end }} of {{ total }}
  </span>
  <div class="join">
    {% if has_prev %}
    <button class="join-item btn btn-sm"
            hx-get="{% url 'metrics:needs_attention' %}?days={{ days }}&page={{ prev_page }}"
            hx-target="#needs-attention-container"
            hx-swap="innerHTML">
      ←
    </button>
    {% endif %}
    <button class="join-item btn btn-sm btn-active">{{ page }}</button>
    {% if has_next %}
    <button class="join-item btn btn-sm"
            hx-get="{% url 'metrics:needs_attention' %}?days={{ days }}&page={{ next_page }}"
            hx-target="#needs-attention-container"
            hx-swap="innerHTML">
      →
    </button>
    {% endif %}
  </div>
</div>
```

---

## Performance Considerations

### Caching Strategy

```python
from django.core.cache import cache

def get_needs_attention_prs(team, start_date, end_date, page=1):
    cache_key = f"needs_attention:{team.id}:{start_date}:{end_date}:{page}"
    result = cache.get(cache_key)
    if result is None:
        result = _compute_needs_attention(team, start_date, end_date, page)
        cache.set(cache_key, result, timeout=300)  # 5 min
    return result
```

### Query Optimization

- Use `select_related('author', 'jira_issue')` for PR queries
- Use `prefetch_related('reviews')` when computing review data
- Compute team averages once and pass to detection functions

---

## Migration Notes

### Redirect Strategy

```python
# apps/metrics/views/dashboard_views.py

from django.shortcuts import redirect
from django.contrib import messages

@login_and_team_required
def team_dashboard(request: HttpRequest) -> HttpResponse:
    """DEPRECATED: Redirect to unified dashboard."""
    messages.info(
        request,
        "The Team Dashboard has moved to the home page. "
        "You've been redirected automatically."
    )
    # Preserve days parameter
    days = request.GET.get('days', 30)
    return redirect(f"{reverse('web_team:home')}?days={days}")
```

### Feature Flag (Optional)

```python
# settings.py
FEATURE_FLAGS = {
    'UNIFIED_DASHBOARD': True,  # Set False to rollback
}

# views.py
if settings.FEATURE_FLAGS.get('UNIFIED_DASHBOARD'):
    # New behavior
else:
    # Old behavior
```

---

## Testing Strategy

### Unit Tests

```python
class TestNeedsAttentionService(TestCase):
    def test_reverts_prioritized_first(self):
        """Reverts should appear before other issue types."""

    def test_excludes_healthy_prs(self):
        """PRs without issues should not appear."""

    def test_pagination_works(self):
        """Should return correct page of results."""

    def test_empty_returns_empty_list(self):
        """No issues should return empty list."""
```

### E2E Tests

```typescript
test('unified dashboard shows key metrics', async ({ page }) => {
  await page.goto('/app/');
  await expect(page.locator('[data-testid="prs-merged"]')).toBeVisible();
  await expect(page.locator('[data-testid="needs-attention"]')).toBeVisible();
});

test('needs attention pagination works', async ({ page }) => {
  await page.goto('/app/');
  await page.click('[data-testid="needs-attention-next"]');
  await expect(page.locator('[data-testid="needs-attention-page"]')).toHaveText('2');
});
```

---

## Rollback Plan

If issues are discovered post-launch:

1. Set `FEATURE_FLAGS['UNIFIED_DASHBOARD'] = False`
2. Remove redirect from `team_dashboard` view
3. Revert `app_home.html` template
4. Clear cache: `cache.clear()`

No database migrations required, so rollback is purely code-based.

---

## Session Handoff Notes (2024-12-31)

### Critical Bug Fix: Review Distribution Count Mismatch

**Problem:** Dashboard showed "118 reviews" for a reviewer, but clicking through to PR list showed only 35 PRs.

**Root Causes (3 issues found):**

1. **Counting reviews vs unique PRs**: Dashboard was counting individual `PRReview` records (review submissions), but PR list counted unique `PullRequest` records. A reviewer can submit multiple reviews on the same PR (request changes → approve).

2. **Missing merged_at filter in dashboard**: Dashboard filtered by `submitted_at` on reviews but didn't filter by `merged_at` on PRs. PR list filtered by both.

3. **PR list didn't filter reviews by date**: When filtering by reviewer, PR list wasn't filtering reviews by `submitted_at` date range.

**Fixes Applied:**

1. Changed `get_review_distribution()` from `Count("id")` to `Count("pull_request", distinct=True)` to count unique PRs
2. Added `pull_request__merged_at__date__gte/lte` filters to `get_review_distribution()` to match PR list semantics
3. Added `submitted_at` date range filtering to PR list's reviewer filter
4. Updated template label from "reviews" to "PRs"
5. Updated tests to use `PRReviewFactory` and added new test for unique PR counting

**Files Modified:**
- `apps/metrics/services/dashboard_service.py` - get_review_distribution()
- `apps/metrics/services/pr_list_service.py` - reviewer filter
- `templates/metrics/partials/review_distribution_chart.html` - label change
- `apps/metrics/tests/dashboard/test_review_metrics.py` - updated tests

**Verification:** Dashboard shows 33 PRs, PR list shows 33 PRs - counts now match!

---

### Previous Session: What Was Completed
- Phase 1 (Service Layer): 4 functions, 59 tests - ALL PASSING
- Phase 2 (HTMX Endpoints): 4 endpoints, 30 tests - ALL PASSING
- Created 3 partial templates for new dashboard components

### Files Modified This Session

**Service Layer:**
- `apps/metrics/services/dashboard_service.py` - Added 4 new functions at end of file

**Tests Created:**
- `apps/metrics/tests/dashboard/test_needs_attention.py` (16 tests)
- `apps/metrics/tests/dashboard/test_ai_impact.py` (15 tests)
- `apps/metrics/tests/dashboard/test_team_velocity.py` (13 tests)
- `apps/metrics/tests/dashboard/test_bottleneck.py` (15 tests)
- `apps/metrics/tests/views/test_dashboard_views.py` (30 tests)
- `apps/metrics/tests/views/__init__.py` (created)

**Views:**
- `apps/metrics/views/chart_views.py` - Added 3 views, modified 1
- `apps/metrics/views/__init__.py` - Added exports

**URLs:**
- `apps/metrics/urls.py` - Added 3 URL routes

**Templates:**
- `templates/metrics/partials/needs_attention.html` (created)
- `templates/metrics/partials/ai_impact.html` (created)
- `templates/metrics/partials/team_velocity.html` (created)

### No Migrations Needed
All changes are view/service layer - no model changes.

### Verification Commands
```bash
# Verify all tests pass
make test

# Run just the new dashboard tests
.venv/bin/pytest apps/metrics/tests/dashboard/ -v
.venv/bin/pytest apps/metrics/tests/views/test_dashboard_views.py -v

# Check for lint issues
make ruff

# Verify no missing migrations
make migrations
```

### Next Steps (Phase 3: Templates)
1. Create bottleneck alert component template
2. Create integration health component template
3. Rewrite `templates/web/app_home.html` with new unified layout
4. Modify `templates/metrics/partials/review_distribution_chart.html` to show bottleneck alert
5. Add time range selector to dashboard header
6. Add loading skeletons to HTMX containers

### Test Count Summary
- Total metrics app tests: 2217 passing
- New dashboard service tests: 59
- New view tests: 30

---

## Phase 3 Plan (Templates)

### Goal
Rewrite `templates/web/app_home.html` to be the unified dashboard with HTMX lazy-loaded sections.

### Layout Design

```
┌─────────────────────────────────────────────────────────────────┐
│ Header: "Dashboard" + Time Range Selector (7d/30d/90d)          │
├─────────────────────────────────────────────────────────────────┤
│ Key Metrics Cards (4 cards: PRs Merged, Cycle Time, AI%, Review)│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌─────────────────────────────────┐│
│ │   Needs Attention       │  │   AI Impact Stats               ││
│ │   (paginated list)      │  │   (3 stats)                     ││
│ └─────────────────────────┘  └─────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐  ┌─────────────────────────────────┐│
│ │   Team Velocity         │  │   Review Distribution           ││
│ │   (top contributors)    │  │   + Bottleneck Alert            ││
│ └─────────────────────────┘  └─────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### TDD Implementation Steps

#### Step 1: TDD - Update team_home() view
**RED Phase:** Write failing tests in `apps/web/tests/test_views.py`
- `test_default_days_is_30` - Context should have days=30 by default
- `test_accepts_days_query_param` - Should accept ?days=7 param

**GREEN Phase:** Update `apps/web/views.py`
```python
days = int(request.GET.get("days", 30))  # Default 30, was 7
context["days"] = days  # Add to context
```

#### Step 2: Create bottleneck alert template (HTML only)
**File:** `templates/metrics/partials/bottleneck_alert.html`

#### Step 3: Update review_distribution_chart.html (HTML only)
- Include bottleneck alert at top

#### Step 4: Rewrite app_home.html (HTML only)
- HTMX containers with lazy loading
- Time range selector
- Keep setup wizard for non-connected teams

#### Step 5: E2E Testing
- Update `tests/e2e/dashboard.spec.ts`

### Key Files to Modify

| File | Action |
|------|--------|
| `apps/web/views.py` | Add `days` param to team_home() |
| `apps/web/tests/test_views.py` | Add tests for days param |
| `templates/web/app_home.html` | REWRITE with HTMX layout |
| `templates/metrics/partials/bottleneck_alert.html` | CREATE |
| `templates/metrics/partials/review_distribution_chart.html` | Add bottleneck include |

### Key Decisions Made
- 30-day default (changed from 7)
- Simple 7d/30d/90d buttons (not full date picker)
- Skeleton loaders for all lazy-loaded sections
- Remove "View Analytics" button (dashboard IS analytics now)

### HTMX Pattern

```html
<div id="needs-attention-container"
     hx-get="{% url 'metrics:needs_attention' %}?days={{ days }}&page=1"
     hx-trigger="load"
     hx-swap="innerHTML">
  <div class="skeleton h-80 w-full rounded-lg"></div>
</div>
```

### No Database Changes
All changes are template/view layer only.
