# Historical Sync Onboarding - Context

## Key Files Reference

### Existing Infrastructure to Reuse

| File | Purpose | Reuse Strategy |
|------|---------|----------------|
| `apps/metrics/seeding/github_graphql_fetcher.py` | GraphQL PR fetching (10x faster than REST) | Import directly, configure page size |
| `apps/metrics/seeding/real_project_seeder.py` | Orchestration pattern with progress callbacks | Copy pattern for `OnboardingSyncService` |
| `apps/integrations/services/groq_batch.py` | LLM batch processing (v5/v6 prompts) | Use directly for AI detection |
| `apps/integrations/models.py` | TrackedRepository with sync fields | Leverage existing `sync_*` fields |
| `pegasus/apps/examples/tasks.py` | Celery progress bar example | Follow pattern for task structure |
| `templates/pegasus/examples/tasks.html` | Progress bar JS template | Adapt for onboarding UI |

### Files to Create

| File | Purpose |
|------|---------|
| `apps/integrations/services/onboarding_sync.py` | Main `OnboardingSyncService` class |
| `apps/integrations/tasks/historical_sync.py` | Celery task with progress |
| `apps/integrations/signals.py` | Django signals for sync events |
| `templates/onboarding/sync_progress.html` | Progress UI template |
| `apps/onboarding/views.py` | View to start sync and show progress |

### Files to Modify

| File | Change |
|------|--------|
| `apps/integrations/urls.py` | Add sync progress endpoint |
| `tformance/settings.py` | Add `HISTORICAL_SYNC_CONFIG` |
| Onboarding flow templates | Add step 6 for sync progress |

---

## Architectural Decisions

### 1. Synchronous vs Asynchronous LLM Processing

**Decision:** Synchronous polling within Celery task

**Rationale:**
- Onboarding is a one-time operation per team
- User is actively waiting - need real progress feedback
- Groq batch API returns in 30-60s per 100 PRs
- Simpler error handling when sync is in-task

**Alternative considered:** Async with separate polling task
- More complex, harder to track overall progress
- Would need task chaining or callbacks

### 2. Progress Granularity

**Decision:** Three-level progress (repos → PRs → LLM batches)

**Rationale:**
- User sees meaningful progress at each stage
- Can show which repo is being processed
- Matches existing `TrackedRepository.sync_*` fields

### 3. Failure Handling

**Decision:** Continue on repo failure, mark as failed

**Rationale:**
- Don't block entire onboarding if one repo fails
- User can still see data from successful repos
- Failed repos shown in UI, can retry later

### 4. Date Range Calculation

**Decision:** 12 months + beginning of earliest month

**Example:**
- Today: Dec 25, 2025
- 12 months back: Dec 25, 2024
- Start of that month: **Dec 1, 2024**
- Range: Dec 1, 2024 → Dec 25, 2025

**Rationale:**
- Ensures complete month coverage for analytics
- Consistent with trends-benchmarks-dashboard requirements
- Makes monthly aggregations accurate

### 5. Repository Priority

**Decision:** Most PRs in last 6 months first

**Rationale:**
- Users see most relevant data fastest
- Active repos have more value for AI correlation
- Creates faster "aha moment"

---

## Dependencies on Other Tasks

### trends-benchmarks-dashboard

Located at: `dev/active/trends-benchmarks-dashboard/`

**Relationship:**
- Historical sync provides data for trend analysis
- Sync ensures 12+ months of history for benchmarking
- Both use same GraphQL fetcher infrastructure

**Integration points:**
- Historical sync must complete before trends dashboard shows data
- Need `calculate_trend()` functions after sync completes
- Consider triggering trend calculation in `historical_sync_complete` signal

### AI Detection System

**Files:**
- `apps/metrics/services/ai_patterns.py` - Regex patterns
- `apps/metrics/services/llm_prompts.py` - LLM prompts (v6.2.0)
- `apps/metrics/prompts/` - Template system

