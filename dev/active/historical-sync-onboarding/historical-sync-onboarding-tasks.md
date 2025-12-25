# Historical Sync Onboarding - Tasks

## Overview

**Estimated Total Time:** 20-26 hours (~3-4 days focused work)

**TDD Approach:** Each feature should follow Red-Green-Refactor cycle.

**Progress:** Phases 1-5 complete (43 tests passing)

---

## Phase 1: Core Infrastructure (2-3 hours) ✅ COMPLETE

### 1.1 Date Range Calculation
- [x] Create `apps/integrations/services/historical_sync.py`
- [x] Implement `calculate_sync_date_range(months: int = 12)`
- [x] Handle edge cases: month boundaries (extends to day 1)
- [x] Write tests: `apps/integrations/tests/test_historical_sync.py`
  - [x] Test 12 months from mid-month
  - [x] Test 12 months from month start
  - [x] Test different month values (6, 24)
  - [x] Test returns tuple of dates
  - [x] Test end date is today

### 1.2 Repository Priority Ordering
- [x] Implement `prioritize_repositories(repos)` function
- [x] Add annotation for recent PR count (last 6 months) using Subquery
- [x] Write tests for ordering logic
  - [x] Test repos sorted by PR count descending
  - [x] Test repos with zero PRs
  - [x] Test single repo case
  - [x] Test empty queryset
  - [x] Test ignores old PRs (>6 months)

### 1.3 Configuration
- [x] Add `HISTORICAL_SYNC_CONFIG` to `tformance/settings.py`
  - [x] `HISTORY_MONTHS` (default: 12)
  - [x] `LLM_BATCH_SIZE` (default: 100)
  - [x] `GRAPHQL_PAGE_SIZE` (default: 25)
  - [x] `MAX_RETRIES` (default: 3)
  - [x] `RETRY_DELAY_SECONDS` (default: 30)
  - [x] `GROQ_POLL_INTERVAL` (default: 5)

---

## Phase 2: Celery Task with Progress (3-4 hours) ✅ COMPLETE

### 2.1 Task Structure
- [x] Add `sync_historical_data_task` to `apps/integrations/tasks.py`
- [x] Implement `sync_historical_data_task(team_id, repo_ids)`
- [x] Add proper error handling and logging
- [x] Update TrackedRepository sync_status on success/failure

### 2.2 Progress Reporting
- [x] Implement progress callback for repo-level progress
- [x] Update sync_progress, sync_prs_completed, sync_prs_total fields

### 2.3 Tests
- [x] Write `TestSyncHistoricalDataTask` in test file
  - [x] Test task exists
  - [x] Test task updates repo sync_status
  - [x] Test task returns result structure
  - [x] Test task handles failed repo

---

## Phase 3: OnboardingSyncService (4-5 hours) ✅ COMPLETE

### 3.1 Service Class
- [x] Create `apps/integrations/services/onboarding_sync.py`
- [x] Implement `OnboardingSyncService` class
  - [x] `__init__(team, github_token)`
  - [x] `sync_repository(repo, progress_callback)`
  - [x] `sync_all_repositories(repos, progress_callback)`
  - [x] `_calculate_days_back()` helper

### 3.2 GraphQL Integration
- [x] Import `sync_repository_history_graphql` from existing module
- [x] Use `asyncio.run()` to call async function from sync context
- [x] Pass days_back based on HISTORY_MONTHS config

### 3.3 Tests
- [x] Write `TestOnboardingSyncService` in test file
  - [x] Test service initialization
  - [x] Test sync_repository returns dict
  - [x] Test sync_repository calls GraphQL sync
  - [x] Test sync_repository uses configured history months
  - [x] Test progress callback invocation
  - [x] Test sync_all_repositories aggregates results

---

## Phase 4: Django Signals (1-2 hours) ✅ COMPLETE

### 4.1 Signal Definitions
- [x] Create `apps/integrations/signals.py`
- [x] Define `onboarding_sync_started` signal
- [x] Define `onboarding_sync_completed` signal
- [x] Define `repository_sync_completed` signal

### 4.2 Signal Emission
- [x] Emit `onboarding_sync_started` at task start
- [x] Emit `repository_sync_completed` after each repo
- [x] Emit `onboarding_sync_completed` when all repos done
- [x] Include relevant data in signal kwargs

### 4.3 Tests
- [x] Write `TestOnboardingSyncSignals` in test file
  - [x] Test signals exist
  - [x] Test onboarding_sync_started emitted
  - [x] Test onboarding_sync_completed emitted
  - [x] Test repository_sync_completed emitted per repo

---

