# Split Integrations Models - Tasks

**Last Updated:** 2026-01-10
**Status:** COMPLETE

## Phase 1: TDD Baseline

- [x] Run full test suite to establish baseline (90 tests passed)
- [x] Run model-specific tests: `pytest apps/integrations/tests/test_models.py -v`
- [x] Document any pre-existing failures (none)

## Phase 2: Create Model Files

### 2.1 Create Directory Structure
- [x] Create `apps/integrations/models/` directory
- [x] Move original `models.py` to backup (or let git track)

### 2.2 Create credentials.py
- [x] Create file with IntegrationCredential class (~85 lines)
- [x] Add imports: BaseTeamModel, CustomUser, EncryptedTextField

### 2.3 Create github.py
- [x] Create file with GitHubIntegration, TrackedRepository, GitHubAppInstallation (~455 lines)
- [x] Add import: `from .credentials import IntegrationCredential`
- [x] Order: GitHubIntegration → GitHubAppInstallation → TrackedRepository

### 2.4 Create jira.py
- [x] Create file with JiraIntegration, TrackedJiraProject (~140 lines)
- [x] Add import: `from .credentials import IntegrationCredential`

### 2.5 Create slack.py
- [x] Create file with SlackIntegration (~100 lines)
- [x] Add import: `from .credentials import IntegrationCredential`

### 2.6 Create __init__.py
- [x] Re-export all models for backward compatibility
- [x] Add docstring documenting module structure
- [x] Define `__all__` list

## Phase 3: Verification

- [x] Run linting: `make ruff` - All checks passed
- [x] Run team isolation check: `make lint-team-isolation` - Passed
- [x] Run model tests: `pytest apps/integrations/tests/test_models.py -v` - 90 passed
- [x] Verify no circular imports with Django shell - Success
- [x] Run full integrations test suite - Passed

## Completion Checklist

- [x] All tests pass (90/90)
- [x] No linting errors
- [x] No circular imports
- [x] Original models.py deleted
- [x] Documentation updated

## Files Created

| File | Lines | Content |
|------|-------|---------|
| `models/__init__.py` | 27 | Re-exports all models |
| `models/credentials.py` | 96 | IntegrationCredential |
| `models/github.py` | 481 | GitHubIntegration, GitHubAppInstallation, TrackedRepository |
| `models/jira.py` | 166 | JiraIntegration, TrackedJiraProject |
| `models/slack.py` | 112 | SlackIntegration |
