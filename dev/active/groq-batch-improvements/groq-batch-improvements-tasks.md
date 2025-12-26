# Groq Batch Improvements - Tasks

Last Updated: 2025-12-26

## Summary

**Decision**: Implement Option B - 20B with 70B batch fallback
**Both passes use Batch API** to maintain 50% discount

## Phase 0: Investigation (COMPLETED)

- [x] Query Groq batch dashboard for failure stats
- [x] Download error files from failed batches
- [x] Analyze error patterns (93.5% JSON validation, 6.5% max tokens)
- [x] Identify root cause (20B model can't generate complex JSON)
- [x] Test retry with 70B model (SUCCESS)
- [x] Research pricing ($0.0375 vs $0.30 per 1M input tokens)
- [x] Present options to user and get approval

## Phase 1: Implement Fallback Logic (COMPLETED)

### Modified `apps/integrations/services/groq_batch.py`

- [x] Add class constants for models:
  ```python
  DEFAULT_MODEL = "openai/gpt-oss-20b"
  FALLBACK_MODEL = "llama-3.3-70b-versatile"
  ```

- [x] Add `_wait_for_completion(batch_id, poll_interval=30)` method:
  - Poll `get_status()` until `is_complete`
  - Return results from `get_results()`

- [x] Add `_get_failed_pr_ids(batch_id)` method:
  - Download error file
  - Parse JSONL and extract pr-{id} custom_ids
  - Return list of integer PR IDs

- [x] Add `_merge_results(first_results, retry_results)` method:
  - Keep successful results from first pass
  - Replace failed results with retry results
  - Return combined list

- [x] Add `submit_batch_with_fallback(prs, poll_interval=30)` method:
  - Returns tuple of (results, stats)
  - Stats include: first_batch_id, retry_batch_id, first_pass_failures, final_failures

- [x] Update `__init__()` to accept optional `model` parameter

### Modified `apps/metrics/management/commands/run_llm_batch.py`

- [x] Add `--with-fallback` argument
- [x] Add `_submit_batch_with_fallback()` method
- [x] Add `_save_results()` method for saving results to DB
- [x] Add progress logging for both passes

## Phase 2: Testing (IN PROGRESS)

- [x] Write unit tests for `_merge_results()` (3 tests)
- [x] Write unit tests for `_get_failed_pr_ids()` (2 tests)
- [x] Write unit tests for `_wait_for_completion()` (1 test)
- [x] Write unit tests for model constants and init (3 tests)
- [ ] **NEXT**: Test with small batch (10 PRs) with `--with-fallback`
- [ ] Verify both batches appear in Groq dashboard
- [ ] Check failure rate drops to <2% after retry

**All 36 unit tests passing.**

## Phase 3: Backfill

After implementation verified:

- [ ] Run backfill for Cal.com (~4,147 unprocessed)
- [ ] Run backfill for Antiwork (~3,083 unprocessed)
- [ ] Run backfill for PostHog Analytics (~3,045 unprocessed)
- [ ] Run backfill for remaining teams

## Phase 4: Verification

- [ ] Query database for >95% coverage across all teams
- [ ] Verify Groq dashboard shows low failure rate
- [ ] Spot check llm_summary quality

---

## Key Technical Notes

### Error File Structure
```json
{
  "custom_id": "pr-26313",
  "response": {
    "status_code": 400,
    "body": {
      "error": {
        "message": "Failed to validate JSON",
        "code": "json_validate_failed"
      }
    }
  }
}
```

### Groq API for Error Files
```python
from groq import Groq
client = Groq()
batch = client.batches.retrieve(batch_id)
error_content = client.files.content(batch.error_file_id)
lines = error_content.text().strip().split('\n')
```

### Test Command (READY TO RUN)
```bash
GROQ_API_KEY=$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --limit 10 --with-fallback
```
