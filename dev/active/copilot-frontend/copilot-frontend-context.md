# Copilot Frontend Context

**Last Updated: 2025-12-18**
**Status: PLANNING**

## Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/copilot_metrics.py` | Add `fetch_copilot_seats()` function |
| `apps/metrics/views.py` | Add HTMX views for Copilot metrics |
| `apps/metrics/urls.py` | Add URL patterns for Copilot endpoints |
| `templates/metrics/partials/copilot_metrics_card.html` | Key metrics card partial |
| `templates/metrics/partials/copilot_trend_chart.html` | Acceptance rate chart partial |
| `templates/metrics/partials/copilot_members_table.html` | Per-member breakdown table |
| `templates/integrations/components/copilot_card.html` | Integrations home Copilot card |
| `tests/e2e/copilot.spec.ts` | E2E tests for Copilot UI |

## Files to Modify

| File | Changes |
|------|---------|
| `apps/integrations/services/copilot_metrics.py` | Add seat utilization functions |
| `apps/integrations/tests/test_copilot_metrics.py` | Add seat utilization tests |
| `apps/integrations/views.py` | Update `integrations_home` context |
| `apps/integrations/templates/integrations/home.html` | Add Copilot card section |
| `templates/metrics/cto_overview.html` | Add Copilot charts section |
| `apps/metrics/views.py` | Add Copilot HTMX endpoints |
| `apps/metrics/urls.py` | Add Copilot URL patterns |

## Key Implementation Details

### Seat Utilization Service Functions

```python
# apps/integrations/services/copilot_metrics.py

def fetch_copilot_seats(access_token: str, org_slug: str) -> dict:
    """Fetch Copilot seat assignments from GitHub API.

    Returns:
        dict with keys:
            - total_seats (int): Paid seats
            - seats (list): Individual seat assignments
            - seat_breakdown (dict): Active/inactive counts
    """
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_slug}/copilot/billing/seats"
    headers = _build_github_headers(access_token)
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()


def get_seat_utilization(seats_data: dict) -> dict:
    """Calculate seat utilization metrics.

    Returns:
        dict with keys:
            - total_seats (int)
            - active_seats (int)
            - inactive_seats (int)
            - utilization_rate (Decimal): 0.00 to 100.00
            - monthly_cost (Decimal): $19 per seat
            - cost_per_active (Decimal): Monthly cost / active users
    """
```

### HTMX View Patterns

```python
# apps/metrics/views.py

@login_and_team_required
def copilot_metrics_card(request):
    """HTMX endpoint for Copilot key metrics card."""
    team = request.team
    days = int(request.GET.get("days", 30))
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    metrics = get_copilot_metrics(team, start_date, end_date)
    return render(request, "metrics/partials/copilot_metrics_card.html", {
        "metrics": metrics
    })
```

### Template Pattern (HTMX Loading)

```html
<!-- In cto_overview.html -->
<div id="copilot-metrics-container"
     hx-get="{% url 'metrics:copilot_metrics_card' %}?days={{ days }}"
     hx-trigger="load"
     hx-swap="innerHTML">
  <div class="skeleton h-24 w-full rounded-lg"></div>
</div>
```

## Data Flow

```
User visits CTO Overview
    │
    ▼
Page loads with skeleton placeholders
    │
    ▼
HTMX triggers hx-get requests to:
├── /metrics/copilot/card/
├── /metrics/copilot/trend/
└── /metrics/copilot/members/
    │
    ▼
Views call dashboard_service functions:
├── get_copilot_metrics()
├── get_copilot_trend()
└── get_copilot_by_member()
    │
    ▼
HTML partials rendered and swapped in
```

## API Reference

### GitHub Copilot Billing Seats API

**Endpoint**: `GET /orgs/{org}/copilot/billing/seats`

**Headers**:
```
Authorization: Bearer {token}
Accept: application/vnd.github+json
```

**Response Structure**:
```json
{
  "total_seats": 10,
  "seats": [
    {
      "assignee": {
        "login": "octocat",
        "id": 1,
        "avatar_url": "https://..."
      },
      "assigning_team": null,
      "last_activity_at": "2025-12-15T10:30:00Z",
      "last_activity_editor": "vscode/1.85.0",
      "created_at": "2025-01-01T00:00:00Z"
    }
  ],
  "seat_breakdown": {
    "total": 10,
    "added_this_cycle": 2,
    "pending_invitation": 1,
    "pending_cancellation": 0,
    "active_this_cycle": 8,
    "inactive_this_cycle": 2
  }
}
```

## Key Decisions

1. **HTMX for loading** - Follow existing pattern in cto_overview.html
2. **Chart.js for visualization** - Consistent with other dashboard charts
3. **DaisyUI cards** - Match existing UI components
4. **$19/seat pricing** - Copilot Business tier assumption
5. **30-day activity window** - Match GitHub's "active this cycle" definition

## Dependencies

- `apps/integrations/services/copilot_metrics.py` (existing)
- `apps/metrics/services/dashboard_service.py` (existing)
- Chart.js (available)
- DaisyUI/Tailwind (available)
- HTMX (available)
