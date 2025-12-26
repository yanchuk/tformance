# Groq Batch Improvements - Context

Last Updated: 2025-12-26

## Current State

**STATUS: Ready for Implementation**

Investigation complete. User approved **Option B: 20B with 70B batch fallback**.

## Key Decision Made This Session

**Implement two-pass batch processing:**
1. First pass: Use cheap `openai/gpt-oss-20b` (Batch API)
2. Second pass: Retry failures with `llama-3.3-70b-versatile` (Batch API)

**Important: Both passes use Batch API** to maximize 50% discount.

## Root Cause Analysis (Completed)

| Error Type | Count | % |
|------------|-------|---|
| JSON validation failed | 782 | **93.5%** |
| Max tokens exceeded | 54 | 6.5% |

**Cause**: `openai/gpt-oss-20b` (20B params) can't reliably generate complex JSON. The 70B model works reliably.

## Pricing Analysis

| Model | Input/1M tokens | Output/1M tokens | Batch Discount |
|-------|-----------------|------------------|----------------|
| `llama-3.3-70b-versatile` | $0.30 | $0.40 | 50% |
| `openai/gpt-oss-20b` | $0.0375 | $0.15 | 50% |

**Cost for 21,000 PRs:**
- Always 70B: ~$36
- Always 20B: ~$6 (but 5-58% failures)
- **Option B (20B + 70B fallback): ~$10-15** ← SELECTED

## Implementation Plan

### Files to Modify

1. **`apps/integrations/services/groq_batch.py`**
   - Add `submit_batch_with_fallback()` method
   - Add `retry_failed_batch()` method
   - Keep existing `submit_batch()` for backward compatibility

2. **`apps/metrics/management/commands/run_llm_batch.py`**
   - Add `--with-fallback` flag to use two-pass processing
   - Add `--retry-batch` flag to retry a specific failed batch

### Code Architecture

```python
class GroqBatchProcessor:
    DEFAULT_MODEL = "openai/gpt-oss-20b"  # Cheap, 80-95% success
    FALLBACK_MODEL = "llama-3.3-70b-versatile"  # Expensive, 98%+ success

    def submit_batch_with_fallback(self, prs, poll_interval=30):
        """Two-pass processing: cheap model first, retry failures with better model."""
        # Pass 1: Submit with cheap model
        batch_id = self.submit_batch(prs, model=self.DEFAULT_MODEL)
        results = self._wait_for_completion(batch_id, poll_interval)

        # Identify failures
        failed_pr_ids = [r.pr_id for r in results if r.error]

        if not failed_pr_ids:
            return results  # All succeeded

        # Pass 2: Retry failures with better model (ALSO BATCH API)
        failed_prs = PullRequest.objects.filter(id__in=failed_pr_ids)
        retry_batch_id = self.submit_batch(list(failed_prs), model=self.FALLBACK_MODEL)
        retry_results = self._wait_for_completion(retry_batch_id, poll_interval)

        # Merge results
        return self._merge_results(results, retry_results)
```

### Key Implementation Notes

1. **Both passes use Batch API** - User explicitly requested batch for retries to reduce costs
2. **Track failed PR IDs from error file** - Already implemented in investigation
3. **Merge results** - Combine successful results from both passes
4. **Backward compatible** - Existing `submit_batch()` unchanged

## Files Modified This Session

| File | Change |
|------|--------|
| `dev/active/groq-batch-improvements/*` | Created plan docs |

**No code changes yet** - Only documentation and analysis.

## Validation Completed

- ✅ Retrieved error files from 4 Groq batches
- ✅ Analyzed 836 failures
- ✅ Identified model mismatch as root cause
- ✅ Tested retry with 70B model - SUCCESS on PR #26313
- ✅ Verified pricing from Groq docs

## Next Immediate Steps

1. Implement `submit_batch_with_fallback()` in `groq_batch.py`
2. Add helper methods: `_wait_for_completion()`, `_get_failed_pr_ids()`, `_merge_results()`
3. Update `run_llm_batch.py` command with `--with-fallback` flag
4. Write tests for new functionality
5. Test with small batch (10 PRs)
6. Run full backfill with fallback enabled

## Commands to Run on Restart

```bash
# Check current test status
make test ARGS='apps/integrations/tests/test_groq_batch.py -v'

# After implementation, test with small batch
GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --limit 10 --with-fallback --poll
```

## No Migrations Needed

This change only affects service-layer code, no model changes.
