# Copilot Frontend & Seat Utilization Implementation Plan

**Last Updated: 2025-12-18**

## Executive Summary

Implement frontend visualization for existing Copilot metrics and add seat utilization tracking via GitHub's Billing Seats API. This completes the Copilot integration by providing CTOs visibility into:
1. Copilot usage metrics (completions, acceptance rates)
2. Seat utilization (paid vs active seats, cost efficiency)
3. Per-member Copilot activity

## Current State Analysis

### Existing Backend Infrastructure (Complete)
- `apps/integrations/services/copilot_metrics.py` - Metrics API client
- `apps/integrations/tasks.py` - Sync tasks (`sync_copilot_metrics_task`)
- `apps/metrics/services/dashboard_service.py` - Dashboard functions:
  - `get_copilot_metrics()` - totals and acceptance rate
  - `get_copilot_trend()` - weekly acceptance rate trend
  - `get_copilot_by_member()` - per-member breakdown
- OAuth scope `manage_billing:copilot` already configured

### Gaps to Address
1. **No seat utilization tracking** - Missing API call to `/orgs/{org}/copilot/billing/seats`
2. **No frontend templates** - Dashboard service functions have no UI
3. **No Copilot section on integrations home** - Status hidden from users
4. **No dashboard charts** - Copilot data not visualized

## Proposed Future State

### Integrations Home
- Copilot card showing: availability status, seat counts, last sync time
- Quick stats: total seats, active users, utilization rate

### CTO Dashboard
- Copilot acceptance rate trend chart
- Copilot usage metrics card (suggestions, acceptances, rate)
- Per-member Copilot table with activity levels

## API Integration Details

### GitHub Copilot Billing Seats API

**Endpoint**: `GET /orgs/{org}/copilot/billing/seats`

**Required Scope**: `manage_billing:copilot` (already have)

**Response Fields**:
```json
{
  "total_seats": 10,
  "seats": [
    {
      "assignee": {"login": "username"},
      "last_activity_at": "2025-12-15T10:30:00Z",
      "last_activity_editor": "vscode",
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

**Key Metrics**:
- `total_seats` - Paid seats
- `seat_breakdown.active_this_cycle` - Users with activity
- Utilization = `active_this_cycle / total * 100`

## Implementation Phases

### Phase 1: Seat Utilization Service (S - 2h)
Add seat tracking functions to `copilot_metrics.py`.

### Phase 2: Dashboard Views & URLs (S - 2h)
Create HTMX-compatible views for Copilot metrics.

### Phase 3: Integrations Home UI (M - 3h)
Add Copilot card to integrations home with status and quick stats.

### Phase 4: Dashboard Charts (M - 4h)
Add Copilot section to CTO overview with acceptance rate trend.

### Phase 5: Per-Member Table (S - 2h)
Add Copilot usage table with per-member breakdown.

### Phase 6: E2E Tests (S - 1h)
Add Playwright tests for Copilot UI components.

## Technical Architecture

```
┌─────────────────────────────────────────────────────────┐
│              GitHub Copilot Billing API                 │
│          GET /orgs/{org}/copilot/billing/seats          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              copilot_metrics.py (Service)               │
│  + fetch_copilot_seats(org, token)                      │
│  + get_seat_utilization(seats_data) -> dict             │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│              views.py (HTMX Views)                      │
│  + copilot_metrics_card()                               │
│  + copilot_trend_chart()                                │
│  + copilot_members_table()                              │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Templates                               │
│  + partials/copilot_metrics_card.html                   │
│  + partials/copilot_trend_chart.html                    │
│  + partials/copilot_members_table.html                  │
│  + integrations/components/copilot_card.html            │
└─────────────────────────────────────────────────────────┘
```

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Org has no Copilot | High | Low | Graceful empty state |
| Seat API returns 403 | Medium | Medium | Show "unavailable" message |
| User matching failures | Medium | Low | Display GitHub login as fallback |
| Chart.js performance | Low | Low | Limit data points to 12 weeks |

## Success Metrics

1. Copilot card visible on integrations home for connected orgs
2. Acceptance rate trend chart renders in <2s
3. Seat utilization percentage accurate within 1%
4. E2E tests cover all Copilot UI components

## Dependencies

- Existing Copilot metrics service (complete)
- GitHub OAuth with `manage_billing:copilot` scope (complete)
- Chart.js for visualizations (available)
- DaisyUI/Tailwind for styling (available)

## Estimated Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1. Seat Utilization Service | S (2h) | None |
| 2. Dashboard Views & URLs | S (2h) | Phase 1 |
| 3. Integrations Home UI | M (3h) | Phase 1 |
| 4. Dashboard Charts | M (4h) | Phases 1-2 |
| 5. Per-Member Table | S (2h) | Phases 1-2 |
| 6. E2E Tests | S (1h) | Phases 3-5 |

**Total**: ~14 hours of development

## Sources

- [GitHub Copilot User Management API](https://docs.github.com/en/rest/copilot/copilot-user-management?apiVersion=2022-11-28)
- [GitHub Copilot Licenses](https://docs.github.com/en/billing/concepts/product-billing/github-copilot-licenses)
- [About billing for GitHub Copilot](https://docs.github.com/en/copilot/concepts/billing/organizations-and-enterprises)
