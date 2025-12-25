# LLM Full PR Context - Key Files & Context

**Last Updated: 2025-12-25 (Session 3 - Final)**

## Implementation Complete ✅

All phases (1-5) are complete. The unified `build_llm_pr_context()` function is now used by both callers.

### What Was Done This Session

1. **Completed Phase 3 - Updated both callers**:
   - `groq_batch.py`: Removed `_format_pr_context()` and 4 helper methods, now uses `build_llm_pr_context(pr)`
   - `run_llm_analysis.py`: Replaced 30+ lines of manual field extraction with single function call
   - Updated 6 tests in `test_groq_batch.py` to use unified function

2. **Completed Phase 4 - Promptfoo updates**:
   - Created `promptfoo-v6.2.yaml` with new context format
   - Added 3 comment-based AI detection tests
   - Updated to use `v6.2.0-system.txt` (synced with `llm_prompts.py`)
   - All 13 tests passing (100%)

3. **Synced prompt files**:
   - `prompts/v6-system.txt` - synced with source of truth
   - `prompts/v6.2.0-system.txt` - identical, used by promptfoo-v6.2.yaml

### Files Modified This Session

| File | Changes |
|------|---------|
| `apps/integrations/services/groq_batch.py` | Removed `_format_pr_context()` and helpers, uses `build_llm_pr_context()` |
| `apps/integrations/tests/test_groq_batch.py` | Updated 6 tests for new function |
| `apps/metrics/management/commands/run_llm_analysis.py` | Simplified to use `build_llm_pr_context()`, updated prefetch |
| `dev/active/ai-detection-pr-descriptions/experiments/promptfoo-v6.2.yaml` | Created with new format |
| `dev/active/ai-detection-pr-descriptions/experiments/prompts/v6-system.txt` | Synced with llm_prompts.py |
| `dev/active/ai-detection-pr-descriptions/experiments/prompts/v6.2.0-system.txt` | Verified identical |

### Test Results

| Test Suite | Result |
|-----------|--------|
| `test_llm_prompts.py` | 101 passed |
| `test_groq_batch.py` | 27 passed |
| `promptfoo-v6.2.yaml` | 13/13 passed (100%) |
| Full test suite | 2958 passed (2 unrelated failures) |

### No Migrations Needed

This work only added/modified Python functions - no model changes.

## Key Files

### Source of Truth

| File | Purpose |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | `build_llm_pr_context()`, `PR_ANALYSIS_SYSTEM_PROMPT`, `PROMPT_VERSION = "6.2.0"` |

### Callers (Both Updated)

| File | Purpose |
|------|---------|
| `apps/integrations/services/groq_batch.py` | Batch processing - `create_batch_file()` uses unified function |
| `apps/metrics/management/commands/run_llm_analysis.py` | CLI command - uses unified function |

### Promptfoo Tests

| File | Purpose |
|------|---------|
| `dev/active/ai-detection-pr-descriptions/experiments/promptfoo-v6.2.yaml` | Main test config |
| `dev/active/ai-detection-pr-descriptions/experiments/prompts/v6.2.0-system.txt` | System prompt |

## Usage

```python
from apps.metrics.services.llm_prompts import build_llm_pr_context

# Requires prefetched relations for performance
pr = PullRequest.objects.select_related("author").prefetch_related(
    "files", "commits", "reviews__reviewer", "comments__author"
).get(id=pr_id)

context = build_llm_pr_context(pr)
```

## Commands on Restart

```bash
# Verify tests pass
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py apps/integrations/tests/test_groq_batch.py -v

# Run promptfoo tests
cd dev/active/ai-detection-pr-descriptions/experiments
npx promptfoo eval -c promptfoo-v6.2.yaml

# View promptfoo results
npx promptfoo view
```

## Key Decisions Made

1. **Skip CI/CD data (PRCheckRun)** - Low value, merged PRs have passing CI
2. **Add PRComment** - May contain AI tool discussion
3. **Unified function approach** - Single function both callers use
4. **Prefetch strategy** - `files`, `commits`, `reviews__reviewer`, `comments__author`
5. **Lenient promptfoo assertions** - Allow LLM judgment variations on edge cases

## No Uncommitted Changes

All work is saved. Run `git status` to verify.
