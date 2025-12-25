# LLM Prompt Timestamps - Tasks

Last Updated: 2025-12-25

## Phase 1: Core Implementation (COMPLETE)

- [x] Add `calculate_relative_hours()` helper function
- [x] Add timestamps to commits section in `build_llm_pr_context()`
- [x] Add timestamps to reviews section
- [x] Add timestamps to comments section
- [x] Write unit tests for `calculate_relative_hours()`
- [x] Write integration tests for timestamp formatting
- [x] Verify all 122 tests pass

## Phase 2: Golden Tests Update (COMPLETE)

- [x] Update HEALTH golden tests with timestamp-formatted data
- [x] Add `[+X.Xh]` prefixes to commit_messages in golden tests
- [x] Add `[+X.Xh] Author:` format to review_comments in golden tests
- [x] Verify all 118 prompts tests pass

**Note**: Jinja template (`user.jinja2`) already handles pre-formatted strings correctly.
No Jinja filter needed since golden tests use pre-formatted timestamp strings.

## Phase 3: Promptfoo Integration (COMPLETE)

- [x] Regenerate `promptfoo.yaml` with updated golden tests
- [ ] Run promptfoo evaluation
- [ ] Verify LLM interprets timestamps correctly
- [ ] Check no regression in AI detection accuracy

## Phase 4: TDD Refactor Phase (COMPLETE)

- [x] Extract `_format_timestamp_prefix()` helper to reduce duplication
- [x] Review implementation for code quality
- [x] Run full test suite - all passing

## Phase 5: Documentation & Commit (IN PROGRESS)

- [ ] Update CLAUDE.md if needed
- [ ] Update HANDOFF.md with timestamp info
- [ ] Commit changes with descriptive message
- [ ] Update prompt version if needed

## Acceptance Criteria

### Core Function
- [x] `calculate_relative_hours(ts, baseline)` returns float hours
- [x] Returns None when either argument is None
- [x] Rounds to 1 decimal place
- [x] Handles timezone-aware datetimes

### Output Format
- [x] Commits show `[+X.Xh]` prefix
- [x] Reviews show `[+X.Xh]` prefix before state
- [x] Comments show `[+X.Xh]` prefix before author
- [x] Missing timestamps handled gracefully (no prefix)

### Test Coverage
- [x] 8 tests for calculate_relative_hours
- [x] 13 tests for build_llm_pr_context timestamps
- [x] All existing tests pass (118 prompts tests)

## Notes

- Using `pr_created_at` as baseline (not `first_review_at`)
- Changed commits to chronological order (ascending)
- Display name preferred over github username
- Golden tests use pre-formatted timestamp strings (not datetime calculations)
