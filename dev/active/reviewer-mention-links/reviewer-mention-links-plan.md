# Reviewer @Mention Links - Implementation Plan

**Last Updated**: 2026-01-02
**Status**: Ready for Implementation
**Methodology**: Strict TDD (Red-Green-Refactor)

## Executive Summary

Currently, clicking `@username` mentions in engineering insights always links to PRs **authored by** that user. However, when insights mention a review bottleneck (e.g., "@rafaeelaudibert has 22 pending reviews"), clicking should show PRs they **need to review**, not PRs they authored.

This plan implements context-aware @mention linking using a dual-syntax approach:
- `@username` → Links to PRs authored by user (current behavior)
- `@@username` → Links to PRs where user is a reviewer (new feature)

## Problem Statement

**Current Behavior:**
```
Insight: "• @rafaeelaudibert holds 22 pending reviews, creating a bottleneck"
Click: Opens /app/pull-requests/?github_name=@rafaeelaudibert&days=30
Result: Shows PRs authored by rafaeelaudibert (WRONG)
```

**Expected Behavior:**
```
Insight: "• @@rafaeelaudibert holds 22 pending reviews, creating a bottleneck"
Click: Opens /app/pull-requests/?reviewer_name=@rafaeelaudibert&days=30
Result: Shows PRs where rafaeelaudibert is a reviewer (CORRECT)
```

## Technical Approach

### Dual Syntax Strategy

| Syntax | Display | URL Parameter | Use Case |
|--------|---------|---------------|----------|
| `@username` | `@username` | `github_name=@username` | PR authors, contributors |
| `@@username` | `@username` | `reviewer_name=@username` | Review bottlenecks, pending reviews |

### Why This Approach?

