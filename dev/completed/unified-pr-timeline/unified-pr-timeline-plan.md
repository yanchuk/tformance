# Unified PR Timeline - Plan

Last Updated: 2025-12-25

## Executive Summary

Implement a unified chronological timeline of all PR-related events to replace separate Commits/Reviews/Comments sections in the LLM user prompt. This enables the LLM to better understand iteration patterns, cause-effect relationships, and PR health indicators.

## Current State Analysis

### Existing Timestamp Infrastructure
The codebase already has timestamp functionality from the previous session:
- `calculate_relative_hours(timestamp, baseline)` - Returns hours difference
- `_format_timestamp_prefix(timestamp, baseline)` - Returns `[+X.Xh]` prefix
- Timestamps added to commits, reviews, comments in `build_llm_pr_context()`

### Available Timestamps (from models)

| Model | Field | Related Name | Content |
|-------|-------|--------------|---------|
| PullRequest | `pr_created_at` | - | Baseline for all timestamps |
| PullRequest | `merged_at` | - | PR merge event |
| Commit | `committed_at` | `pr.commits` | Commit authored time |
| PRReview | `submitted_at` | `pr.reviews` | Review submission time |
| PRComment | `comment_created_at` | `pr.comments` | Comment creation time |

### Current User Prompt Format (Separate Sections)
```
Commits:
- [+0.5h] Add notification models
- [+52.0h] Fix review feedback

Reviews:
- [+48.0h] [CHANGES_REQUESTED] Sarah: Need rate limiting

Comments:
- [+48.0h] Sarah: Need rate limiting
```

## Proposed Future State

### Unified Timeline Format
```
Timeline:
- [+0.5h] COMMIT: Add notification models
- [+4.0h] COMMIT: Implement WebSocket consumer
- [+48.0h] REVIEW [CHANGES_REQUESTED]: Sarah Tech Lead: Need rate limiting
- [+48.5h] COMMENT: Sarah Tech Lead: Can you also add tests?
- [+50.0h] COMMENT: Bob Backend: Consider Redis for scalability
- [+52.0h] COMMIT: Fix review feedback: add rate limiting
- [+72.0h] COMMIT: Address review: improve error handling
- [+72.0h] REVIEW [APPROVED]: Bob Backend: LGTM after fixes
- [+96.0h] MERGED
```

### Benefits
1. **Clear cause-effect**: Review at +48h → Fix commit at +52h is immediately visible
2. **Iteration patterns**: Long gaps between events indicate blockers
3. **Single section**: Reduces cognitive load for LLM
4. **Merge event**: Shows when PR was completed

## Implementation Phases

### Phase 1: Core Timeline Builder (TDD) [Effort: M]
Add dataclass and functions to `llm_prompts.py`:
- `TimelineEvent` dataclass
- `build_timeline(pr)` function
- `format_timeline(events)` function

### Phase 2: Template Integration [Effort: S]
Update Jinja templates and Python functions:
- Add timeline to `user.jinja2`
- Update system prompt to explain timeline format
- Sync `get_user_prompt()` with template

### Phase 3: Golden Tests & Verification [Effort: S]
Update test infrastructure:
- Update HEALTH golden tests with timeline format
- Run promptfoo eval to verify LLM understanding
- Ensure 90%+ pass rate maintained

## Detailed Tasks

### Phase 1: Core Timeline Builder

#### 1.1 Add TimelineEvent Dataclass [S]
**File**: `apps/metrics/services/llm_prompts.py`
**Acceptance Criteria**:
- Dataclass with fields: `hours_after_pr_created`, `event_type`, `content`
- Event types: "COMMIT", "REVIEW", "COMMENT", "MERGED"
- Properly typed with `@dataclass` decorator

#### 1.2 Implement build_timeline() [M]
**File**: `apps/metrics/services/llm_prompts.py`
**Acceptance Criteria**:
- Accepts PullRequest instance
- Collects from `pr.commits.all()`, `pr.reviews.all()`, `pr.comments.all()`
- Adds MERGED event if `pr.merged_at` exists
- Calculates hours from `pr.pr_created_at`
- Sorts by timestamp ascending
- Returns `list[TimelineEvent]`

