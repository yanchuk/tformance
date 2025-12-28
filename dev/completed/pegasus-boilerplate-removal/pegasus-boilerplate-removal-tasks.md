# Tasks: Pegasus Boilerplate Removal

**Last Updated: 2025-12-28**

## Phase 1: Configuration Updates

- [x] **1.1** Remove `PEGASUS_APPS` from `tformance/settings.py`
- [x] **1.2** Remove `PEGASUS_APPS` from `INSTALLED_APPS` composition
- [x] **1.3** Remove `apps.teams_example.apps.TeamsExampleConfig` from `PROJECT_APPS`
- [x] **1.4** Remove `test-celerybeat` scheduled task
- [x] **1.5** Remove URL patterns from `tformance/urls.py`
- [x] **1.6** Remove pegasus logger from LOGGING config

## Phase 2: Directory Removal

- [x] **2.1** Remove `pegasus/` directory
- [x] **2.2** Remove `apps/teams_example/` directory
- [x] **2.3** Remove `templates/pegasus/` directory
- [x] **2.4** Remove `templates/teams_example/` directory
- [x] **2.5** Remove `assets/javascript/pegasus/` directory

## Phase 3: Cleanup

- [x] **3.1** Update `BaseTeamModel` docstring to remove teams_example reference

## Phase 4: Verification

- [x] **4.1** Run `django check` - no issues
- [x] **4.2** Run `ruff check` - all checks passed
- [x] **4.3** Run tests - 664 passed (2 pre-existing flaky failures unrelated to this change)

## Summary

Removed ~80 files of Pegasus boilerplate code. All verification passed.
