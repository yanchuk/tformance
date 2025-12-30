# Repository Selector - Context & Reference

**Last Updated: 2024-12-30**

## Quick Reference

### Files to Create
| File | Purpose |
|------|---------|
| `apps/metrics/tests/test_repo_filter.py` | TDD tests for repo filtering |
| `assets/javascript/components/repo-selector.js` | Alpine component |
| `templates/metrics/partials/repo_selector.html` | Dropdown UI |
| `tests/e2e/repo-selector.spec.ts` | E2E tests |

### Files to Modify
| File | Change |
|------|--------|
| `apps/metrics/services/dashboard_service.py` | Add `repo` param to 30+ functions |
| `apps/metrics/views/analytics_views.py` | Add repo to context |
| `apps/metrics/views/chart_views.py` | Pass repo to service calls |
| `assets/javascript/alpine.js` | Add `repoFilter` store |
| `templates/metrics/analytics/base_analytics.html` | Add selector UI |
| 7 analytics templates | Update crosslinks |

---

## Test Data Setup Pattern

```python
# apps/metrics/tests/test_repo_filter.py
from django.test import TestCase
from apps.metrics.factories import TeamFactory, PullRequestFactory, TeamMemberFactory
from apps.metrics.services import dashboard_service
from datetime import date, timedelta

class RepoFilterTestCase(TestCase):
    """Base test case with multi-repo test data."""

    def setUp(self):
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

        # Create PRs in different repos
        self.frontend_pr = PullRequestFactory(
            team=self.team,
            github_repo="acme/frontend",
            author=self.member,
            state="merged",
            merged_at=date.today() - timedelta(days=5),
            cycle_time_hours=24.0,
        )
        self.backend_pr = PullRequestFactory(
            team=self.team,
            github_repo="acme/backend",
            author=self.member,
            state="merged",
            merged_at=date.today() - timedelta(days=3),
            cycle_time_hours=48.0,
        )
        self.mobile_pr = PullRequestFactory(
            team=self.team,
            github_repo="acme/mobile",
            author=self.member,
            state="merged",
            merged_at=date.today() - timedelta(days=1),
            cycle_time_hours=12.0,
        )

        self.start_date = date.today() - timedelta(days=30)
        self.end_date = date.today()
```

---

## TDD Test Pattern

```python
class TestRepoFilterHelper(RepoFilterTestCase):
    """Tests for _apply_repo_filter helper."""

    def test_apply_repo_filter_returns_filtered_queryset(self):
        """Filter returns only PRs from specified repo."""
        from apps.metrics.models import PullRequest
        qs = PullRequest.objects.filter(team=self.team)

        filtered = dashboard_service._apply_repo_filter(qs, "acme/frontend")

        self.assertEqual(filtered.count(), 1)
        self.assertEqual(filtered.first().github_repo, "acme/frontend")

    def test_apply_repo_filter_returns_all_when_none(self):
        """No filter returns all PRs."""
        from apps.metrics.models import PullRequest
        qs = PullRequest.objects.filter(team=self.team)

        filtered = dashboard_service._apply_repo_filter(qs, None)

        self.assertEqual(filtered.count(), 3)

    def test_apply_repo_filter_returns_all_when_empty_string(self):
        """Empty string treated same as None."""
        from apps.metrics.models import PullRequest
        qs = PullRequest.objects.filter(team=self.team)

        filtered = dashboard_service._apply_repo_filter(qs, "")

        self.assertEqual(filtered.count(), 3)


class TestGetCycleTimeTrendRepoFilter(RepoFilterTestCase):
    """Tests for get_cycle_time_trend with repo filter."""

    def test_returns_all_repos_when_no_filter(self):
        """Without repo param, returns data for all repos."""
        result = dashboard_service.get_cycle_time_trend(
            self.team, self.start_date, self.end_date
        )
        # Assert includes data from all repos
        self.assertTrue(len(result) > 0)

    def test_filters_by_repo_when_specified(self):
        """With repo param, returns only data from that repo."""
        result = dashboard_service.get_cycle_time_trend(
            self.team, self.start_date, self.end_date, repo="acme/frontend"
        )
        # Assert only frontend data included
        # (specific assertion depends on function return structure)

    def test_returns_empty_for_nonexistent_repo(self):
        """Non-existent repo returns empty result."""
        result = dashboard_service.get_cycle_time_trend(
            self.team, self.start_date, self.end_date, repo="acme/nonexistent"
        )
        # Assert empty result (not error)
```

---

## Service Layer Implementation Pattern

```python
# apps/metrics/services/dashboard_service.py

def _apply_repo_filter(qs: QuerySet, repo: str | None) -> QuerySet:
    """Apply repository filter to queryset if repo is specified.

    Args:
        qs: Base queryset to filter
        repo: Repository name (owner/repo format) or None/empty for all

    Returns:
        Filtered queryset
    """
    if repo:
        return qs.filter(github_repo=repo)
    return qs


def get_cycle_time_trend(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,  # NEW PARAMETER
) -> list[dict]:
    """Get cycle time trend data.

    Args:
        team: Team to get data for
        start_date: Start of date range
        end_date: End of date range
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        List of dicts with week/cycle_time data
    """
    qs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__date__gte=start_date,
        merged_at__date__lte=end_date,
    )

    # Apply repo filter
    qs = _apply_repo_filter(qs, repo)

    # ... rest of function unchanged
```

