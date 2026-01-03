# Sync Logging Optimization - Implementation Plan

## Executive Summary

Add comprehensive structured logging to the GitHub sync pipeline to enable debugging, bottleneck identification, and operational visibility during the alpha development period.

**Goal**: Full visibility into sync operations with JSON-structured logs for easy parsing and analysis.

**Scope**: Step 1 of the broader sync optimization plan (logging first, then optimize based on data).

---

## Current State Analysis

### Existing Logging
- Uses standard Python `logging` module with f-string messages
- Inconsistent event naming (`f"Starting sync for repository: {name}"`)
- No structured fields for filtering/querying
- No timing information for API calls or DB writes
- No rate limit visibility in logs

### Current Log Examples (tasks.py)
```python
logger.info(f"Starting sync for repository: {tracked_repo.full_name}")
logger.warning(f"Sync failed for {tracked_repo.full_name}, retrying in {countdown}s: {exc}")
```

### Pain Points
1. Can't filter logs by team_id, repo_id, or task_id easily
2. No timing data to identify slow operations
3. Rate limit status not logged (blind to API quota)
4. Hard to trace a single sync through multiple files/functions

---

## Proposed Future State

### Structured Logging with `structlog`
```python
logger.info(
    "sync.repo.started",
    team_id=123,
    repo_id=456,
    full_name="org/repo",
    task_id="abc-123"
)
```

### JSON Output (for log aggregation)
```json
{
  "timestamp": "2026-01-03T16:30:00Z",
  "level": "info",
  "event": "sync.repo.started",
  "team_id": 123,
  "repo_id": 456,
  "full_name": "org/repo",
  "task_id": "abc-123"
}
```

### Event Naming Convention
- `sync.pipeline.*` - Onboarding pipeline events
- `sync.repo.*` - Per-repository events
- `sync.api.*` - GitHub API call events
- `sync.db.*` - Database write events
- `sync.pr.*` - Per-PR processing events

---

## Implementation Phases

### Phase 1: Create Sync Logger Module (TDD)

**File**: `apps/utils/sync_logger.py`

Create a reusable structured logging helper:
- Context managers for timing
- Consistent field injection (team_id, repo_id, task_id)
- JSON formatting for production

### Phase 2: Instrument Onboarding Pipeline (TDD)

**File**: `apps/integrations/onboarding_pipeline.py`

Add logging for:
- Pipeline start/complete/failed
- Phase transitions (syncing → llm_processing → etc.)
- Phase 2 dispatch

### Phase 3: Instrument Sync Tasks (TDD)

**File**: `apps/integrations/tasks.py`

Add logging for:
- Task start/retry/complete/failed
- Per-repo sync progress
- Error context on failures

### Phase 4: Instrument GraphQL Sync (TDD)

**Files**:
- `apps/integrations/services/github_graphql.py` - Client logging
- `apps/integrations/services/github_graphql_sync.py` - Sync service logging

Add logging for:
- Every GraphQL query with timing
- Rate limit checks
- Per-PR processing
- DB write batches

### Phase 5: Integration Testing & QA

- Verify existing alpha-qa-backlog fixes still work
- Run E2E smoke tests
- Test with real GitHub org sync
- Verify log output format

---

## Detailed Event Catalog

| Event | Level | Fields | When |
|-------|-------|--------|------|
| `sync.pipeline.started` | INFO | team_id, repos_count, phase, task_id | Pipeline start |
| `sync.pipeline.phase_changed` | INFO | team_id, phase, previous_phase | Phase transition |
| `sync.pipeline.completed` | INFO | team_id, repos_synced, total_prs, duration_sec | Success |
| `sync.pipeline.failed` | ERROR | team_id, phase, error_type, error_msg | Failure |
| `sync.repo.started` | INFO | team_id, repo_id, full_name | Repo sync start |
| `sync.repo.progress` | DEBUG | team_id, repo_id, prs_done, prs_total, pct | Every 10 PRs |
| `sync.repo.completed` | INFO | team_id, repo_id, prs_synced, duration_sec | Repo sync end |
| `sync.repo.failed` | ERROR | team_id, repo_id, error_type, error_msg | Repo sync fail |
| `sync.api.graphql` | DEBUG | query_name, points_cost, duration_ms, status | Each GraphQL call |
| `sync.api.rest` | DEBUG | endpoint, duration_ms, status_code | Each REST call |
| `sync.api.rate_limit` | INFO | remaining, limit, reset_at, will_wait | Rate limit check |
| `sync.api.rate_wait` | WARNING | wait_seconds, reset_at | Waiting for reset |
| `sync.db.write` | DEBUG | entity_type, created, updated, duration_ms | DB batch write |
| `sync.pr.processed` | DEBUG | pr_id, pr_number, reviews, commits, files | Per-PR |
| `sync.task.retry` | WARNING | task_name, retry_count, countdown, error | Task retry |

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Log volume too high | Medium | Low | Use DEBUG level for high-frequency events |
| Performance impact | Low | Low | Structlog is fast, logging is async |
| Breaking existing tests | Medium | Medium | Add logging incrementally with tests |
| JSON output breaks log viewers | Low | Low | Keep text format in dev, JSON in prod |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Debug time for sync failures | 30+ min | 5 min |
| Visibility into rate limits | None | Full |
| Ability to trace single sync | Hard | Easy (by task_id) |
| Time spent per operation | Unknown | Measured |

---

## GitHub API Best Practices (Constraints)

**MUST FOLLOW**:
- NO parallel API calls with same token
- Sequential requests only per OAuth token
- Respect `X-RateLimit-Remaining` header
- Wait for `X-RateLimit-Reset` when limit reached

These constraints inform logging placement - we log timing because we can't parallelize.

---

## QA Workflow

After implementation:
1. Run unit tests: `make test`
2. Run E2E smoke: `make e2e-smoke`
3. Manual QA: Verify alpha-qa-backlog fixes
4. Test real sync: Connect GitHub org, verify logs
5. Review log output format

---

*Last Updated: 2026-01-03*
