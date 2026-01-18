# Tasks: GitHub Personal Account Sync Fix

**Last Updated:** 2026-01-18

## Phase 1: Add `sync_single_user_as_member()` Function (TDD)

### RED: Write Failing Tests

- [ ] **T1.1** Test: creates TeamMember for new user
  - **File:** `apps/integrations/tests/test_member_sync.py`
  - **Effort:** S
  - **Acceptance:** Test fails with `AttributeError: module has no attribute 'sync_single_user_as_member'`

- [ ] **T1.2** Test: updates existing member if username changed
  - **File:** `apps/integrations/tests/test_member_sync.py`
  - **Effort:** S
  - **Depends on:** T1.1

- [ ] **T1.3** Test: returns unchanged when no changes
  - **File:** `apps/integrations/tests/test_member_sync.py`
  - **Effort:** S
  - **Depends on:** T1.1

- [ ] **T1.4** Test: handles API error gracefully (returns failed=1)
  - **File:** `apps/integrations/tests/test_member_sync.py`
  - **Effort:** S
  - **Depends on:** T1.1

- [ ] **T1.5** Test: handles private email (None)
  - **File:** `apps/integrations/tests/test_member_sync.py`
  - **Effort:** S
  - **Depends on:** T1.1

### GREEN: Implement Minimal Code

- [ ] **T1.6** Implement `sync_single_user_as_member()` function
  - **File:** `apps/integrations/services/member_sync.py`
  - **Effort:** M
  - **Depends on:** T1.1-T1.5
  - **Acceptance:** All tests from T1.1-T1.5 pass

### REFACTOR: Clean Up

- [ ] **T1.7** Add docstring and type hints
  - **File:** `apps/integrations/services/member_sync.py`
  - **Effort:** S
  - **Depends on:** T1.6

---

## Phase 2: Update Task Routing (TDD)

### RED: Write Failing Tests

- [ ] **T2.1** Test: task routes to `sync_single_user_as_member` for `account_type="User"`
  - **File:** `apps/integrations/tests/test_github_sync_tasks.py` (or existing test file)
  - **Effort:** M
  - **Depends on:** T1.6
  - **Acceptance:** Test fails with assertion error (calls wrong function)

- [ ] **T2.2** Test: task routes to `sync_github_members` for `account_type="Organization"`
  - **File:** `apps/integrations/tests/test_github_sync_tasks.py`
  - **Effort:** S
  - **Depends on:** T2.1

### GREEN: Implement Routing

- [ ] **T2.3** Add account_type check in `sync_github_app_members_task`
  - **File:** `apps/integrations/_task_modules/github_sync.py`
  - **Lines:** ~790-796
  - **Effort:** S
  - **Depends on:** T2.1-T2.2
  - **Acceptance:** Both routing tests pass

---

## Phase 3: Verify and Deploy

- [ ] **T3.1** Run full test suite locally
  - **Command:** `make test`
  - **Effort:** S
  - **Depends on:** T2.3
  - **Acceptance:** All tests pass, no regressions

- [ ] **T3.2** Deploy to Heroku
  - **Command:** `git push heroku main`
  - **Effort:** S
  - **Depends on:** T3.1

- [ ] **T3.3** Verify fix with new personal account install
  - **Steps:** Create new team → Install GitHub App on personal account → Verify sync completes
  - **Effort:** M
  - **Depends on:** T3.2
  - **Acceptance:** Sync completes all 5 steps (Members → PRs → AI Analysis → Metrics → Insights)

- [ ] **T3.4** Re-sync any stuck personal account installations
  - **Command:** Heroku shell command (see context.md)
  - **Effort:** S
  - **Depends on:** T3.2

---

## Summary

| Phase | Tasks | Effort |
|-------|-------|--------|
| Phase 1 (Function) | T1.1-T1.7 | 7 tasks, ~30 min |
| Phase 2 (Routing) | T2.1-T2.3 | 3 tasks, ~15 min |
| Phase 3 (Deploy) | T3.1-T3.4 | 4 tasks, ~20 min |
| **Total** | **14 tasks** | **~1 hour** |

---

## Commands Reference

```bash
# Run specific tests
.venv/bin/pytest apps/integrations/tests/test_member_sync.py -v

# Run all integration tests
.venv/bin/pytest apps/integrations/tests/ -v

# Run full test suite
make test

# Check test coverage
.venv/bin/pytest apps/integrations/tests/test_member_sync.py --cov=apps/integrations/services/member_sync
```
