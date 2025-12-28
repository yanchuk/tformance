# Groq Batch Processing Improvements Plan

Last Updated: 2025-12-26

## Executive Summary

Investigation of the LLM analysis pipeline revealed **two distinct issues**:

1. **~21,000 PRs (55%) never submitted** - Historical data not backfilled
2. **~1,000+ actual batch failures** - Wrong model causing JSON validation errors

### Root Cause Analysis

**CRITICAL FINDING**: The batch processor uses `openai/gpt-oss-20b` (20B model) while the direct API uses `llama-3.3-70b-versatile` (70B model). The smaller model produces invalid JSON 93.5% of failed requests.

| Error Type | Count | Percentage |
|------------|-------|------------|
| JSON validation failed | 782 | 93.5% |
| Max tokens exceeded | 54 | 6.5% |
| **Total analyzed** | **836** | 100% |

### Evidence from Groq Batch Dashboard

| Batch ID | Total | Completed | Failed | Failure % |
|----------|-------|-----------|--------|-----------|
| batch_01kd9xbskdfg0... | 1,000 | 422 | 578 | **57.8%** |
| batch_01kdabnj80eyh... | 5,000 | 4,878 | 122 | 2.4% |
| batch_01kdabf6cqed4... | 5,000 | 4,884 | 116 | 2.3% |
| batch_01kdabvkt7fbk... | 1,299 | 1,238 | 61 | 4.7% |

### Validation Test

Retried failed PR #26313 with `llama-3.3-70b-versatile`:
- **Result**: Successfully processed with valid JSON
- **Confidence**: Model change will fix 93.5% of failures

## Current Architecture

```
groq_batch.py:
  model = "openai/gpt-oss-20b"     ← PROBLEM: Small model
  max_tokens = 1500

run_llm_analysis.py:
  model = "llama-3.3-70b-versatile"  ← WORKS: Large model
  max_tokens = 800
```

## Error Details

```json
{
  "response": {
    "status_code": 400,
    "body": {
      "error": {
        "message": "Failed to validate JSON",
        "type": "invalid_request_error",
        "code": "json_validate_failed",
        "failed_generation": ""  // Model generated non-JSON output
      }
    }
  }
}
```

```json
{
  "error": {
    "message": "Failed to generate JSON",
    "code": "json_validate_failed",
    "failed_generation": "max completion tokens reached before generating a valid document"
  }
}
```

## Proposed Solutions

### Solution 1: Change Batch Model to llama-3.3-70b-versatile (RECOMMENDED)

**Change in `groq_batch.py`:**
```python
class GroqBatchProcessor:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",  # Changed from openai/gpt-oss-20b
        # ...
    ):
```

**Pros:**
- Simple one-line fix
- Same model as direct API (proven to work)
- 70B model is 3.5x larger, much better JSON generation
- Both models have 131K context window

**Cons:**
- May be slightly more expensive per token (check Groq pricing)
- Need to reprocess failed PRs after fix

**Effort: S** (Small - one line change)

### Solution 2: Increase max_tokens for Batch API

**Change from 1500 → 2000 tokens:**
```python
"body": {
    "model": self.model,
    "max_tokens": 2000,  # Increased from 1500
    # ...
}
```

**Pros:**
- Fixes max_tokens errors (6.5% of failures)
- Easy change

**Cons:**
- Won't fix JSON validation errors (93.5%)
- Slight cost increase

**Effort: S**

### Solution 3: Add Retry Logic for Failed PRs

**Create new command `retry_failed_llm_batch.py`:**
```python
def handle(self, *args, **options):
    """Retry PRs that failed in batch processing."""

    # Get PRs that exist but have no llm_summary
    failed_pr_ids = get_failed_pr_ids_from_batch(batch_id)

    # Retry with direct API (uses better model)
    for pr_id in failed_pr_ids:
        process_single_pr(pr_id)
```

**Pros:**
- Salvages failed PRs without resubmitting entire batch
- Uses direct API which is more reliable

**Cons:**
- 50% more expensive than batch API
- Requires implementing new command

**Effort: M**

### Solution 4: Hybrid Approach - Batch with Direct Fallback

```python
def process_with_fallback(prs):
    """Process batch, then retry failures with direct API."""
    batch_id = processor.submit_batch(prs)

    # Wait for completion
    results = processor.get_results(batch_id)

    # Collect failures
    failed_ids = [r.pr_id for r in results if r.error]

    # Retry failures with direct API
    for pr_id in failed_ids:
        process_single_pr(pr_id, model="llama-3.3-70b-versatile")
```

**Pros:**
- Best of both worlds: batch savings + reliability
- Automatic retry without manual intervention

**Cons:**
- More complex implementation
- Need to track batch completion state

**Effort: L**

## Recommendation

### Phase 0: Immediate Fix (NOW)

**Change batch model to `llama-3.3-70b-versatile`:**

```bash
# Single line change in apps/integrations/services/groq_batch.py
# Line 301: model: str = "openai/gpt-oss-20b"
#    → model: str = "llama-3.3-70b-versatile"
```

This will fix 93.5% of failures going forward.

### Phase 1: Reprocess Failed PRs

After model change, run backfill for PRs that failed:

```bash
# Re-run batch processing for teams with high failure rates
GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --limit 1000 --poll
```

### Phase 2: Increase max_tokens (Optional)

If max_tokens errors persist after model change:

```python
# Line 369 in groq_batch.py
"max_tokens": 2000,  # Increased from 1500
```

### Phase 3: Add Monitoring

Track batch success rates:

```sql
-- Query to monitor LLM processing health
SELECT
    DATE(pr_created_at) as date,
    COUNT(*) as total,
    COUNT(CASE WHEN llm_summary IS NOT NULL THEN 1 END) as processed,
    ROUND(100.0 * COUNT(CASE WHEN llm_summary IS NOT NULL THEN 1 END) / COUNT(*), 1) as pct
FROM metrics_pullrequest
WHERE body IS NOT NULL AND body != ''
GROUP BY DATE(pr_created_at)
ORDER BY date DESC
LIMIT 30;
```

## Success Metrics

| Metric | Before Fix | Target | After Fix |
|--------|------------|--------|-----------|
| Batch failure rate | ~5-58% | <2% | TBD |
| JSON validation errors | 93.5% of failures | <1% | TBD |
| Total coverage | 44.8% | >95% | TBD |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Model cost increase | Low | Low | llama-3.3-70b is competitively priced |
| Model availability | Low | Medium | Fallback to smaller model if needed |
| Breaking existing code | Very Low | Low | Single line change, well-tested flow |

## Implementation Checklist

- [ ] **Phase 0**: Change model in `groq_batch.py` (line 301)
- [ ] Test batch with small sample (10 PRs)
- [ ] Verify JSON output is valid
- [ ] Run full backfill for unprocessed PRs
- [ ] Monitor failure rates in Groq dashboard
- [ ] (Optional) Increase max_tokens if still seeing truncation
