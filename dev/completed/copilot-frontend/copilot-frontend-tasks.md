# Copilot Frontend Tasks

**Last Updated: 2025-12-18**
**Status: COMPLETE**

## Phase 1: Seat Utilization Service (S - 2h) - COMPLETE

### 1.1 Add Seat Fetching Function
- [x] Add `fetch_copilot_seats(access_token, org_slug)` to `copilot_metrics.py`
- [x] Handle 403 (insufficient permissions) gracefully
- [x] Add `_make_github_api_request()` helper for consistent error handling

### 1.2 Add Utilization Calculator
- [x] Add `get_seat_utilization(seats_data)` function
- [x] Calculate: total_seats, active_seats, inactive_seats, utilization_rate
- [x] Calculate cost metrics: monthly_cost ($19/seat), cost_per_active_user

### 1.3 Unit Tests
- [x] Test `fetch_copilot_seats` with mocked response
- [x] Test 403 error handling
- [x] Test `get_seat_utilization` calculations
- [x] Test edge cases (zero seats, zero active)

**Tests:** `apps/integrations/tests/test_copilot_metrics.py` (9 new tests)

---

## Phase 2: Dashboard Views & URLs (S - 2h) - COMPLETE

### 2.1 Create HTMX Views
- [x] Add `copilot_metrics_card(request)` view
- [x] Add `copilot_trend_chart(request)` view
- [x] Add `copilot_members_table(request)` view

### 2.2 Add URL Patterns
- [x] Add `cards/copilot/` pattern
- [x] Add `charts/copilot-trend/` pattern
- [x] Add `tables/copilot-members/` pattern

### 2.3 Unit Tests
- [x] Test views return correct templates
- [x] Test views require team authentication
- [x] Test views handle empty data gracefully

**Tests:** `apps/metrics/tests/test_views.py` (30 new tests)

---

## Phase 3: Integrations Home UI (M - 3h) - COMPLETE

### 3.1 Create Copilot Card Component
- [x] Add Copilot card to `templates/integrations/home.html`
- [x] Show Copilot availability status (available/unavailable)
- [x] Show "Available" badge when GitHub connected
- [x] Add "Sync Now" button placeholder

### 3.2 Styling
- [x] Violet theme consistent with Copilot branding
- [x] DaisyUI card component structure
- [x] Consistent with GitHub/Jira/Slack cards

---

## Phase 4: Dashboard Charts (M - 4h) - COMPLETE

### 4.1 Create Copilot Metrics Card Partial
- [x] Create `templates/metrics/partials/copilot_metrics_card.html`
- [x] Show: total suggestions, acceptances, acceptance rate
- [x] Show: active users count
- [x] Style with DaisyUI stats component
- [x] Handle empty state with "No Copilot data" message

### 4.2 Create Acceptance Rate Chart Partial
- [x] Create `templates/metrics/partials/copilot_trend_chart.html`
- [x] Use Chart.js canvas element
- [x] Include json_script for data passing
- [x] Handle empty data with message

### 4.3 Add to CTO Overview
- [x] Add Copilot section divider with violet icon
- [x] Add HTMX container for metrics card
- [x] Add HTMX container for trend chart
- [x] Show skeleton loaders during load

---

## Phase 5: Per-Member Table (S - 2h) - COMPLETE

### 5.1 Create Members Table Partial
- [x] Create `templates/metrics/partials/copilot_members_table.html`
- [x] Columns: Avatar, Member, Total, Accepted, Rate
- [x] Style with DaisyUI table-zebra
- [x] Avatar placeholders for members
- [x] Color-coded acceptance rates

### 5.2 Add to CTO Overview
- [x] Add HTMX container for members table
- [x] Position in 2-column grid with trend chart
- [x] Handle empty state

---

## Phase 6: Chart.js & Final Integration (S - 1h) - COMPLETE

### 6.1 Chart.js Initialization
- [x] Add chart initialization in `assets/javascript/app.js`
- [x] Use existing `AppDashboardCharts.weeklyBarChart()` function
- [x] Handle chart destroy/recreate on HTMX swap

### 6.2 Final Testing
- [x] All unit tests passing (1389 total)
- [x] Linter clean (ruff B904 fix applied)

---

## Post-Implementation

### Linter Fix
- [x] Fix ruff B904: `raise CopilotMetricsError(...) from e`

### Pending
- [ ] Commit linter fix
- [ ] Push to pass CI
- [ ] Move to `dev/completed/`
- [ ] Real-world testing with actual Copilot data

---

## Test Commands

```bash
# Run all Copilot-related unit tests
make test ARGS='apps.integrations.tests.test_copilot_metrics --keepdb'
make test ARGS='apps.metrics.tests.test_views --keepdb'

# Run linter
.venv/bin/ruff check apps/integrations/services/copilot_metrics.py

# Run full test suite
make test ARGS='--keepdb'
```

---

## Definition of Done

- [x] All tasks checked off
- [x] Unit tests passing (39 new tests)
- [x] Code reviewed (ruff lint clean)
- [x] No regressions in existing tests
- [ ] Committed and pushed