---

## View Layer Pattern

```python
# apps/metrics/views/chart_views.py

def _get_repo_filter(request: HttpRequest) -> str | None:
    """Extract repository filter from request.

    Args:
        request: HTTP request

    Returns:
        Repository name or None if not specified
    """
    repo = request.GET.get("repo", "")
    return repo if repo else None


@team_admin_required
def cycle_time_chart(request: HttpRequest) -> HttpResponse:
    """Cycle time trend chart."""
    start_date, end_date = get_date_range_from_request(request)
    repo = _get_repo_filter(request)  # NEW

    data = dashboard_service.get_cycle_time_trend(
        request.team, start_date, end_date, repo=repo  # Pass repo
    )
    chart_data = chart_formatters.format_time_series(data)
    return TemplateResponse(
        request,
        "metrics/partials/cycle_time_chart.html",
        {"chart_data": chart_data},
    )
```

---

## Alpine.js Store Pattern

```javascript
// assets/javascript/alpine.js (add after dateRange store)

Alpine.store('repoFilter', {
  selectedRepo: '',  // '' = all, 'owner/repo' = specific
  repos: [],         // Available repos (populated from page context)

  setRepo(repo) {
    this.selectedRepo = repo;
  },

  isAll() {
    return this.selectedRepo === '';
  },

  isSelected(repo) {
    return this.selectedRepo === repo;
  },

  syncFromUrl() {
    const params = new URLSearchParams(window.location.search);
    this.selectedRepo = params.get('repo') || '';
  },

  toUrlParam() {
    if (this.selectedRepo) {
      return `repo=${encodeURIComponent(this.selectedRepo)}`;
    }
    return '';
  }
});

// Sync on init
Alpine.store('repoFilter').syncFromUrl();
```

---

## Template Crosslink Pattern

```html
<!-- Before -->
<a href="{% url 'metrics:pr_list' %}?days={{ days }}">
  View All PRs
</a>

<!-- After -->
<a href="{% url 'metrics:pr_list' %}?days={{ days }}{% if selected_repo %}&repo={{ selected_repo }}{% endif %}">
  View All PRs
</a>
```

---

## E2E Test Pattern

```typescript
// tests/e2e/repo-selector.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Repository Selector', () => {
  test.beforeEach(async ({ page }) => {
    // Login and navigate to analytics
    await page.goto('/accounts/login/');
    await page.fill('[name="login"]', 'admin@example.com');
    await page.fill('[name="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await page.waitForURL('**/dashboard/**');
    await page.goto('/a/test-team/analytics/');
  });

  test('repo selector dropdown opens and closes', async ({ page }) => {
    // Find and click the repo selector button
    const selector = page.locator('[data-testid="repo-selector"]');
    await selector.click();

    // Verify dropdown is visible
    const dropdown = page.locator('[data-testid="repo-dropdown"]');
    await expect(dropdown).toBeVisible();

    // Click elsewhere to close
    await page.click('body');
    await expect(dropdown).not.toBeVisible();
  });

  test('selecting repo updates URL', async ({ page }) => {
    // Open dropdown
    await page.click('[data-testid="repo-selector"]');

    // Select a specific repo
    await page.click('text=frontend');

    // Verify URL updated
    await expect(page).toHaveURL(/repo=.*frontend/);
  });

  test('tab navigation preserves repo selection', async ({ page }) => {
    // Select a repo
    await page.click('[data-testid="repo-selector"]');
    await page.click('text=frontend');

    // Click AI Adoption tab
    await page.click('text=AI Adoption');

    // Verify URL still has repo param
    await expect(page).toHaveURL(/repo=.*frontend/);
  });
});
```

---

## Key Decisions Reference

| Decision | Choice | Rationale |
|----------|--------|-----------|
| URL param for "all" | Omit param | Cleaner URLs, backward compatible |
| Repo format in URL | Full `owner/repo` | Unambiguous, matches GitHub |
| Store sync | On alpine:init | Consistent with dateRange pattern |
| Filter helper | Separate function | DRY, testable |
| Team member display | Only contributors | UX - no confusing zeros |

---

## Parallel Work Coordination

### pr-sidebar-move Task
- Status: In progress (parallel)
- Overlap: Crosslink updates
- Coordination: Complete repo-selector crosslinks, then merge carefully

### Files Both Tasks Touch
- `templates/metrics/analytics/base_analytics.html`
- Various analytics template crosslinks

---

## Commands Reference

```bash
# Run repo filter tests only
pytest apps/metrics/tests/test_repo_filter.py -v

# Run with coverage
pytest apps/metrics/tests/test_repo_filter.py --cov=apps.metrics.services.dashboard_service

# Run E2E tests
npx playwright test tests/e2e/repo-selector.spec.ts

# Full test suite
make test

# Lint check
make ruff
```