## Phase 5: Frontend Progress UI (3-4 hours) ✅ COMPLETE

### 5.1 Template
- [x] Create `templates/onboarding/sync_progress.html`
- [x] Add overall progress bar with percentage
- [x] Add repository status list
- [x] Add completion section with CTA
- [x] Follow Easy Eyes design system

### 5.2 JavaScript
- [x] Poll-based progress tracking using fetch API
- [x] Progress bar updates with percentage
- [x] Handle success/error states
- [x] Show completion UI when done

### 5.3 View
- [x] Create `sync_progress` view in `apps/onboarding/views.py`
- [x] Create `start_sync` API view (POST returns task_id)
- [x] Add URL patterns for both views

### 5.4 Onboarding Flow Integration
- [x] Non-blocking sync: starts in background after repo selection
- [x] Floating sync indicator shows progress on all onboarding pages
- [x] Sync indicator links to detailed progress page
- [x] User can continue with Jira/Slack/complete while sync runs
- [x] Steps remain: GitHub(1) → Repos(2) → Jira(3) → Slack(4) → Done(5)

### 5.5 Tests
- [x] Write unit tests for sync_progress view (4 tests)
- [x] Write unit tests for start_sync API view (3 tests)
- [x] All 7 new tests passing

---

## Phase 6: Testing & Polish (4-5 hours) 🔲 PENDING

### 6.1 Integration Tests
- [ ] Full flow test with mocked external APIs
- [ ] Test partial failure scenarios
- [ ] Test resume after browser close

### 6.2 Edge Cases
- [ ] Empty repository (no PRs)
- [ ] Repository with 10k+ PRs
- [ ] All repos fail
- [ ] Groq API timeout
- [ ] GitHub rate limit hit

### 6.3 Error Handling
- [ ] Add retry logic with exponential backoff
- [ ] Improve error messages for users
- [ ] Log errors with context for debugging

### 6.4 Performance
- [ ] Profile sync for large repos
- [ ] Optimize batch sizes if needed
- [ ] Add timing logs

---

## Phase 7: Documentation & Cleanup (2-3 hours) 🔲 PENDING

### 7.1 Documentation
- [ ] Update `prd/ONBOARDING.md` with sync step
- [ ] Add sync configuration to README
- [ ] Document signals for extensibility

### 7.2 Code Review Checklist
- [ ] All tests passing
- [ ] No linting errors
- [ ] Type hints added
- [ ] Docstrings complete
- [ ] Error handling comprehensive

### 7.3 Final Verification
- [ ] Manual test full onboarding flow
- [ ] Verify dashboard shows data post-sync
- [ ] Check logs for any warnings

---

## Files Created/Modified

### New Files
- `apps/integrations/services/historical_sync.py` - Date range, priority functions
- `apps/integrations/services/onboarding_sync.py` - OnboardingSyncService class
- `apps/integrations/signals.py` - Django signals for extensibility
- `apps/integrations/tests/test_historical_sync.py` - 27 tests
- `templates/onboarding/sync_progress.html` - Sync progress UI with Celery polling

### Modified Files
- `apps/integrations/tasks.py` - Added sync_historical_data_task
- `tformance/settings.py` - Added HISTORICAL_SYNC_CONFIG
- `apps/onboarding/views.py` - Added sync_progress and start_sync views, background sync on repo selection
- `apps/onboarding/urls.py` - Added sync and start_sync URL patterns
- `apps/onboarding/tests/test_views.py` - Added 7 tests for sync views
- `templates/onboarding/base.html` - Added floating sync indicator (non-blocking)

---

## Test Summary

Total: **43 tests passing**

### Historical Sync Tests (27)
- TestCalculateSyncDateRange: 7 tests
- TestPrioritizeRepositories: 6 tests
- TestSyncHistoricalDataTask: 4 tests
- TestOnboardingSyncService: 6 tests
- TestOnboardingSyncSignals: 4 tests

### Onboarding View Tests (16)
- OnboardingStartViewTests: 3 tests
- GithubConnectViewTests: 1 test
- SelectOrganizationViewTests: 1 test
- SkipOnboardingViewTests: 4 tests
- SyncProgressViewTests: 4 tests
- StartSyncApiViewTests: 3 tests

---

## Definition of Done

- [x] All unit tests passing (pytest) - 43/43 ✅
- [ ] All E2E tests passing (Playwright)
- [x] Code follows project conventions (ruff)
- [ ] No N+1 queries in sync path
- [x] Progress updates visible in real-time
- [ ] User can see dashboard within 10 minutes (typical team)
- [x] Errors are gracefully handled
- [ ] Documentation updated