#### 1.3 Implement format_timeline() [S]
**File**: `apps/metrics/services/llm_prompts.py`
**Acceptance Criteria**:
- Formats as `[+X.Xh] EVENT_TYPE: content`
- Special format for REVIEW: `[+X.Xh] REVIEW [STATE]: reviewer: body`
- Limits to 15 events maximum
- Returns "Timeline:\n" + formatted events

#### 1.4 Write TDD Tests [M]
**File**: `apps/metrics/tests/test_llm_prompts.py`
**Acceptance Criteria**:
- TestTimelineEvent class (2 tests)
- TestBuildTimeline class (6 tests)
- TestFormatTimeline class (4 tests)
- All tests pass after implementation

### Phase 2: Template Integration

#### 2.1 Update user.jinja2 [S]
**File**: `apps/metrics/prompts/templates/user.jinja2`
**Acceptance Criteria**:
- Add `timeline` parameter
- Replace commits/reviews/comments sections with timeline section
- Fallback to separate sections if timeline not provided

#### 2.2 Update System Prompt [S]
**File**: `apps/metrics/prompts/templates/sections/intro.jinja2`
**Acceptance Criteria**:
- Update "Understanding Timestamps" section
- Explain timeline event types
- Show example timeline interpretation

#### 2.3 Update get_user_prompt() [S]
**File**: `apps/metrics/services/llm_prompts.py`
**Acceptance Criteria**:
- Accept `timeline` parameter
- Use timeline section instead of separate sections
- Maintain backward compatibility

#### 2.4 Update build_llm_pr_context() [S]
**File**: `apps/metrics/services/llm_prompts.py`
**Acceptance Criteria**:
- Call `build_timeline(pr)` and `format_timeline()`
- Add `timeline` key to context dict
- Remove separate commits/reviews/comments keys (or keep for fallback)

### Phase 3: Golden Tests & Verification

#### 3.1 Update Golden Tests [S]
**File**: `apps/metrics/prompts/golden_tests.py`
**Acceptance Criteria**:
- Update HEALTH tests with timeline field
- Timeline formatted as single string with events
- Verify tests pass

#### 3.2 Export and Run Promptfoo [S]
**Commands**:
```bash
.venv/bin/python manage.py export_prompts
npx promptfoo eval -c dev/active/ai-detection-pr-descriptions/experiments/promptfoo.yaml
```
**Acceptance Criteria**:
- Promptfoo eval passes 90%+
- No regressions in AI detection tests

## Risk Assessment

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| LLM misinterprets timeline | Medium | Low | Clear format, examples in system prompt |
| Too many events clutters context | Medium | Medium | 15 event limit, prioritize important events |
| Breaking existing tests | High | Low | TDD approach, run all tests frequently |
| Template sync issues | Medium | Medium | Equivalence test between Jinja and Python |

## Success Metrics

1. **All tests pass**: 130+ tests in test_llm_prompts.py
2. **Promptfoo eval**: 90%+ pass rate
3. **Template equivalence**: `render_user_prompt()` matches `get_user_prompt()`
4. **Timeline clarity**: MERGED event visible, cause-effect patterns clear

## Dependencies

- Existing timestamp infrastructure (commit 3d7db8a)
- Factory classes for testing (CommitFactory, PRReviewFactory, PRCommentFactory)
- Promptfoo for LLM evaluation

## Files to Modify

| File | Changes |
|------|---------|
| `apps/metrics/services/llm_prompts.py` | Add TimelineEvent, build_timeline, format_timeline |
| `apps/metrics/tests/test_llm_prompts.py` | Add timeline tests |
| `apps/metrics/prompts/templates/user.jinja2` | Add timeline section |
| `apps/metrics/prompts/templates/sections/intro.jinja2` | Update timestamp docs |
| `apps/metrics/prompts/render.py` | Add timeline parameter |
| `apps/metrics/prompts/golden_tests.py` | Update HEALTH tests |