**Integration:**
- `GroqBatchProcessor` uses latest prompts automatically
- Results include `is_ai_assisted`, `tools`, `llm_summary`
- Stored in PR model for dashboard display

---

## Key Code Patterns

### Progress Callback Pattern (from real_project_seeder.py)

```python
ProgressCallback = Any  # Callable[[str, int, int, str], None]

def _report_progress(
    self,
    step: str,
    current: int,
    total: int,
    message: str = "",
) -> None:
    """Report progress to callback if provided."""
    if self.progress_callback:
        self.progress_callback(step, current, total, message)
```

### Celery Progress Pattern (from pegasus example)

```python
from celery_progress.backend import ProgressRecorder

@shared_task(bind=True)
def my_task(self, *args):
    progress_recorder = ProgressRecorder(self)

    for i in range(total):
        # Do work...
        progress_recorder.set_progress(
            current=i + 1,
            total=total,
            description=f"Processing item {i + 1}",
        )

    return result
```

### GraphQL Fetcher Usage

```python
fetcher = GitHubGraphQLFetcher(github_token)

# Fetch with pagination
prs = fetcher.fetch_prs(
    org="antiwork",
    repo="gumroad",
    since=start_date,
    page_size=25,  # Optimal for rate limits
)

# Each PR includes:
# - title, body, author, state, merged_at
# - files_changed, additions, deletions
# - reviews, commits, labels
# - milestone, assignees, linked_issues (v2)
```

### Groq Batch Processing

```python
processor = GroqBatchProcessor()

# Submit batch (async)
batch_id = processor.submit_batch(prs)

# Poll for completion
while True:
    status = processor.get_status(batch_id)
    if status.is_complete:
        break
    time.sleep(5)

# Get results
results = processor.get_results(batch_id)
for result in results:
    # result.is_ai_assisted: bool
    # result.tools: list[str]
    # result.confidence: float
    # result.llm_summary: dict (full v5/v6 response)
```

---

## TrackedRepository Sync Fields

Already exist in model:

```python
class TrackedRepository(BaseTeamModel):
    # Sync status tracking
    sync_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('syncing', 'Syncing'),
            ('completed', 'Completed'),
            ('failed', 'Failed'),
        ],
        default='pending',
    )
    sync_progress = models.IntegerField(default=0)  # 0-100
    sync_prs_total = models.IntegerField(null=True, blank=True)
    sync_prs_completed = models.IntegerField(default=0)
    sync_started_at = models.DateTimeField(null=True, blank=True)
    sync_error = models.TextField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `SYNC_HISTORY_MONTHS` | 12 | Months of history to fetch |
| `SYNC_LLM_BATCH_SIZE` | 100 | PRs per LLM batch |
| `GROQ_API_KEY` | Required | Groq API for LLM processing |

---

## Testing Strategy

### Unit Tests

| Test File | Coverage |
|-----------|----------|
| `test_date_range.py` | Date calculation edge cases |
| `test_repo_priority.py` | Sorting by PR activity |
| `test_onboarding_sync_service.py` | Service methods |
| `test_historical_sync_task.py` | Celery task behavior |
| `test_signals.py` | Signal emission |

### Integration Tests

| Test | Purpose |
|------|---------|
| Full sync flow | End-to-end with mocked GitHub/Groq |
| Progress updates | Verify celery_progress integration |
| Error handling | Partial failures, retries |

### E2E Tests

| Test | Purpose |
|------|---------|
| Onboarding flow | User completes setup, sees progress |
| Dashboard after sync | Data visible post-sync |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| GitHub rate limits | GraphQL is 10x more efficient, use token pool |
| Groq API down | Queue for later, proceed with regex detection |
| Large repos (10k+ PRs) | Progress shows realistic time estimate |
| User closes browser | Task continues, can return to progress page |
| Timeout on batch | Retry logic with exponential backoff |
