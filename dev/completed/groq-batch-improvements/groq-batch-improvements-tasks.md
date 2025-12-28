# Groq Batch Improvements - Tasks

Last Updated: 2025-12-26 22:30

## Summary

**Decision**: Implement Option B - 20B with 70B batch fallback
**Both passes use Batch API** to maintain 50% discount
**BUG FIX**: Fixed error detection to read from Groq error file (was only checking parse errors)

## Model Comparison Results (Dec 2025)

Tested 25 PRs across 3 models to determine optimal fallback:

| Model | JSON Success | Avg Latency | Batch Input | Batch Output |
|-------|--------------|-------------|-------------|--------------|
| GPT OSS 20B | 96% (24/25) | 1252ms | $0.0375/1M | $0.15/1M |
| GPT OSS 120B | 100% (25/25) | 2219ms | $0.075/1M | $0.30/1M |
| Llama 3.3 70B | 100% (25/25) | 839ms | $0.295/1M | $0.395/1M |

### Why Llama 3.3 70B (not GPT OSS 120B)?

Both achieve 100% JSON reliability, but:
- **Speed**: Llama 3.3 is 2.6x faster (839ms vs 2219ms)
- **Cost diff**: Only $0.02 per 1000 PRs (~8% savings)
- **Architecture**: Llama 3.3 70B dense vs GPT OSS 120B MoE (5.1B active)

### Cost Per 1000 PRs

```
Pass 1 (GPT OSS 20B): $0.22
Pass 2 (Llama 3.3 70B, 4% failures): $0.04
────────────────────────────────────────
Total with Llama fallback: $0.26
Total with GPT 120B fallback: $0.24 (saves $0.02)
```

### Batch vs Caching

Per Groq docs: "The batch discount does not stack with prompt caching discounts."
All batch tokens billed at flat 50% rate. Caching provides performance benefit only.

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

- [x] Add class constants for models
- [x] Add `_wait_for_completion()` method
- [x] Add `_get_failed_pr_ids()` method
- [x] Add `_merge_results()` method
- [x] Add `submit_batch_with_fallback()` method
- [x] **BUG FIX**: Update `submit_batch_with_fallback()` to check error file:
  ```python
  # Now properly combines error file failures + parse errors
  error_file_failed = self._get_failed_pr_ids(stats["first_batch_id"])
  parse_error_failed = [r.pr_id for r in first_results if r.error]
  failed_pr_ids = list(set(error_file_failed + parse_error_failed))
  ```

### Modified `apps/metrics/management/commands/run_llm_batch.py`

- [x] Add `--with-fallback` argument
- [x] Add progress logging for both passes

## Phase 2: Testing (COMPLETED)

- [x] Write unit tests for all new methods
- [x] Test with real batches - **VERIFIED WORKING**
- [x] Cal.com batch: 41 failures detected, all 41 retried successfully

**All 36 unit tests passing.**

## Phase 3: Backfill (COMPLETE)

Final LLM Processing Status: **89.0% (53,876/60,545 PRs)**

**Note**: 6,669 PRs have empty body text and are automatically excluded.
**All processable PRs now analyzed (0 remaining).**

| Team | Analyzed | AI PRs | AI Rate |
|------|----------|--------|---------|
| Plane | 1,524 | 1,322 | 86.7% |
| Dub | 894 | 750 | 83.9% |
| Antiwork | 3,935 | 2,429 | 61.7% |
| Cal.com | 5,515 | 2,292 | 41.6% |
| PostHog | 6,159 | 413 | 6.7% |
| Vercel | 5,481 | 114 | 2.1% |

## Phase 4: Verification (COMPLETE)

- [x] Query database for coverage across all teams
- [x] Generate AI detection summary report
- [x] AI tools breakdown: CodeRabbit (51%), Devin (16%), Cubic (14%), Claude (6%), Cursor (6%)

## Phase 5: JSON Schema Mode + Bug Fixes (COMPLETED)

Added strict JSON Schema mode for more reliable structured outputs.

- [x] Implement `get_strict_schema()` function (Groq-compatible, no null types)
- [x] Add `use_json_schema_mode` parameter to `GroqBatchProcessor`
- [x] Update `create_batch_file()` to use json_schema format when enabled
- [x] Write TDD tests (6 tests in TestJSONSchemaMode class)
- [x] **BUG FIX**: Fixed `_merge_results()` to include API-level failures
  - PRs failing at Groq API level weren't being included in merged results
  - Added `failed_pr_ids` parameter to properly add retry results
  - Added TDD test `test_merge_results_adds_api_level_failures`
- [x] All 43 groq_batch tests passing

**JSON Schema mode verified working** with 17/17 (100%) success rate.

## Phase 6: Team Insights Analysis (NEXT)

- [ ] Monthly AI adoption trends per team
- [ ] Correlation: AI usage vs PR cycle time
- [ ] Correlation: AI usage vs review time
- [ ] Generate actionable insights for CTOs

---

## Commands Reference

```bash
# LLM Backfill COMPLETE - 89.0% coverage (53,876/60,545 PRs)
# All processable PRs analyzed (6,669 excluded for empty body)

# Process new PRs (after GitHub sync adds more)
/bin/bash -c 'export GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d= -f2) && .venv/bin/python manage.py run_llm_batch --limit 500 --with-fallback'

# Check coverage
.venv/bin/python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tformance.settings')
import django
django.setup()
from apps.metrics.models import PullRequest
total = PullRequest.objects.count()
with_llm = PullRequest.objects.exclude(llm_summary__isnull=True).exclude(llm_summary={}).count()
print(f'LLM: {with_llm:,}/{total:,} ({with_llm/total*100:.1f}%)')
"
```
