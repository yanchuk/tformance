# Tasks: LLM Misclassification Investigation

**Last Updated:** 2026-01-03

## Related Task

**Sync Progress Fix** - See `dev/active/sync-progress-fix/` for the progress bar bug fix (shows 2% when complete).

## Phase 0: Verification & Fix - COMPLETE

- [x] Investigate why PR #2408 classified as Rails
- [x] Confirm OAuth scopes are correct (`repo` provides full access)
- [x] Confirm GraphQL query includes files, commits, reviews
- [x] Test direct API call with app OAuth token (works!)
- [x] Test GraphQL fetch with `GitHubGraphQLClient` (works!)
- [x] Identify that `_process_files()` works when called manually
- [x] **User action: Delete team 149 data and re-run onboarding** → Team 150 created
- [x] Monitor fresh sync for file saving → **BUG REPRODUCES**
- [x] Confirm files NOT saved despite GraphQL returning them
- [x] **FIX THE BUG: Changed `asyncio.run()` to `async_to_sync()`**
- [x] Add logging to `_process_files()` for debugging
- [x] **Fix all 4 asyncio.run() locations in tasks.py**
- [x] **Fix missing llm_summary_version in LLM save**
- [x] **Update tests for new async_to_sync pattern**
- [ ] **TEST THE FIX: Re-run sync for team 150** (requires Celery restart)

## Fix Summary

**Root Cause**: `asyncio.run()` creates a new event loop that breaks `@sync_to_async` database operations in Celery workers.

**Why it silently fails**:
1. `asyncio.run()` creates a NEW event loop in current thread
2. `@sync_to_async(thread_sensitive=True)` expects Django's thread context
3. DB operations execute but don't commit properly in Celery workers
4. No errors raised - data just doesn't persist

**Why we didn't catch it earlier**:
- Tests use `asyncio.run()` outside Celery context (works fine)
- PR metadata saves correctly (different code path)
- No error logs - silent failure
- Bug only manifests in Celery worker's threading model

**Solution**: Use `async_to_sync()` from `asgiref` instead - Django's recommended approach for calling async from sync.

**Files Changed**:
- `apps/integrations/services/onboarding_sync.py` - Use `async_to_sync` instead of `asyncio.run`
- `apps/integrations/services/github_graphql_sync.py` - Added logging to `_process_files()`
- `apps/integrations/tasks.py` - Fixed 4 locations:
  - Line 159: `_sync_with_graphql_or_rest()`
  - Line 210: `_sync_incremental_with_graphql_or_rest()`
  - Line 483: `_sync_members_with_graphql_or_rest()`
  - Line 1618: `_fetch_pr_core_data_with_graphql_or_rest()`
  - Line 2131: Added `llm_summary_version` to LLM save
- `apps/integrations/tests/test_two_phase_sync.py` - Updated tests for new pattern

## Phase 1: Prompt Fix (Anti-Bias Rules)

**Effort: Small | Priority: High**

- [ ] Edit `apps/metrics/prompts/templates/sections/tech_detection.jinja2`
  - [ ] Add "Critical Rules for Tech Detection" section
  - [ ] Add rule: DO NOT infer from org/repo names
  - [ ] Add rule: Return empty arrays when no file evidence
  - [ ] Add example showing "railsware" ≠ Rails
- [ ] Update `PROMPT_VERSION` in `apps/metrics/services/llm_prompts.py`
  - [ ] Bump from `8.1.0` to `8.2.0`
- [ ] Add golden test case in `apps/metrics/prompts/golden_tests.py`
  - [ ] Test: PR with "railsware" org, no files → empty tech arrays
- [ ] Run validation: `make export-prompts && npx promptfoo eval`
- [ ] All tests pass

## Phase 2: Add Logging for Empty Nested Data

**Effort: Small | Priority: Medium**

- [x] Edit `apps/integrations/services/github_graphql_sync.py`
  - [x] In `_process_files()` add debug logging
  - [x] Add warning log when files=0 but additions+deletions>0
  - [x] Include PR number, additions, deletions in log
- [ ] Add test for the new logging
- [ ] Run: `.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py -v`

## Phase 3: Add Language Fetch to Onboarding

**Effort: Medium | Priority: Medium**

- [ ] Edit `apps/integrations/onboarding_pipeline.py`
  - [ ] Import `refresh_repo_languages_task`
  - [ ] Add to Phase 1 pipeline after `sync_historical_data_task`
  - [ ] Use `group()` to run for all repos in parallel
- [ ] Update tests in `apps/integrations/tests/test_onboarding_pipeline.py`
- [ ] Run: `.venv/bin/pytest apps/integrations/tests/test_onboarding_pipeline.py -v`

## Phase 4: Re-analyze Affected PRs

**Effort: Small | Priority: Low (after fixes deployed)**

- [ ] Re-run LLM analysis for team 150 PRs
  - [ ] Command: `.venv/bin/python manage.py run_llm_analysis --team 150`
- [ ] Verify PR #2408 now has correct classification
- [ ] Verify all PRs have correct tech categories

## Validation Checklist

- [ ] Fresh sync saves files for all PRs
- [ ] Repo languages fetched during onboarding
- [ ] PR #2408 classified correctly (Go, not Rails)
- [x] All integration tests pass (103 passed)
- [ ] All prompt tests pass

---

## Quick Reference

### Test Commands

```bash
# Prompt validation
make export-prompts && npx promptfoo eval

# Unit tests
.venv/bin/pytest apps/integrations/tests/test_github_graphql_sync.py -v
.venv/bin/pytest apps/integrations/tests/test_onboarding_pipeline.py -v
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Full test suite
make test
```

### Key Files to Edit

| File | Section |
|------|---------|
| `apps/metrics/prompts/templates/sections/tech_detection.jinja2` | Add anti-bias rules |
| `apps/metrics/services/llm_prompts.py` | PROMPT_VERSION |
| `apps/metrics/prompts/golden_tests.py` | New test case |
| `apps/integrations/services/github_graphql_sync.py` | Add logging |
| `apps/integrations/onboarding_pipeline.py` | Add language fetch |

### Database Cleanup (if needed)

```sql
-- Delete team 150 nested data for fresh test
DELETE FROM metrics_prfile WHERE team_id = 150;
DELETE FROM metrics_prreview WHERE team_id = 150;
DELETE FROM metrics_commit WHERE team_id = 150;
-- Keep PRs for comparison
```

## Notes

### Why Files Weren't Saved - CONFIRMED

The `asyncio.run()` in Celery workers creates a new event loop that breaks Django's `@sync_to_async` thread context management. Database operations execute but don't commit properly.

**Key insight**: The code worked perfectly when called manually (outside Celery) but silently failed inside Celery workers.

### GitHub Resource Limits (Red Herring)

Initially suspected GitHub's September 2025 resource limits caused partial results, but direct API testing proved this was NOT the issue. The API returns files correctly.
