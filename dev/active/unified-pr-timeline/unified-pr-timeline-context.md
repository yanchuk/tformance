# Unified PR Timeline - Context

Last Updated: 2025-12-25

## Current State: IN PROGRESS - RED PHASE

TDD tests written and failing. Ready for GREEN phase implementation.

## Key Files

| File | Purpose | Status |
|------|---------|--------|
| `apps/metrics/services/llm_prompts.py` | Timeline builder functions | TO UPDATE |
| `apps/metrics/tests/test_llm_prompts.py` | Unit tests | TESTS WRITTEN (failing) |
| `apps/metrics/prompts/templates/user.jinja2` | User prompt template | TO UPDATE |
| `apps/metrics/prompts/templates/sections/intro.jinja2` | System prompt intro | TO UPDATE |
| `apps/metrics/prompts/render.py` | Template rendering | TO UPDATE |
| `apps/metrics/prompts/golden_tests.py` | Test cases | TO UPDATE |

## Available Timestamps

| Model | Field | Access | Content Format |
|-------|-------|--------|----------------|
| PullRequest | `pr_created_at` | direct | Baseline |
| PullRequest | `merged_at` | direct | MERGED event |
| Commit | `committed_at` | `pr.commits.all()` | COMMIT: message |
| PRReview | `submitted_at` | `pr.reviews.all()` | REVIEW [STATE]: reviewer: body |
| PRComment | `comment_created_at` | `pr.comments.all()` | COMMENT: author: body |

**Not included** (per user decision):
- PRCheckRun.started_at / completed_at (CI/CD events)

## Data Structures

### TimelineEvent Dataclass
```python
@dataclass
class TimelineEvent:
    hours_after_pr_created: float  # Hours from pr_created_at
    event_type: str                # "COMMIT", "REVIEW", "COMMENT", "MERGED"
    content: str                   # Formatted content
```

### Event Content Formats

| Event Type | Content Format | Example |
|------------|----------------|---------|
| COMMIT | `{message}` | "Add notification models" |
| REVIEW | `[{STATE}]: {reviewer}: {body}` | "[CHANGES_REQUESTED]: Sarah: Need tests" |
| COMMENT | `{author}: {body}` | "Bob: Consider Redis" |
| MERGED | empty string | "" |

### Formatted Output
```
Timeline:
- [+0.5h] COMMIT: Add notification models
- [+48.0h] REVIEW [CHANGES_REQUESTED]: Sarah Tech Lead: Need rate limiting
- [+52.0h] COMMIT: Fix review feedback
- [+72.0h] REVIEW [APPROVED]: Bob Backend: LGTM
- [+96.0h] MERGED
```

## Key Functions

### Existing (reuse)
- `calculate_relative_hours(timestamp, baseline)` - Returns float hours
- `_format_timestamp_prefix(timestamp, baseline)` - Returns `[+X.Xh] `

### New to Implement
- `TimelineEvent` - Dataclass for timeline events
- `build_timeline(pr)` - Collect and sort all events
- `format_timeline(events, max_events=15)` - Format to string

## Database Queries

```python
# Commits
pr.commits.select_related('author').order_by('committed_at')

# Reviews
pr.reviews.select_related('reviewer').order_by('submitted_at')

# Comments
pr.comments.select_related('author').order_by('comment_created_at')
```

## Test Status

**RED Phase Complete**: 10 failing tests written
- TestTimelineEvent: 2 tests
- TestBuildTimeline: 5 tests
- TestFormatTimeline: 3 tests

All fail with `ImportError` - functions don't exist yet.

## Decisions Made

1. **Baseline**: Use `pr_created_at` (not `first_review_at`)
2. **Event limit**: 15 events max to avoid context overflow
3. **MERGED event**: Include as final event to show completion
4. **No CI/CD**: Skip PRCheckRun events per user request
5. **Sorting**: Ascending by timestamp (oldest first)

## Commands

```bash
# Run timeline tests only
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -k timeline -v

# Run all LLM prompt tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v

# Export promptfoo config
.venv/bin/python manage.py export_prompts

# Run promptfoo eval
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=$GROQ_API_KEY npx promptfoo eval
```

## Session Progress

- [x] Created dev docs
- [x] Analyzed available timestamps
- [x] Wrote failing tests (RED phase)
- [ ] Implement functions (GREEN phase)
- [ ] Refactor if needed (REFACTOR phase)
- [ ] Update Jinja templates
- [ ] Update system prompt
- [ ] Update golden tests
- [ ] Run promptfoo eval
- [ ] Commit changes
