# LLM Prompt Timestamps - Context

Last Updated: 2025-12-25

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/services/llm_prompts.py` | Core implementation | Modified |
| `apps/metrics/tests/test_llm_prompts.py` | Unit tests | Created |
| `apps/metrics/prompts/templates/user.jinja2` | Jinja template | Needs update |
| `apps/metrics/prompts/render.py` | Template rendering | Needs update |
| `apps/metrics/prompts/golden_tests.py` | Test cases | Needs timestamp data |

## Key Functions

### `calculate_relative_hours(timestamp, baseline)`
- Location: `apps/metrics/services/llm_prompts.py:140`
- Returns hours difference rounded to 1 decimal
- Returns None if either argument is None
- Handles timezone-aware datetimes

### `build_llm_pr_context(pr)`
- Location: `apps/metrics/services/llm_prompts.py:323`
- Builds complete LLM context from PullRequest object
- Now includes timestamps for commits, reviews, comments
- Uses `pr.pr_created_at` as baseline

## Database Fields Used

| Model | Field | Type | Purpose |
|-------|-------|------|---------|
| PullRequest | `pr_created_at` | DateTimeField | Baseline for timestamps |
| PullRequest | `first_review_at` | DateTimeField | Alternative baseline |
| Commit | `committed_at` | DateTimeField | Commit timestamp |
| PRReview | `submitted_at` | DateTimeField | Review timestamp |
| PRComment | `comment_created_at` | DateTimeField | Comment timestamp |

## Key Decisions

### Decision 1: Use pr_created_at as baseline
**Rationale**: More consistent than first_review_at since all PRs have creation time, but not all have reviews.

### Decision 2: Format [+X.Xh] prefix
**Rationale**: Compact, clear, machine-readable. Plus sign indicates "after baseline".

### Decision 3: Chronological ordering for commits
**Changed**: From descending (`-committed_at`) to ascending (`committed_at`) for narrative flow.

### Decision 4: Display name priority
**Changed**: Use `display_name` before `github_username` for more readable output.

## Dependencies

### Internal
- `apps/metrics/models.github` - PullRequest, Commit, PRReview, PRComment
- `apps/metrics/factories` - Test factories

### External
- Django ORM
- Python datetime

## Test Coverage

| Test Class | Tests | Status |
|------------|-------|--------|
| TestCalculateRelativeHours | 8 | PASS |
| TestBuildLlmPrContextTimestamps | 13 | PASS |
| Existing tests | 101 | PASS |

## Open Questions

1. **Should we use first_review_at when available?** Current: No, using pr_created_at for consistency
2. **Should Jinja template support timestamps?** Pending Phase 2
3. **Do golden tests need timestamp data?** Yes, for full promptfoo testing
