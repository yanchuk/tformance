# LLM Full PR Context - Key Files & Context

**Last Updated: 2025-12-25 (Session 3 - COMMITTED)**

## Status: COMPLETE & COMMITTED ✅

Commit: `0f45dcd Add unified build_llm_pr_context() for LLM analysis (v6.2.0)`

All phases completed. Task can be moved to `dev/completed/`.

## What Was Done

1. **Created unified `build_llm_pr_context()` function** in `apps/metrics/services/llm_prompts.py:287-466`
   - Takes PullRequest object with prefetched relations
   - Includes ALL 10 sections: metadata, flags, organization, code changes, timing, commits, reviews, comments, repo languages, description
   - PROMPT_VERSION bumped to "6.2.0"

2. **Updated both callers**:
   - `groq_batch.py`: Removed `_format_pr_context()` and 4 helper methods
   - `run_llm_analysis.py`: Replaced 30+ lines with single function call

3. **Updated promptfoo tests**:
   - Created `promptfoo-v6.2.yaml` with 13 tests
   - Uses `v6.2.0-system.txt` (synced with source of truth)
   - All tests passing (100%)

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | SOURCE OF TRUTH - `build_llm_pr_context()`, version 6.2.0 |
| `apps/integrations/services/groq_batch.py` | Uses unified function in `create_batch_file()` |
| `apps/metrics/management/commands/run_llm_analysis.py` | Uses unified function |
| `dev/active/ai-detection-pr-descriptions/experiments/promptfoo-v6.2.yaml` | Test config |

## Test Results

| Suite | Result |
|-------|--------|
| test_llm_prompts.py | 101 passed |
| test_groq_batch.py | 27 passed |
| promptfoo-v6.2.yaml | 13/13 passed |

## No Migrations Needed

Only Python function changes - no model modifications.

## Usage

```python
from apps.metrics.services.llm_prompts import build_llm_pr_context

pr = PullRequest.objects.select_related("author").prefetch_related(
    "files", "commits", "reviews__reviewer", "comments__author"
).get(id=pr_id)

context = build_llm_pr_context(pr)
```

## Next Steps

Move task to `dev/completed/llm-full-pr-context/`
