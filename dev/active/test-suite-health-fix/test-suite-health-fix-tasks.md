# Test Suite Health Fix - Tasks

**Last Updated:** 2026-01-12
**Claude Plan Reference:** `/Users/yanchuk/.claude/plans/streamed-leaping-flurry.md`

---

## Phase 0: Quick Wins (4 tests)

### Schema Evolution Fixes
- [x] **0.1** Add 12 models to `TEAM_MODELS` in `scripts/tests/test_lint_team_isolation.py`
- [x] **0.2** Add `view_copilot_usage` to expected enum in `apps/metrics/tests/services/test_insight_llm.py`
- [x] **0.3** Check/create pending migration for teams (not needed - already exists)

### Verification
- [ ] **0.4** Run: `.venv/bin/pytest scripts/tests/test_lint_team_isolation.py -v -n 0 --reuse-db`
- [ ] **0.5** Run: `.venv/bin/pytest apps/metrics/tests/services/test_insight_llm.py -v -n 0 --reuse-db`

---

## Phase 1: Production Bug Fixes (4+ tests)

### Groq Batch Serialization
- [ ] **1.1** Read `apps/integrations/services/groq_batch.py` to understand `_LazyPrompt` issue
- [ ] **1.2** Fix JSON serialization - convert lazy prompts to strings before dump
- [ ] **1.3** Run: `.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v -n 0 --reuse-db`

### Team Context Mock Issue
- [ ] **1.4** Investigate `apps/onboarding/tests/test_team_context.py` MagicMock issue
- [ ] **1.5** Fix task ID return value
- [ ] **1.6** Run: `.venv/bin/pytest apps/onboarding/tests/test_team_context.py -v -n 0 --reuse-db`

---

## Phase 2: Re-exports Approach (22 tests)

### Add Re-exports
- [ ] **2.1** Read `apps/integrations/tasks.py` to find import section
- [ ] **2.2** Add re-export: `from apps.metrics.services.survey_service import create_pr_survey  # noqa: F401`
- [ ] **2.3** Add re-export: `from apps.integrations.services.jira_sync import sync_project_issues  # noqa: F401`
- [ ] **2.4** Add any other missing re-exports identified by test failures

### Verification
- [ ] **2.5** Run: `.venv/bin/pytest apps/integrations/tests/test_slack_tasks.py -v -n 0 --reuse-db`
- [ ] **2.6** Run: `.venv/bin/pytest apps/integrations/tests/test_jira_tasks.py -v -n 0 --reuse-db`

---

## Phase 3: Template Path Fixes (16 tests)

### Fix Template Paths
- [ ] **3.1** Read `apps/metrics/tests/test_copilot_template.py` setUp method
- [ ] **3.2** Update template path to `insight/sections/copilot_metrics.jinja2`
- [ ] **3.3** Read `apps/metrics/tests/test_copilot_jinja2_template.py` setUp method
- [ ] **3.4** Update template path to `insight/sections/copilot_metrics.jinja2`

### Apply setUpTestData (Optional Optimization)
- [ ] **3.5** Convert `test_copilot_template.py` to use `@classmethod setUpTestData`
- [ ] **3.6** Convert `test_copilot_jinja2_template.py` to use `@classmethod setUpTestData`

### Verification
- [ ] **3.7** Run: `.venv/bin/pytest apps/metrics/tests/test_copilot_template.py -v -n 0 --reuse-db`
- [ ] **3.8** Run: `.venv/bin/pytest apps/metrics/tests/test_copilot_jinja2_template.py -v -n 0 --reuse-db`

---

## Phase 4: Skip TDD Tests (11 tests)

### Add Skip Markers
- [ ] **4.1** Read `apps/metrics/tests/test_github_authenticated_fetcher.py` to find `TestGitHubFetcherCheckpointing`
- [ ] **4.2** Add `@pytest.mark.skip(reason="Checkpointing feature not implemented")` to class
- [ ] **4.3** Verify skip marker is applied to all 11 checkpointing tests

### Verification
- [ ] **4.4** Run: `.venv/bin/pytest apps/metrics/tests/test_github_authenticated_fetcher.py -v -n 0 --reuse-db`
- [ ] **4.5** Confirm 11 tests show as SKIPPED

---

## Phase 5: Pipeline Tests for Signals (5+ tests)

### Understand Current Architecture
- [ ] **5.1** Read `apps/integrations/tests/test_two_phase_pipeline.py` to understand test structure
- [ ] **5.2** Read signal handlers to understand new architecture
- [ ] **5.3** Identify what tests should verify

### Rewrite Tests
- [ ] **5.4** Update `test_phase1_ends_with_phase1_complete_status` for signals
- [ ] **5.5** Update `test_phase2_ends_with_complete_status` for signals
- [ ] **5.6** Update `test_phase1_dispatches_phase2` for signals
- [ ] **5.7** Update remaining pipeline tests

### Verification
- [ ] **5.8** Run: `.venv/bin/pytest apps/integrations/tests/test_two_phase_pipeline.py -v -n 0 --reuse-db`

---

## Phase 6: Remaining Fixes (~30 tests)

### Jira Metrics (6 tests)
- [ ] **6.1** Investigate `apps/metrics/tests/services/test_jira_metrics.py` failures
- [ ] **6.2** Fix assertion mismatches
- [ ] **6.3** Run: `.venv/bin/pytest apps/metrics/tests/services/test_jira_metrics.py -v -n 0 --reuse-db`

### Quick Sync Tasks (6 tests)
- [ ] **6.4** Investigate `apps/integrations/tests/test_quick_sync_task.py` failures
- [ ] **6.5** Fix task dispatch changes
- [ ] **6.6** Run: `.venv/bin/pytest apps/integrations/tests/test_quick_sync_task.py -v -n 0 --reuse-db`

### Sync Logging (4 tests)
- [ ] **6.7** Investigate `apps/integrations/tests/test_sync_logging.py` failures
- [ ] **6.8** Fix logger name changes
- [ ] **6.9** Run: `.venv/bin/pytest apps/integrations/tests/test_sync_logging.py -v -n 0 --reuse-db`

### Other Miscellaneous
- [ ] **6.10** Fix remaining failures (investigate as encountered)

---

## Final Verification

- [ ] **7.1** Run full test suite: `.venv/bin/pytest --reuse-db -q`
- [ ] **7.2** Verify: 5,458 passed, 11 skipped, 0 failed
- [ ] **7.3** Run `make test` to confirm CI would pass
- [ ] **7.4** Update this task file with completion status

---

## Acceptance Criteria

| Criteria | Status |
|----------|--------|
| All Phase 0-6 tasks complete | |
| 5,458 tests passing | |
| 11 tests skipped (checkpointing) | |
| 0 tests failing | |
| Test duration < 90s | |
| No production regressions | |

---

## Notes

- Each phase should be verified before moving to next
- If a fix causes new failures, investigate before continuing
- Update context.md with any new discoveries
- Reference Claude plan for detailed rationale
