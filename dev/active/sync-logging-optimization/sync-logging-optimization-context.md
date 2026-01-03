# Sync Logging Optimization - Context

## Key Files to Modify

### New Files to Create

| File | Purpose |
|------|---------|
| `apps/utils/sync_logger.py` | Structured logging helper with timing context managers |
| `apps/utils/tests/test_sync_logger.py` | Unit tests for sync logger |

### Files to Instrument

| File | Lines | Changes |
|------|-------|---------|
| `apps/integrations/onboarding_pipeline.py` | ~450 | Add pipeline event logging |
| `apps/integrations/tasks.py` | ~2500 | Add task/repo event logging |
| `apps/integrations/services/github_graphql.py` | ~300 | Add API call logging |
| `apps/integrations/services/github_graphql_sync.py` | ~900 | Add sync/PR logging |
| `apps/integrations/services/github_rate_limit.py` | ~100 | Add rate limit logging |

### Test Files to Create/Update

| File | Purpose |
|------|---------|
| `apps/utils/tests/test_sync_logger.py` | New - logger unit tests |
| `apps/integrations/tests/test_sync_logging.py` | New - integration tests |

---

## Key Decisions

### 1. Use `structlog` vs Standard Logging

**Decision**: Use standard `logging` module with custom formatter for JSON output

**Rationale**:
- Codebase already uses standard logging everywhere
- Adding structlog as dependency adds complexity
- Can achieve same result with custom JSON formatter
- Easier to maintain consistency

### 2. Log Level Strategy

| Event Type | Level | Rationale |
|------------|-------|-----------|
| Pipeline start/end | INFO | Important milestones |
| API calls | DEBUG | High volume, only needed for debugging |
| Rate limits | INFO/WARNING | Operationally important |
| Errors | ERROR | Always visible |
| Per-PR progress | DEBUG | Very high volume |

### 3. Context Injection Pattern

```python
# Use thread-local context for team_id/repo_id/task_id
# Avoids passing context through all function signatures

from apps.utils.sync_logger import sync_context

with sync_context(team_id=123, repo_id=456, task_id="abc"):
    # All log calls in this block get context automatically
    logger.info("sync.repo.started")
```

### 4. Timing Pattern

```python
from apps.utils.sync_logger import timed_operation

with timed_operation("sync.api.graphql", query_name="fetch_prs"):
    result = await client.execute(query)
# Automatically logs duration_ms when block exits
```

---

## Dependencies

### Python Packages (Already Installed)
- `logging` - Standard library
- `json` - Standard library
- `time` - Standard library
- `contextvars` - Standard library (Python 3.7+)

### No New Dependencies Required

---

## Current Logging Patterns (Reference)

### tasks.py (current)
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"Starting sync for repository: {tracked_repo.full_name}")
logger.warning(f"Sync failed for {tracked_repo.full_name}, retrying...")
```

### onboarding_pipeline.py (current)
```python
logger.info(f"Pipeline status updated: team={team_id}, status={status}")
logger.error(f"Pipeline failed for team {team_id}: {error_message}")
```

### github_graphql_sync.py (current)
```python
logger.debug(f"Syncing PR #{pr_number} for {repo_name}")
logger.error(f"Error processing PR {pr_number}: {e}")
```

---

## Sync Pipeline Flow (Reference)

```
User selects repos in onboarding
  ↓
start_onboarding_pipeline(team_id, repo_ids)
  ↓
start_phase1_pipeline() [Celery chain]
  ├→ update_pipeline_status(syncing)          ← LOG: sync.pipeline.started
  ├→ sync_historical_data_task(days_back=30)  ← LOG: sync.repo.* events
  │   └→ OnboardingSyncService.sync_repository()
  │       └→ sync_repository_history_graphql() ← LOG: sync.api.* events
  ├→ update_pipeline_status(llm_processing)   ← LOG: sync.pipeline.phase_changed
  ├→ run_llm_analysis_batch()
  ├→ update_pipeline_status(computing_metrics)
  ├→ aggregate_team_weekly_metrics_task()
  ├→ update_pipeline_status(phase1_complete)  ← LOG: sync.pipeline.completed
  └→ dispatch_phase2_pipeline()               ← LOG: sync.pipeline.started (phase 2)
```

---

## Environment Variables (Reference)

No new environment variables needed. Logging configuration uses existing Django settings.

Current logging config location: `tformance/settings.py` (`LOGGING` dict)

---

## Related PRDs/Docs

- `prd/IMPLEMENTATION-PLAN.md` - Phase 2 includes GitHub integration
- `prd/ARCHITECTURE.md` - System architecture overview
- `CLAUDE.md` - Coding guidelines (function-based views, TDD, etc.)

---

## Constraints

### GitHub API (MUST FOLLOW)
- No parallel API calls with same OAuth token
- Sequential requests only
- Respect rate limit headers
- Current implementation already follows this

### TDD Workflow (MUST FOLLOW)
1. Write failing test (RED)
2. Implement minimum code (GREEN)
3. Refactor if needed (REFACTOR)
4. Repeat for each function

---

## Open Questions (Resolved)

| Question | Resolution |
|----------|------------|
| structlog vs logging? | Use standard logging with JSON formatter |
| What level for API calls? | DEBUG (high volume) |
| Log to file or stdout? | Stdout (container-friendly) |
| Add log aggregation? | Not in this phase (future) |

---

*Last Updated: 2026-01-03*
