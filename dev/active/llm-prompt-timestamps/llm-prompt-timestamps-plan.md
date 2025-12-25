# LLM Prompt Timestamps Feature - Plan

Last Updated: 2025-12-25

## Executive Summary

Add timestamps and relative timing to the LLM user prompt for better context in AI detection and health assessment. Timestamps show when commits, reviews, and comments occurred relative to PR creation, helping the LLM understand the PR's timeline and iteration patterns.

## Current State Analysis

### Before Implementation
The `build_llm_pr_context()` function outputs:
```
Commits:
- Address review feedback
- Initial implementation

Reviews:
- [APPROVED] developer13: Looks good!

Comments:
- developer13: Should we consider caching?
```

### Problems
1. No temporal context for events
2. LLM can't assess iteration timing (e.g., "commit 2h after review")
3. Health assessment lacks timeline visibility
4. Can't distinguish rapid iterations from slow responses

## Proposed Future State

### After Implementation
```
Commits:
- [+4.0h] Address review feedback
- [+0.5h] Initial implementation

Reviews:
- [+2.0h] [APPROVED] Bob: Looks good!

Comments:
- [+2.5h] Bob: Should we consider caching?
```

### Benefits
1. LLM can assess response patterns (quick fixes vs slow iterations)
2. Better health assessment insights
3. Timeline visibility for PR process understanding
4. Supports metrics like "time to fix review comments"

## Implementation Phases

### Phase 1: Core Implementation (COMPLETE)
- [x] Add `calculate_relative_hours()` helper function
- [x] Modify commits section with timestamps
- [x] Modify reviews section with timestamps
- [x] Modify comments section with timestamps
- [x] Use `pr_created_at` as baseline

### Phase 2: Jinja Template Sync (PENDING)
- [ ] Update `user.jinja2` template to match Python function
- [ ] Add timestamp parameters to `render_user_prompt()`
- [ ] Update golden tests with timestamp expectations
- [ ] Regenerate promptfoo.yaml

### Phase 3: Testing & Validation (IN PROGRESS)
- [x] Unit tests for `calculate_relative_hours()`
- [x] Integration tests for timestamp formatting
- [ ] Promptfoo evaluation with new format
- [ ] Verify LLM handles timestamps correctly

## Technical Details

### Helper Function
```python
def calculate_relative_hours(timestamp: datetime | None, baseline: datetime | None) -> float | None:
    """Calculate hours difference between timestamp and baseline.
    Returns hours rounded to 1 decimal place, or None if either is None.
    """
    if timestamp is None or baseline is None:
        return None
    delta = timestamp - baseline
    hours = delta.total_seconds() / 3600
    return round(hours, 1)
```

### Baseline Selection
- Primary: `pr.pr_created_at` (PR creation time)
- Alternative: `pr.first_review_at` (for review-relative timing)
- Current implementation uses `pr_created_at` for consistency

### Format Specification
| Event Type | Format |
|------------|--------|
| Commit | `- [+X.Xh] message` |
| Review | `- [+X.Xh] [STATE] reviewer: body` |
| Comment | `- [+X.Xh] author: body` |

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Token bloat from timestamps | Low | Low | Prefix is only 9 chars per line |
| None timestamps | Medium | Low | Graceful handling implemented |
| Timezone issues | Low | Medium | Django uses timezone-aware datetimes |
| Jinja/Python mismatch | Medium | Medium | Equivalence tests exist |

## Success Metrics

1. All 21 new tests pass
2. Existing 101+ tests still pass
3. Promptfoo evaluation shows no regression
4. LLM correctly interprets timeline context
