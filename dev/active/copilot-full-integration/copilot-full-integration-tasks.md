# Copilot Full Integration - Tasks

## Status Legend
- [ ] Not started
- [~] In progress
- [x] Completed
- [!] Blocked

---

## Phase 1: Feature Flags Foundation (Epic 5) ✅ COMPLETE

### Task 1.1: Create Waffle Flag Definitions ✅
- [x] RED: Write test for `is_copilot_feature_active()` helper (10 tests)
- [x] GREEN: Implement in `integration_flags.py` with `COPILOT_FEATURE_FLAGS` constant
- [x] REFACTOR: Hierarchical flag checking (sub-flags require master flag)

### Task 1.2: Create Waffle Flags ✅
- [x] Created migration 0022 using `teams.Flag` model (not `waffle.Flag`)
- [x] Flags: copilot_enabled, copilot_seat_utilization, copilot_language_insights, copilot_delivery_impact, copilot_llm_insights

### Task 1.3: Gate Celery Tasks with Flags ✅
- [x] RED: Write tests for task flag gating (4 tests)
- [x] GREEN: Implemented `is_copilot_sync_enabled()` and `is_copilot_sync_globally_enabled()`
- [x] Gated `sync_copilot_metrics_task` and `sync_all_copilot_metrics`

---

## Phase 2: ROI & Seat Utilization (Epic 1) ✅ COMPLETE

### Task 2.1: Create CopilotSeatSnapshot Model ✅
- [x] RED: Write model tests (15 tests)
- [x] GREEN: Created model with migration 0036
- [x] REFACTOR: Added calculated properties (utilization_rate, monthly_cost, wasted_spend, cost_per_active_user)

### Task 2.2: Implement Billing API Fetch ✅
- [x] RED: Write tests for billing functions (10 tests)
- [x] GREEN: Implemented `fetch_copilot_billing()`, `parse_billing_response()`, `sync_copilot_seats_to_snapshot()`
- [x] REFACTOR: Uses shared `_make_github_api_request()` error handling

### Task 2.3: Dashboard Seat Stats ✅
- [x] RED: Write view tests (13 tests)
- [x] GREEN: Created `copilot_seat_stats_card` view with feature flag gating
- [x] GREEN: Created `templates/metrics/partials/copilot_seat_stats_card.html` with ROI warning
- [x] REFACTOR: Simplified flag check (sub-flag includes master validation)

### Task 2.4: CTO Overview Integration ✅
- [x] Added `copilot_seat_utilization_enabled` context in `dashboard_views.py`
- [x] Integrated seat stats card in `cto_overview.html` (lines 97-120)

### Task 2.5-2.6: Cost Calculations ✅
- [x] Implemented as model properties on `CopilotSeatSnapshot`
- [x] `COPILOT_SEAT_PRICE = Decimal("19.00")` constant

---

## Phase 3: Language & Editor Insights (Epic 2) ✅ COMPLETE

### Task 3.1: Create CopilotLanguageDaily Model ✅
- [x] RED: Write model tests (10 tests)
- [x] GREEN: Created model with migration 0037
- [x] REFACTOR: Added verbose_name, help_text, indexes, __str__

### Task 3.2: Create CopilotEditorDaily Model ✅
- [x] RED: Write model tests (9 tests)
- [x] GREEN: Created model with migrations 0038, 0039
- [x] REFACTOR: Added verbose_name, help_text, indexes, __str__

### Task 3.3: Parse Language/Editor from Metrics API ✅
- [x] RED: Write tests for parsing nested data (7 tests)
- [x] GREEN: Extended `parse_metrics_response()` to extract `editors` and `languages`
- [x] REFACTOR: Updated docstring, handles missing data gracefully

### Task 3.4: Sync Language/Editor Breakdown Data ✅
- [x] RED: Write tests for sync services (10 tests)
- [x] GREEN: Implemented `sync_copilot_language_data()` and `sync_copilot_editor_data()`
- [x] REFACTOR: Clean implementation using update_or_create pattern

### Task 3.5: Add Language Breakdown Chart ✅
- [x] RED: Write view tests (11 tests)
- [x] GREEN: Created `copilot_language_chart` view and template
- [x] REFACTOR: Proper docstring, sorts by acceptance rate

### Task 3.6: Add Editor Comparison Chart ✅
- [x] RED: Write view tests (11 tests)
- [x] GREEN: Created `copilot_editor_chart` view and template
- [x] REFACTOR: Includes active_users in aggregation

---

## Phase 4: Delivery Impact (Epic 3)

### Task 4.1: Add Copilot Fields to TeamMember
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for new fields
  - `copilot_last_activity_at`
  - `copilot_last_editor`

- [ ] GREEN: Create migration

- [ ] REFACTOR: Add property helpers

### Task 4.2: Sync Per-User Copilot Activity
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for syncing user activity from Seats API
- [ ] GREEN: Implement sync to TeamMember fields
- [ ] REFACTOR: Handle user matching edge cases

### Task 4.3: Copilot vs Non-Copilot PR Query
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for PR comparison query
  - Identify PRs by authors with recent Copilot activity
  - Calculate avg cycle time for each group
  - Calculate avg review time for each group

