# Copilot Integration Tasks

**Last Updated: 2025-12-18**
**Status: ALL PHASES COMPLETE**

## Phase 1: OAuth Scope Update (S - 2h) - COMPLETE

### 1.1 Update OAuth Scopes
- [x] Add `manage_billing:copilot` to `GITHUB_OAUTH_SCOPES` in `github_oauth.py`
- [x] Test OAuth flow still works with new scope
- [x] Refactored scopes to list format with documentation

**Tests:** `apps/integrations/tests/test_github_oauth.py` - 48 tests passing

---

## Phase 2: Copilot Service Module (M - 4h) - COMPLETE

### 2.1 Create Copilot Metrics Service
- [x] Create `apps/integrations/services/copilot_metrics.py`
- [x] Implement `fetch_copilot_metrics(access_token, org_slug, since=None, until=None)`
- [x] Implement `check_copilot_availability(access_token, org_slug)` - returns True/False
- [x] Implement `parse_metrics_response(data)` - normalize API response
- [x] Implement `map_copilot_to_ai_usage(parsed_day_data)` - map to AIUsageDaily fields

### 2.2 Error Handling
- [x] Handle 403 (insufficient licenses) gracefully
- [x] Handle network errors gracefully
- [x] CopilotMetricsError exception class created

### 2.3 Unit Tests
- [x] Write tests for `fetch_copilot_metrics` with mocked responses
- [x] Write tests for error handling scenarios
- [x] Write tests for `check_copilot_availability`
- [x] Write tests for `map_copilot_to_ai_usage`

**Tests:** `apps/integrations/tests/test_copilot_metrics.py` - 18 tests passing

---

## Phase 3: Data Storage (S - 1h) - COMPLETE

### 3.1 Verify AIUsageDaily Model
- [x] Confirmed `AIUsageDaily` model fields match Copilot API response
- [x] No migration needed - existing model sufficient

### 3.2 Data Mapping
- [x] `code_completions_total` → `suggestions_shown`
- [x] `code_completions_accepted` → `suggestions_accepted`
- [x] `acceptance_rate` calculated as (accepted/total) * 100

**Tests:** Included in test_copilot_metrics.py (TestCopilotDataStorage class)

---

## Phase 4: Sync Task (M - 4h) - COMPLETE

### 4.1 Create Celery Task
- [x] Add `sync_copilot_metrics_task(team_id)` to `apps/integrations/tasks.py`
- [x] Implement team member matching by `github_username`
- [x] Handle unmatched users (stores aggregate data)

### 4.2 Scheduler Integration
- [x] Add `sync_all_copilot_metrics()` task for daily batch sync
- [ ] Register in Celery beat schedule (manual task - needs config update)

### 4.3 Retry Logic
- [x] Implement exponential backoff for API failures (60s, 120s, 240s)
- [x] Set max retries (3)
- [x] Log failures to Sentry

### 4.4 Unit Tests
- [x] Test sync task with mocked service
- [x] Test team member matching logic
- [x] Test retry behavior

**Tests:** `apps/integrations/tests/test_copilot_sync.py` - 10 tests passing

---

## Phase 5: Dashboard Enhancement (M - 6h) - COMPLETE (Backend only)

### 5.1 Backend - Dashboard Service Functions
- [x] `get_copilot_metrics(team, start_date, end_date)` - totals and acceptance rate
- [x] `get_copilot_trend(team, start_date, end_date)` - weekly trend data
- [x] `get_copilot_by_member(team, start_date, end_date)` - per-member breakdown

### 5.2-5.4 Frontend (NOT IMPLEMENTED)
- [ ] Add Copilot data to existing charts (future work)
- [ ] Create Copilot metrics table (future work)
- [ ] Empty state design (future work)

**Tests:** `apps/metrics/tests/test_dashboard_service.py` - TestCopilotDashboardService (4 tests)

---

## Phase 6: Settings UI (S - 2h) - COMPLETE

### 6.1 Integration Settings Page
- [x] Add `copilot_available` to integrations home context
- [x] Add `copilot_last_sync` to integrations home context
- [x] Show Copilot status when GitHub is connected

### 6.2 Manual Sync
- [x] Create `copilot_sync` view for manual sync trigger
- [x] Add URL pattern `copilot/sync/`
- [x] Returns 404 if no GitHub integration

### 6.3 Tests
- [x] Test settings page includes Copilot context
- [x] Test sync view triggers task
- [x] Test sync requires GitHub integration

**Tests:** `apps/integrations/tests/test_views.py` - TestCopilotSettings (3 tests)

---

## Remaining Work (Future Enhancement)

1. **Celery Beat Schedule**: Add `sync_all_copilot_metrics` to periodic tasks
2. **Frontend Charts**: Add Copilot data visualization to dashboard
3. **Template Updates**: Add Copilot section to integrations home template
4. **CLAUDE.md**: Update documentation with Copilot integration details

---

## Test Summary

All tests passing:
```bash
make test ARGS='apps.integrations.tests.test_github_oauth --keepdb'     # 48 tests
make test ARGS='apps.integrations.tests.test_copilot_metrics --keepdb'  # 18 tests
make test ARGS='apps.integrations.tests.test_copilot_sync --keepdb'     # 10 tests
make test ARGS='apps.metrics.tests.test_dashboard_service.TestCopilotDashboardService --keepdb'  # 4 tests
make test ARGS='apps.integrations.tests.test_views.TestCopilotSettings --keepdb'  # 3 tests
```
