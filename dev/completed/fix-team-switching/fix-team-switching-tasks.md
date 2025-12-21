# Fix Team Switching - Tasks

**Last Updated:** 2025-12-21

## Phase 1: TDD Red Phase - Write Failing Tests

- [x] **1.1** Create test file `apps/teams/tests/test_switch_team.py`
- [x] **1.2** Write `test_switch_team_success`
- [x] **1.3** Write `test_switch_team_updates_session`
- [x] **1.4** Write `test_switch_team_not_member`
- [x] **1.5** Write `test_switch_team_unauthenticated`
- [x] **1.6** Write `test_switch_team_nonexistent_team`
- [x] **1.7** Verify all tests fail

## Phase 2: TDD Green Phase - Implement View

- [x] **2.1** Add URL pattern to `apps/teams/urls.py`
- [x] **2.2** Create `switch_team` view in `apps/teams/views/membership_views.py`
- [x] **2.3** Export view from `apps/teams/views/__init__.py` (auto-exported via wildcard)
- [x] **2.4** Run tests - all should pass

## Phase 3: Update Dashboard URL

- [x] **3.1** Write test for `dashboard_url` property
- [x] **3.2** Update `Team.dashboard_url` in `apps/teams/models.py`
- [x] **3.3** Run full team test suite (59 tests pass)

## Phase 4: Verification

- [x] **4.1** Run all tests - 59 team tests pass
- [x] **4.2** Manual E2E test - User confirmed "now it works"
- [x] **4.3** Clean up dev-docs

## Summary

| Phase | Tasks | Status |
|-------|-------|--------|
| Phase 1: Red | 7 | Complete |
| Phase 2: Green | 4 | Complete |
| Phase 3: Dashboard URL | 3 | Complete |
| Phase 4: Verification | 3 | Complete |
| **Total** | **17** | **17 Complete** |

## Commits

1. `9cf184e` - Fix team switching and badge truncation
2. `029c3b6` - Fix onboarding background and text-warning contrast for light theme