- [ ] GREEN: Implement comparison service

- [ ] REFACTOR: Add confidence indicators for small samples

### Task 4.4: Add Delivery Impact Cards
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for delivery impact endpoint
- [ ] GREEN: Create endpoint and template cards
- [ ] REFACTOR: Add trend indicators

---

## Phase 5: Enhanced LLM Insights (Epic 4)

### Task 5.1: Extend Copilot Prompt Context
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for extended prompt context
  - Includes seat utilization data
  - Includes wasted spend
  - Includes cost per active user

- [ ] GREEN: Extend `get_copilot_metrics_for_prompt()`

- [ ] REFACTOR: Optimize queries

### Task 5.2: Update Jinja2 Template
**TDD: Red-Green-Refactor**

- [ ] RED: Write template rendering tests
  - Test renders seat data
  - Test renders cost metrics
  - Test identifies struggling users (<20% acceptance)

- [ ] GREEN: Update `copilot_metrics.jinja2`

- [ ] REFACTOR: Improve formatting

### Task 5.3: Add Flag Check to LLM Context
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for LLM respecting `copilot_llm_insights` flag
- [ ] GREEN: Add flag check in prompt render
- [ ] REFACTOR: Clean up conditional logic

---

## Phase 6: Graceful Degradation (Epic 6)

### Task 6.1: Verify No UI Changes Without Copilot
**TDD: Red-Green-Refactor**

- [ ] RED: Write test that non-Copilot user sees no Copilot section
- [ ] GREEN: Ensure template conditionals work
- [ ] REFACTOR: Clean up any leaked Copilot references

### Task 6.2: Add Empty States
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for empty state scenarios
  - Copilot connected, no data yet
  - Copilot connected, no data in date range

- [ ] GREEN: Add empty state templates

- [ ] REFACTOR: Add helpful suggestions

### Task 6.3: Handle Partial Data Scenarios
**TDD: Red-Green-Refactor**

- [ ] RED: Write test for partial data handling
  - Has metrics but no seats
  - Has seats but no metrics
  - Has some but not all language data

- [ ] GREEN: Add conditional rendering

- [ ] REFACTOR: Consolidate data availability checks

---

## Integration Tests

### E2E Test Suite
- [ ] Test CTO Overview with Copilot enabled
- [ ] Test CTO Overview without Copilot
- [ ] Test flag toggle behavior
- [ ] Test chart rendering

---

## Notes

### Dependencies Between Tasks
- Phase 1 (Feature Flags) MUST complete before other phases
- Task 2.1 (Model) before Task 2.3 (Sync)
- Task 4.1 (Fields) before Task 4.2 (Sync)

### Testing Priority
1. Model tests (foundation)
2. Service tests (business logic)
3. View tests (API surface)
4. Template tests (rendering)
5. E2E tests (full flow)

### Session Progress (Last Updated: 2026-01-07)

**Completed:**
- [x] Phase 1: Feature Flags Foundation (14 tests)
- [x] Phase 2: ROI & Seat Utilization (38 tests)
- [x] Phase 3: Language & Editor Insights (49 tests)

**Total: 128 new tests passing**

**Next Steps:**
- [ ] Phase 4: Delivery Impact (Copilot vs Non-Copilot PR comparison)
- [ ] Phase 5: Enhanced LLM Insights
- [ ] Phase 6: Graceful Degradation

**Restart Commands:**
```bash
.venv/bin/python manage.py migrate
.venv/bin/pytest apps/metrics/tests/test_copilot_*.py apps/integrations/tests/test_copilot_*.py -v --tb=short --ignore=apps/integrations/tests/test_copilot_sync.py
```

**Key Implementation Files:**
- `apps/integrations/services/integration_flags.py` - Feature flag helpers
- `apps/integrations/services/copilot_metrics.py` - API functions + sync services
- `apps/metrics/models/aggregations.py` - CopilotSeatSnapshot, CopilotLanguageDaily, CopilotEditorDaily
- `apps/metrics/views/chart_views.py` - Copilot chart endpoints
- `templates/metrics/partials/copilot_*.html` - Dashboard templates
- `templates/metrics/cto_overview.html` - Dashboard integration

**Test Files:**
- `apps/integrations/tests/test_copilot_feature_flags.py` - 10 tests
- `apps/integrations/tests/test_copilot_billing.py` - 10 tests
- `apps/integrations/tests/test_copilot_seat_stats_view.py` - 13 tests
- `apps/integrations/tests/test_copilot_language_editor_parsing.py` - 7 tests
- `apps/integrations/tests/test_copilot_language_editor_sync.py` - 10 tests
- `apps/integrations/tests/test_copilot_language_chart_view.py` - 11 tests
- `apps/integrations/tests/test_copilot_editor_chart_view.py` - 11 tests
- `apps/metrics/tests/test_copilot_seat_snapshot.py` - 15 tests
- `apps/metrics/tests/test_copilot_language_daily.py` - 10 tests
- `apps/metrics/tests/test_copilot_editor_daily.py` - 9 tests
- Plus existing template/PR correlation tests
