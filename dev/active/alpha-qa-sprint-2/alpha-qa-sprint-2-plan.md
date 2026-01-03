# Alpha QA Sprint 2 - Implementation Plan

**Last Updated:** 2026-01-03

## Executive Summary

This sprint addresses 8 open issues from alpha QA testing, focusing on critical onboarding pipeline bugs that block new user activation. Priority is fixing the P0 blocker (A-027) that prevents LLM processing after sync, followed by UI/UX issues in the sync flow.

## Current State Analysis

### Backlog Status
- **Resolved:** 19 issues (A-001 through A-019)
- **Open:** 8 issues (A-020 through A-027)
- **Blockers:** 1 (A-027 - Pipeline stuck at llm_processing)

### Critical Path Issues
The onboarding pipeline has a critical failure point:
1. User connects GitHub ✅
2. User selects repositories ✅
3. Sync starts and completes ✅
4. LLM processing never runs ❌ (A-027)
5. User stuck at "llm_processing" status indefinitely

### Root Causes Identified
1. **A-027**: LLM task returns error dict instead of raising exception
2. **A-027**: Multiple Celery workers with incompatible pool settings
3. **A-020/A-021/A-026**: Feature flags not checked in all templates
4. **A-022**: Stall detection timer not reset on progress
5. **A-025**: Member sync not in onboarding pipeline

---

## Implementation Phases

### Phase 1: Critical Pipeline Fix (P0)
**Goal:** Fix onboarding pipeline to complete end-to-end

| Task | Issue | Effort | Description |
|------|-------|--------|-------------|
| 1.1 | A-027 | S | Fix LLM task to raise ValueError on missing GROQ_API_KEY |
| 1.2 | A-027 | S | Update test to expect ValueError instead of error dict |
| 1.3 | A-027 | S | Document single Celery worker requirement |
| 1.4 | A-027 | M | Add pipeline stuck detection (15 min timeout) |

### Phase 2: Feature Flag Compliance (P1)
**Goal:** All UI respects ENABLE_JIRA/SLACK_INTEGRATION flags

| Task | Issue | Effort | Description |
|------|-------|--------|-------------|
| 2.1 | A-021 | S | Fix "Continue to Jira" button on sync page |
| 2.2 | A-026 | S | Hide "Enhance your insights" banner when flags off |
| 2.3 | - | S | Audit all templates for missed flag checks |

### Phase 3: Sync Progress UI (P1)
**Goal:** Progress indicators work correctly during sync

| Task | Issue | Effort | Description |
|------|-------|--------|-------------|
| 3.1 | A-020 | M | Fix main progress bar to read sync_progress field |
| 3.2 | A-022 | S | Fix stall detection to reset timer on progress change |
| 3.3 | A-023 | M | Add HTMX polling to sync widget (3s interval) |

### Phase 4: Member Sync (P1)
**Goal:** Team members populated after GitHub connection

| Task | Issue | Effort | Description |
|------|-------|--------|-------------|
| 4.1 | A-025 | M | Debug OAuth callback member sync trigger |
| 4.2 | A-025 | M | Add member sync to onboarding pipeline if needed |

### Phase 5: Investigation (P1)
**Goal:** Understand and fix PR visibility issues

| Task | Issue | Effort | Description |
|------|-------|--------|-------------|
| 5.1 | A-024 | M | Investigate why synced PRs don't appear in list |
| 5.2 | A-024 | S | Check date range filter vs phase timing |

---

## Technical Details

### A-027: LLM Task Fix

**File:** `apps/metrics/tasks.py` (lines 121-132)

```python
# BEFORE (returns dict - doesn't fail chain)
if not api_key:
    logger.error("GROQ_API_KEY environment variable not set")
    return {"error": "GROQ_API_KEY not set"}

# AFTER (raises exception - properly fails chain)
if not api_key:
    logger.error("GROQ_API_KEY environment variable not set")
    raise ValueError("GROQ_API_KEY environment variable not set")
```

**Test Update:** `apps/metrics/tests/test_llm_tasks.py` (line 171-177)

```python
# BEFORE
def test_returns_error_without_api_key(self, mock_sleep):
    """Returns error dict when GROQ_API_KEY not set."""
    with patch.dict("os.environ", {}, clear=True):
        result = run_llm_analysis_batch(team_id=self.team.id, limit=10)
    self.assertIn("error", result)

# AFTER (TDD - expect ValueError)
def test_raises_error_without_api_key(self, mock_sleep):
    """Raises ValueError when GROQ_API_KEY not set."""
    with patch.dict("os.environ", {}, clear=True):
        with self.assertRaises(ValueError) as ctx:
            run_llm_analysis_batch(team_id=self.team.id, limit=10)
    self.assertIn("GROQ_API_KEY", str(ctx.exception))
```

### A-021 & A-026: Feature Flag Checks

**Template Pattern:**
```django
{% if enable_jira_integration or enable_slack_integration %}
  <!-- Show integration prompts -->
{% endif %}
```

**Files to Check:**
- `templates/onboarding/sync.html` - A-021
- `templates/dashboard/components/enhance_insights.html` - A-026
- `templates/dashboard/base.html` - A-026

### A-020: Main Progress Bar

**Investigation:**
- Check `sync_status` API endpoint returns `sync_progress`
- Verify template reads from correct field
- Compare main bar vs per-repo badge data binding

### A-022: Stall Detection

**Fix Pattern:**
```javascript
// Track last progress change time
let lastProgressTime = Date.now();
let lastProgress = 0;

// On each poll
if (newProgress > lastProgress) {
  lastProgressTime = Date.now();
  lastProgress = newProgress;
}

// Stall check
const stalledFor = (Date.now() - lastProgressTime) / 1000;
const showStall = stalledFor > 45 && status === 'syncing';
```

---

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| LLM API rate limits during batch | M | M | Rate limit delay (2.1s) already in place |
| Celery chain breaks again | H | L | Add monitoring, single worker config |
| Template changes break layout | M | L | E2E tests cover sync flow |
| Member sync fails silently | M | M | Add logging at each step |

---

## Success Metrics

1. **Pipeline Completion Rate:** 100% of new users reach dashboard
2. **LLM Processing:** All synced PRs get llm_summary within 10 minutes
3. **Feature Flag Compliance:** Zero Jira/Slack references when flags disabled
4. **Sync UX:** Progress bar updates in real-time, no false stall warnings

---

## Dependencies

- GROQ_API_KEY environment variable set in all environments
- Single Celery worker running (not multiple with different pools)
- Redis running for task queue
- PostgreSQL for model updates

---

## Testing Strategy (TDD)

For each fix:
1. **RED:** Write/update failing test first
2. **GREEN:** Implement minimal fix
3. **REFACTOR:** Clean up if needed
4. **E2E:** Run relevant Playwright tests

**Key Test Files:**
- `apps/metrics/tests/test_llm_tasks.py`
- `apps/integrations/tests/test_github_graphql_sync.py`
- `apps/onboarding/tests/test_views.py`
- `tests/e2e/onboarding.spec.ts`
