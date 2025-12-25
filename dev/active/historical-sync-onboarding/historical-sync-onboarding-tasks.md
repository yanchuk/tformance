# Historical Sync Onboarding - Tasks

## Overview

**Estimated Total Time:** 20-26 hours (~3-4 days focused work)

**TDD Approach:** Each feature should follow Red-Green-Refactor cycle.

---

## Phase 1: Core Infrastructure (2-3 hours)

### 1.1 Date Range Calculation
- [ ] Create `apps/integrations/services/sync_utils.py`
- [ ] Implement `calculate_sync_date_range(months: int = 12)`
- [ ] Handle edge cases: month boundaries, leap years
- [ ] Write tests: `apps/integrations/tests/test_sync_utils.py`
  - [ ] Test 12 months from mid-month
  - [ ] Test 12 months from month start
  - [ ] Test different month values (6, 24)

### 1.2 Repository Priority Ordering
- [ ] Implement `prioritize_repositories(repos)` function
- [ ] Add annotation for recent PR count (last 6 months)
- [ ] Write tests for ordering logic
  - [ ] Test repos sorted by PR count descending
  - [ ] Test repos with zero PRs
  - [ ] Test single repo case

### 1.3 Configuration
- [ ] Add `HISTORICAL_SYNC_CONFIG` to `tformance/settings.py`
  - [ ] `HISTORY_MONTHS` (default: 12)
  - [ ] `LLM_BATCH_SIZE` (default: 100)
  - [ ] `GRAPHQL_PAGE_SIZE` (default: 25)
  - [ ] `MAX_RETRIES` (default: 3)

---

## Phase 2: Celery Task with Progress (3-4 hours)

### 2.1 Task Structure
- [ ] Create `apps/integrations/tasks/historical_sync.py`
- [ ] Implement `sync_historical_data_task(team_id, repo_ids)`
- [ ] Integrate `celery_progress.backend.ProgressRecorder`
- [ ] Add proper error handling and logging

### 2.2 Progress Reporting
- [ ] Implement multi-level progress calculation
  - [ ] Repo-level progress (x/N repos)
  - [ ] PR-level progress within repo (y/M PRs)
- [ ] Create `calculate_overall_progress()` helper
- [ ] Include repo status info in progress metadata

### 2.3 Tests
- [ ] Write `apps/integrations/tests/test_historical_sync_task.py`
  - [ ] Test task starts and updates progress
  - [ ] Test error handling per repo
  - [ ] Test signal emission on completion

---

## Phase 3: OnboardingSyncService (4-5 hours)

### 3.1 Service Class
- [ ] Create `apps/integrations/services/onboarding_sync.py`
- [ ] Implement `OnboardingSyncService` class
  - [ ] `__init__(team, github_token)`
  - [ ] `sync_repository(repo, progress_callback)`
  - [ ] `sync_all_repositories(repos, progress_callback)`

### 3.2 GraphQL Integration
- [ ] Import and configure `GitHubGraphQLFetcher`
- [ ] Add date range filtering to fetch calls
- [ ] Handle pagination and rate limits
- [ ] Implement batch PR creation

### 3.3 LLM Integration
- [ ] Implement `_process_llm_batch(prs)` method
- [ ] Use `GroqBatchProcessor` with polling
- [ ] Apply results to PR records
- [ ] Handle Groq API failures gracefully

### 3.4 Tests
- [ ] Write `apps/integrations/tests/test_onboarding_sync.py`
  - [ ] Test service initialization
  - [ ] Test single repo sync (mocked GraphQL)
  - [ ] Test LLM batch processing (mocked Groq)
  - [ ] Test progress callback invocation

---

## Phase 4: Django Signals (1-2 hours)

### 4.1 Signal Definitions
- [ ] Create `apps/integrations/signals.py`
- [ ] Define `historical_sync_repo_complete` signal
- [ ] Define `historical_sync_complete` signal
- [ ] Define `historical_sync_progress` signal (optional)

### 4.2 Signal Emission
- [ ] Emit `historical_sync_repo_complete` after each repo
- [ ] Emit `historical_sync_complete` when all repos done
- [ ] Include relevant data in signal kwargs

### 4.3 Initial Receivers (Placeholder)
- [ ] Create `apps/integrations/receivers.py`
- [ ] Add placeholder for email notification
- [ ] Add placeholder for weekly aggregation trigger
- [ ] Register receivers in `apps/integrations/apps.py`

### 4.4 Tests
- [ ] Write `apps/integrations/tests/test_signals.py`
  - [ ] Test signals emitted correctly
  - [ ] Test receiver registration

---

## Phase 5: Frontend Progress UI (3-4 hours)

### 5.1 Template
- [ ] Create `templates/onboarding/sync_progress.html`
- [ ] Add overall progress bar with percentage
- [ ] Add repository status list
- [ ] Add completion section with CTA
- [ ] Follow Easy Eyes design system

### 5.2 JavaScript
- [ ] Integrate `celery_progress.js`
- [ ] Implement `CeleryProgressBar.initProgressBar()` callbacks
- [ ] Add `updateRepoStatuses()` function (safe DOM methods)
- [ ] Handle success/error states

### 5.3 View
- [ ] Create sync progress view in `apps/onboarding/views.py`
- [ ] Start Celery task on page load
- [ ] Pass task_id to template
- [ ] Add URL pattern

### 5.4 Onboarding Flow Integration
- [ ] Add step 6 to onboarding flow
- [ ] Redirect to sync page after repo selection
- [ ] Block dashboard access until sync complete
- [ ] Handle "continue later" case

### 5.5 Tests
- [ ] Write E2E test for progress page
  - [ ] Test progress bar updates
  - [ ] Test completion redirect

---

## Phase 6: Testing & Polish (4-5 hours)

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

## Phase 7: Documentation & Cleanup (2-3 hours)

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

## Optional Enhancements (Future)

### Email Notifications
- [ ] Send email when sync starts
- [ ] Send email when sync completes
- [ ] Include PR count and time taken

### Slack Notifications
- [ ] Post to configured channel
- [ ] Include sync summary

### Resume/Retry
- [ ] Allow user to retry failed repos
- [ ] Show "Resume Sync" button if incomplete

### Progress Persistence
- [ ] Store progress in session/DB
- [ ] Allow returning to progress page

---

## Definition of Done

- [ ] All unit tests passing (pytest)
- [ ] All E2E tests passing (Playwright)
- [ ] Code follows project conventions (ruff)
- [ ] No N+1 queries in sync path
- [ ] Progress updates visible in real-time
- [ ] User can see dashboard within 10 minutes (typical team)
- [ ] Errors are gracefully handled
- [ ] Documentation updated
