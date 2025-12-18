# Copilot Frontend Tasks

**Last Updated: 2025-12-18**
**Status: PENDING**

## Phase 1: Seat Utilization Service (S - 2h)

### 1.1 Add Seat Fetching Function
- [ ] Add `fetch_copilot_seats(access_token, org_slug)` to `copilot_metrics.py`
- [ ] Handle pagination for large orgs (>100 seats)
- [ ] Handle 403 (insufficient permissions) gracefully

### 1.2 Add Utilization Calculator
- [ ] Add `get_seat_utilization(seats_data)` function
- [ ] Calculate: total_seats, active_seats, inactive_seats, utilization_rate
- [ ] Calculate cost metrics: monthly_cost ($19/seat), cost_per_active

### 1.3 Unit Tests
- [ ] Test `fetch_copilot_seats` with mocked response
- [ ] Test pagination handling
- [ ] Test 403 error handling
- [ ] Test `get_seat_utilization` calculations

**Tests:** `apps/integrations/tests/test_copilot_metrics.py`

---

## Phase 2: Dashboard Views & URLs (S - 2h)

### 2.1 Create HTMX Views
- [ ] Add `copilot_metrics_card(request)` view
- [ ] Add `copilot_trend_chart(request)` view
- [ ] Add `copilot_members_table(request)` view

### 2.2 Add URL Patterns
- [ ] Add `copilot/card/` pattern
- [ ] Add `copilot/trend/` pattern
- [ ] Add `copilot/members/` pattern

### 2.3 Unit Tests
- [ ] Test views return correct templates
- [ ] Test views require team authentication
- [ ] Test views handle empty data gracefully

**Tests:** `apps/metrics/tests/test_views.py`

---

## Phase 3: Integrations Home UI (M - 3h)

### 3.1 Create Copilot Card Component
- [ ] Create `templates/integrations/components/copilot_card.html`
- [ ] Show Copilot availability status (available/unavailable)
- [ ] Show seat counts (total, active, utilization %)
- [ ] Show last sync timestamp
- [ ] Add "Sync Now" button

### 3.2 Update Integrations Home View
- [ ] Add `copilot_seats` to context (if GitHub connected)
- [ ] Add `copilot_utilization` to context
- [ ] Handle API errors gracefully

### 3.3 Include Card in Home Template
- [ ] Add Copilot card after GitHub card
- [ ] Only show when GitHub is connected
- [ ] Show "Connect GitHub first" message otherwise

### 3.4 Unit Tests
- [ ] Test Copilot card renders when GitHub connected
- [ ] Test Copilot card hidden when GitHub not connected
- [ ] Test utilization displays correctly

**Tests:** `apps/integrations/tests/test_views.py`

---

## Phase 4: Dashboard Charts (M - 4h)

### 4.1 Create Copilot Metrics Card Partial
- [ ] Create `templates/metrics/partials/copilot_metrics_card.html`
- [ ] Show: total suggestions, acceptances, acceptance rate
- [ ] Show: active users count
- [ ] Style with DaisyUI stats component

### 4.2 Create Acceptance Rate Chart Partial
- [ ] Create `templates/metrics/partials/copilot_trend_chart.html`
- [ ] Use Chart.js line chart
- [ ] Show weekly acceptance rate trend
- [ ] Handle empty data with message

### 4.3 Add to CTO Overview
- [ ] Add Copilot section header
- [ ] Add HTMX container for metrics card
- [ ] Add HTMX container for trend chart
- [ ] Show skeleton loaders during load

### 4.4 Unit Tests
- [ ] Test chart partial renders with data
- [ ] Test chart partial handles empty data
- [ ] Test Chart.js config is valid

**Tests:** `apps/metrics/tests/test_views.py`

---

## Phase 5: Per-Member Table (S - 2h)

### 5.1 Create Members Table Partial
- [ ] Create `templates/metrics/partials/copilot_members_table.html`
- [ ] Columns: Member, Suggestions, Accepted, Rate
- [ ] Sort by suggestions descending
- [ ] Style with DaisyUI table component

### 5.2 Add to CTO Overview
- [ ] Add HTMX container for members table
- [ ] Position below trend chart

### 5.3 Unit Tests
- [ ] Test table renders with member data
- [ ] Test table handles no members gracefully
- [ ] Test table sorting

**Tests:** `apps/metrics/tests/test_views.py`

---

## Phase 6: E2E Tests (S - 1h)

### 6.1 Create Copilot E2E Tests
- [ ] Create `tests/e2e/copilot.spec.ts`
- [ ] Test Copilot card on integrations page
- [ ] Test Copilot section on CTO dashboard
- [ ] Test chart renders (visual check)

### 6.2 Update Testing Guide
- [ ] Add Copilot section to REAL-WORLD-TESTING.md
- [ ] Document Copilot-specific testing steps
- [ ] Add troubleshooting for Copilot issues

**Tests:** `tests/e2e/copilot.spec.ts`

---

## Test Commands

```bash
# Run all Copilot-related unit tests
make test ARGS='apps.integrations.tests.test_copilot_metrics --keepdb'
make test ARGS='apps.integrations.tests.test_copilot_sync --keepdb'
make test ARGS='apps.integrations.tests.test_views.TestCopilotSettings --keepdb'
make test ARGS='apps.metrics.tests.test_views --keepdb'

# Run E2E tests
make e2e  # All E2E tests
npx playwright test tests/e2e/copilot.spec.ts  # Copilot E2E only

# Run full test suite
make test ARGS='--keepdb'
```

---

## Definition of Done

Each phase is complete when:
1. All tasks checked off
2. Unit tests passing
3. Code reviewed (ruff lint clean)
4. No regressions in existing tests
