# LLM Prompt Timestamps - Context

Last Updated: 2025-12-25 02:30 UTC

## Current State: COMPLETE - Ready to commit

All phases complete. System prompt, Jinja templates, and tests all synced and passing.

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/services/llm_prompts.py` | Core implementation | COMPLETE - timestamps + section updated |
| `apps/metrics/tests/test_llm_prompts.py` | Unit tests | COMPLETE - 21 new tests |
| `apps/metrics/prompts/templates/user.jinja2` | Jinja template | COMPLETE - supports new format |
| `apps/metrics/prompts/templates/sections/intro.jinja2` | System prompt intro | COMPLETE - timestamp docs added |
| `apps/metrics/prompts/render.py` | Template rendering | COMPLETE - reviews/comments params |
| `apps/metrics/prompts/golden_tests.py` | Test cases | COMPLETE - HEALTH tests with timestamps |

## Key Functions

### `calculate_relative_hours(timestamp, baseline)`
- Location: `apps/metrics/services/llm_prompts.py:140`
- Returns hours difference rounded to 1 decimal
- Returns None if either argument is None

### `_format_timestamp_prefix(timestamp, baseline)`
- Location: `apps/metrics/services/llm_prompts.py:155`
- Returns `[+X.Xh] ` prefix or empty string
- Used by commits, reviews, comments sections

### `build_llm_pr_context(pr)`
- Location: `apps/metrics/services/llm_prompts.py:352`
- Builds complete LLM context from PullRequest object
- Now includes timestamps for commits, reviews, comments
- Uses `pr.pr_created_at` as baseline

## Database Fields Used

| Model | Field | Type | Purpose |
|-------|-------|------|---------|
| PullRequest | `pr_created_at` | DateTimeField | Baseline for timestamps |
| Commit | `committed_at` | DateTimeField | Commit timestamp |
| PRReview | `submitted_at` | DateTimeField | Review timestamp |
| PRComment | `comment_created_at` | DateTimeField | Comment timestamp |

## Key Decisions (Final)

### Decision 1: Use pr_created_at as baseline
All timestamps relative to PR creation time.

### Decision 2: Format [+X.Xh] prefix
Compact, clear, machine-readable. Shows hours after PR creation.

### Decision 3: Section headers "Commits:", "Reviews:", "Comments:"
Changed from "Recent commits:" to just "Commits:" for consistency.

### Decision 4: System prompt explains timestamps
Added "## Understanding Timestamps" section explaining format and usage.

## Session Changes Summary

### Files Modified This Session

1. **`apps/metrics/services/llm_prompts.py`**:
   - Added `calculate_relative_hours()` helper
   - Added `_format_timestamp_prefix()` helper
   - Updated `build_llm_pr_context()` with timestamps
   - Updated `get_user_prompt()` to use "Commits:" and "Comments:" headers
   - Added timestamp section to `PR_ANALYSIS_SYSTEM_PROMPT`

2. **`apps/metrics/tests/test_llm_prompts.py`**:
   - 8 tests for `calculate_relative_hours()`
   - 13 tests for `build_llm_pr_context()` timestamps

3. **`apps/metrics/prompts/templates/user.jinja2`**:
   - Changed "Recent commits:" to "Commits:"
   - Added `reviews` and `comments` parameter support
   - Increased commit limit from 5 to 10

4. **`apps/metrics/prompts/templates/sections/intro.jinja2`**:
   - Added "## Understanding Timestamps" section

5. **`apps/metrics/prompts/render.py`**:
   - Added `reviews` and `comments` parameters

6. **`apps/metrics/prompts/golden_tests.py`**:
   - Added `reviews` and `comments` fields to dataclass
   - Updated HEALTH tests with timestamp-formatted data

## Test Coverage

| Test Suite | Tests | Status |
|------------|-------|--------|
| TestCalculateRelativeHours | 8 | PASS |
| TestBuildLlmPrContextTimestamps | 13 | PASS |
| prompts/tests/ | 115 | PASS |
| Promptfoo eval | 53/58 (91%) | PASS |

## Commands to Verify

```bash
# Run all prompts tests
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Run timestamp-specific tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -k timestamp -v

# Export and eval with promptfoo
.venv/bin/python manage.py export_prompts --output dev/active/ai-detection-pr-descriptions/experiments/
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=gsk_... npx promptfoo eval -c promptfoo.yaml
```

## Commits Made This Session

```
3d7db8a Add timestamps to LLM PR context for timeline analysis
4d6bd41 Add model comparison config and real-world test cases
```

## Uncommitted Changes

Need to commit:
- Template and system prompt updates from this session
- Golden tests with reviews/comments fields

## Open Questions (Resolved)

1. ~~Should we use first_review_at when available?~~ → No, using pr_created_at
2. ~~Should Jinja template support timestamps?~~ → Yes, pre-formatted strings
3. ~~Do golden tests need timestamp data?~~ → Yes, HEALTH tests updated
