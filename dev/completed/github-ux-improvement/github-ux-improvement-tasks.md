# GitHub UX Improvement - Tasks

Last Updated: 2025-12-29

## Task Checklist

### Phase 1: TDD RED - Write Failing Tests
- [x] **Task 1.1** - Create test file `test_github_ux_messaging.py`
- [x] **Task 1.2** - Write test: email signup user sees "Connect GitHub"
- [x] **Task 1.3** - Write test: GitHub signup user sees "Grant Repository Access"
- [x] **Task 1.4** - Write test: `has_github_social` context variable is correct
- [x] **Task 1.5** - Verify tests fail (5 failed, 3 passed as expected)

### Phase 2: TDD GREEN - Implement Minimal Code
- [x] **Task 2.1** - Add SocialAccount import to views.py
- [x] **Task 2.2** - Add `has_github_social` to view context
- [x] **Task 2.3** - Update template with conditional heading
- [x] **Task 2.4** - Update template with conditional subtext
- [x] **Task 2.5** - Update template with conditional button text
- [x] **Task 2.6** - Verify tests pass (8/8 pass)

### Phase 3: TDD REFACTOR - Code Quality
- [x] **Task 3.1** - Review code for clarity (no refactoring needed)
- [x] **Task 3.2** - Run full test suite (118/118 onboarding tests pass)
- [x] **Task 3.3** - Run linter (ruff passed)

### Phase 4: Finalize
- [x] **Task 4.1** - Move docs to completed
- [ ] **Task 4.2** - Commit changes

## Progress Summary

| Phase | Status | Tasks Completed |
|-------|--------|-----------------|
| Phase 1: RED | Complete | 5/5 |
| Phase 2: GREEN | Complete | 6/6 |
| Phase 3: REFACTOR | Complete | 3/3 |
| Phase 4: Finalize | In Progress | 1/2 |

**Total Progress: 15/16 tasks completed**

## Dependencies

```
Task 1.5 depends on: 1.1, 1.2, 1.3, 1.4
Task 2.6 depends on: 2.1, 2.2, 2.3, 2.4, 2.5
Phase 2 depends on: Phase 1 complete
Phase 3 depends on: Phase 2 complete
Phase 4 depends on: Phase 3 complete
```

## Notes

- Use Factory Boy for test data creation
- Follow existing test patterns in `apps/onboarding/tests/`
- All template changes should use existing DaisyUI classes