1. **Backward Compatible**: Existing `@username` mentions continue working
2. **Explicit Context**: LLM and templates can use `@@` for reviewer context
3. **Clean Display**: `@@` renders as `@` in output (user doesn't see difference)
4. **Simple Pattern**: Easy regex update, no semantic analysis needed

## Implementation Phases

### Phase 1: Backend Filter (TDD)

Add `reviewer_name` filter to PR list service, parallel to existing `github_name`.

**Files Modified:**
- `apps/metrics/services/pr_list_service.py`
- `apps/metrics/views/pr_list_views.py`
- `apps/metrics/tests/test_pr_list_service.py`

### Phase 2: Template Filter (TDD)

Extend `linkify_mentions` to handle `@@username` syntax.

**Files Modified:**
- `apps/metrics/templatetags/pr_list_tags.py`
- `apps/metrics/tests/test_pr_list_tags.py`

### Phase 3: Prompt Updates

Update LLM prompts to use `@@` for bottleneck mentions.

**Files Modified:**
- `apps/metrics/services/insight_llm.py`
- `apps/metrics/prompts/templates/insight/user.jinja2`

### Phase 4: Integration Testing

Regenerate insights and verify end-to-end flow.

## Detailed Task Breakdown

### Phase 1: Backend Filter (Effort: M)

#### Task 1.1: RED - Write Failing Tests for reviewer_name Filter
**Acceptance Criteria:**
- [ ] Test `test_filter_by_reviewer_name` - basic filtering with @ prefix
- [ ] Test `test_filter_by_reviewer_name_without_prefix` - filtering without @
- [ ] Test `test_filter_by_reviewer_name_case_insensitive` - case insensitivity
- [ ] Test `test_filter_by_reviewer_name_not_found_returns_empty` - no match handling
- [ ] Test `test_filter_by_reviewer_name_team_scoped` - security/isolation

**Pattern:** Mirror existing `github_name` tests but for reviewer context.

#### Task 1.2: GREEN - Implement reviewer_name Filter
**Acceptance Criteria:**
- [ ] Add `reviewer_name` filter to `get_prs_queryset()`
- [ ] Strip @ prefix if present
- [ ] Look up team member by github_username (case-insensitive)
- [ ] Filter PRs where user is a reviewer (via PRReview)
- [ ] Return empty queryset if member not found

#### Task 1.3: GREEN - Add reviewer_name to View Filter Keys
**Acceptance Criteria:**
- [ ] Add `"reviewer_name"` to `filter_keys` list in `_get_filters_from_request()`

#### Task 1.4: REFACTOR - Code Quality
**Acceptance Criteria:**
- [ ] No code duplication between github_name and reviewer_name logic
- [ ] Consider extracting shared member lookup logic
- [ ] All tests still pass

### Phase 2: Template Filter (Effort: M)

#### Task 2.1: RED - Write Failing Tests for @@ Syntax
**Acceptance Criteria:**
- [ ] Test `test_converts_reviewer_mention_to_link` - `@@alice` → reviewer link
- [ ] Test `test_reviewer_mention_displays_single_at` - `@@alice` displays as `@alice`
- [ ] Test `test_mixed_author_and_reviewer_mentions` - both in same text
- [ ] Test `test_reviewer_mention_uses_days_parameter` - days param works
- [ ] Test `test_triple_at_not_matched` - `@@@alice` edge case

#### Task 2.2: GREEN - Extend linkify_mentions for @@ Syntax
**Acceptance Criteria:**
- [ ] Add second regex pattern for `@@username`
- [ ] Process `@@` first (longer match), then `@`
- [ ] Generate `reviewer_name=@username` for `@@` matches
- [ ] Display as `@username` (single @) in link text

#### Task 2.3: REFACTOR - Pattern Optimization
**Acceptance Criteria:**
- [ ] Single pass through text if possible
- [ ] No regex catastrophic backtracking risks
- [ ] All tests still pass

### Phase 3: Prompt Updates (Effort: S)

#### Task 3.1: Update User Prompt Template
**Acceptance Criteria:**
- [ ] Change bottleneck line to use `@@{{ github_username }}`
- [ ] Add comment explaining `@@` = reviewer context

#### Task 3.2: Update System Prompt
**Acceptance Criteria:**
- [ ] Add `@@username` format documentation
- [ ] Update examples to show `@@` for bottleneck mentions
- [ ] Clarify when to use `@` vs `@@`

### Phase 4: Integration Testing (Effort: S)

#### Task 4.1: Regenerate Insights
**Acceptance Criteria:**
- [ ] Delete existing demo team insights
- [ ] Regenerate with updated prompts
- [ ] Verify `@@` appears in bottleneck mentions

#### Task 4.2: End-to-End Verification
**Acceptance Criteria:**
- [ ] Click author `@mention` → shows authored PRs
- [ ] Click reviewer `@@mention` → shows PRs to review
- [ ] Both display as `@username` visually

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Existing insights have wrong syntax | Medium | Regenerate insights for demo teams |
| LLM doesn't use @@ consistently | Low | Clear examples in prompt, can regenerate |
| Regex performance with many @@ | Low | Simple patterns, tested with large text |
| Breaking existing @mention links | High | `@` behavior unchanged, only adding `@@` |

## Success Metrics

1. **Functional**: Clicking bottleneck @mention shows reviewer's pending PRs
2. **Tests**: All 10+ new tests pass
3. **Backward Compatible**: Existing @mention links unchanged
4. **Performance**: No measurable increase in template render time

## Dependencies

- Existing `github_name` filter implementation (completed)
- Existing `linkify_mentions` filter (completed)
- PRReview model with reviewer relationship (exists)
- Demo teams with bottleneck data (exists)

## Commands Reference

```bash
# Run specific test file
make test ARGS='apps.metrics.tests.test_pr_list_service'

# Run specific test class
make test ARGS='apps.metrics.tests.test_pr_list_service::TestGetPrsQueryset'

# Run tests matching pattern
make test ARGS='-k reviewer_name'

# Regenerate insights
GROQ_API_KEY=xxx .venv/bin/python gen_insights.py
```
