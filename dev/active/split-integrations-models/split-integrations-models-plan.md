# Split Integrations Models Refactoring Plan

**Last Updated:** 2026-01-10
**Status:** IN PROGRESS

## Executive Summary

Refactor the oversized `apps/integrations/models.py` (809 lines) into domain-specific model files to improve maintainability, readability, and adherence to the 200-300 line guideline.

## Current State Analysis

### File Statistics
- **Current file:** `apps/integrations/models.py` (809 lines)
- **Contains 7 models** spanning 4 domains

### Models in Current File

| Model | Lines | Domain | Dependencies |
|-------|-------|--------|--------------|
| `IntegrationCredential` | ~85 | Core | BaseTeamModel |
| `GitHubIntegration` | ~95 | GitHub | IntegrationCredential |
| `TrackedRepository` | ~180 | GitHub | GitHubIntegration, GitHubAppInstallation |
| `JiraIntegration` | ~60 | Jira | IntegrationCredential |
| `TrackedJiraProject` | ~80 | Jira | JiraIntegration |
| `SlackIntegration` | ~100 | Slack | IntegrationCredential |
| `GitHubAppInstallation` | ~180 | GitHub | Team only |

## Proposed Future State

```
apps/integrations/models/
├── __init__.py          # Re-exports all models (~50 lines)
├── credentials.py       # IntegrationCredential (~85 lines)
├── github.py            # GitHubIntegration, TrackedRepository, GitHubAppInstallation (~455 lines)
├── jira.py              # JiraIntegration, TrackedJiraProject (~140 lines)
└── slack.py             # SlackIntegration (~100 lines)
```

### Why This Split?

1. **Domain cohesion**: GitHub models grouped, Jira models grouped, Slack separate
2. **Dependency order**: `credentials.py` → `github.py`/`jira.py`/`slack.py`
3. **Backward compatibility**: `__init__.py` re-exports preserve all existing imports
4. **No migrations needed**: Pure Python refactoring, no schema changes

## Import Dependency Graph

```
IntegrationCredential (credentials.py)
    ↓
GitHubIntegration ← uses credential
    ↓
GitHubAppInstallation ← independent (Team only)
    ↓
TrackedRepository ← uses both GitHubIntegration and GitHubAppInstallation

IntegrationCredential (credentials.py)
    ↓
JiraIntegration ← uses credential
    ↓
TrackedJiraProject ← uses JiraIntegration

IntegrationCredential (credentials.py)
    ↓
SlackIntegration ← uses credential
```

## Implementation Phases

### Phase 1: TDD Baseline (30 min)
- Run existing model tests to establish passing baseline
- Document any pre-existing test failures

### Phase 2: Create Model Files (1 hour)

#### 2.1 Create `credentials.py`
- Move `IntegrationCredential` class
- Add proper imports (BaseTeamModel, CustomUser, EncryptedTextField)

#### 2.2 Create `github.py`
- Move `GitHubIntegration`, `TrackedRepository`, `GitHubAppInstallation`
- Import `IntegrationCredential` from `.credentials`
- Note: Order matters - GitHubAppInstallation before TrackedRepository

#### 2.3 Create `jira.py`
- Move `JiraIntegration`, `TrackedJiraProject`
- Import `IntegrationCredential` from `.credentials`

#### 2.4 Create `slack.py`
- Move `SlackIntegration`
- Import `IntegrationCredential` from `.credentials`

#### 2.5 Create `__init__.py`
- Re-export all models for backward compatibility
- Add docstring documenting module structure

### Phase 3: Verification (30 min)
- Run linting: `make ruff`
- Run team isolation check: `make lint-team-isolation`
- Run model tests
- Verify circular imports with Django shell

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Circular imports | Medium | High | Follow dependency order: credentials → github/jira/slack |
| Missing re-exports | Medium | High | Update `__all__` list, run import tests |
| Test failures | Low | Medium | TDD baseline before changes |
| Migration issues | N/A | N/A | No schema changes |
| Import breaks | Low | Medium | `__init__.py` re-exports maintain compatibility |

## Success Metrics

- [ ] All existing tests pass (especially `test_models.py`)
- [ ] No circular import errors
- [ ] Linting passes (`make ruff`, `make lint-team-isolation`)
- [ ] All 30+ files importing from `apps.integrations.models` work unchanged
- [ ] github.py stays under 500 lines (largest domain file)

## Verification Commands

```bash
# Quick verification - model tests
.venv/bin/pytest apps/integrations/tests/test_models.py -v --tb=short

# Full verification
make test
make ruff
make lint-team-isolation

# Import test
.venv/bin/python manage.py shell -c "from apps.integrations.models import IntegrationCredential, GitHubIntegration, TrackedRepository, JiraIntegration, TrackedJiraProject, SlackIntegration, GitHubAppInstallation; print('OK')"
```

## Files to Modify

### New Files
- `apps/integrations/models/__init__.py`
- `apps/integrations/models/credentials.py`
- `apps/integrations/models/github.py`
- `apps/integrations/models/jira.py`
- `apps/integrations/models/slack.py`

### Files to Delete
- `apps/integrations/models.py` (after moving to directory)

### External Dependencies (unchanged due to __init__.py re-exports)
- 30+ files import from `apps.integrations.models` - all will work unchanged
