# Reviewer Pending State Implementation Plan

**Last Updated:** 2026-01-02

## Executive Summary

Implement proper distinction between "awaiting review" and "already reviewed" states for the `@@username` reviewer filter. Currently, clicking `@@pauldambra` from insights shows ALL PRs where pauldambra submitted any review, including PRs he already approved. This creates confusion as users see PRs that don't actually need action.

## Current State Analysis

### Problem Statement

When clicking `@@pauldambra` link from LLM insights, the PR list shows PRs where:
- pauldambra has ANY review on record
- Including PRs he already **approved** (not blocking)

**Example:** PR #2810 appears in pauldambra's list, but he approved it on Dec 23, 2025.

### Current Implementation

| Component | File | Current Logic |
|-----------|------|---------------|
| Bottleneck detection | `dashboard_service.py:2810-2913` | Excludes `approved`, counts `commented`/`changes_requested` |
| `reviewer_name` filter | `pr_list_service.py:159-173` | Returns ALL PRs where user submitted any review |

### Code Analysis

**pr_list_service.py (lines 159-173):**
```python
reviewer_name = filters.get("reviewer_name")
if reviewer_name:
    username = reviewer_name.lstrip("@")
    member = TeamMember.objects.get(team=team, github_username__iexact=username)
    # BUG: Shows ALL PRs where this member has submitted a review
    reviewer_pr_ids = PRReview.objects.filter(
        team=team, reviewer=member
    ).values_list("pull_request_id", flat=True)
    qs = qs.filter(id__in=reviewer_pr_ids)
```

### Review State Semantics

| Review State | Is Blocking? | Ball With |
|--------------|--------------|-----------|
| No review submitted | YES | Reviewer |
| `commented` | NO | Author (reviewer gave feedback) |
| `changes_requested` | NO | Author (needs to fix) |
| `approved` | NO | Author/Maintainer |
| `dismissed` | YES | Reviewer (needs to re-review) |

## Proposed Future State

### Target Behavior

The `@@username` filter should show PRs where the reviewer **genuinely needs to take action**:

1. **Open, non-draft PRs only** (already filtered by dashboard link)
2. **Reviewer has NOT submitted any review** (awaiting first review), OR
3. **Reviewer's latest review is `dismissed`** (needs to re-review)

Since we don't track `requested_reviewers` from GitHub API, we focus on Phase 1:
- Exclude PRs where reviewer's latest review is `approved`, `commented`, or `changes_requested`

### Why This Approach?

When a reviewer submits ANY review (even a comment), the ball is with the author:
- **commented**: "I have questions, author needs to respond"
- **changes_requested**: "Author needs to fix these issues"
- **approved**: "I'm done reviewing this PR"

Only `dismissed` reviews require the reviewer to act again.

## Implementation Phases

### Phase 1: Reviewer Filter Fix (TDD)

Update `reviewer_name` filter to exclude PRs where reviewer's latest review is a "completed" state.

#### TDD Cycle 1: reviewer_name Filter

**🔴 RED: Write Failing Tests**

Create test class in `apps/metrics/tests/test_pr_list_service.py`:

```python
class TestReviewerNameFilterPendingState(TestCase):
    """Tests for reviewer_name filter excluding completed reviews."""

    def test_excludes_prs_with_approved_latest_review(self):
        """PRs where reviewer's latest review is 'approved' are excluded."""

    def test_excludes_prs_with_commented_latest_review(self):
        """PRs where reviewer's latest review is 'commented' are excluded."""

    def test_excludes_prs_with_changes_requested_latest_review(self):
        """PRs where reviewer's latest review is 'changes_requested' are excluded."""

    def test_includes_prs_with_dismissed_latest_review(self):
        """PRs where reviewer's latest review is 'dismissed' ARE included."""

    def test_latest_review_wins_over_earlier(self):
        """Only the latest review state matters (commented then approved = excluded)."""

    def test_changes_requested_after_approval_included(self):
        """If latest review is changes_requested after approval, PR is included."""

    def test_mixed_approved_and_pending_prs(self):
        """Reviewer with some approved and some pending PRs shows only pending."""
```

**🟢 GREEN: Implement Fix**

Update `pr_list_service.py` reviewer_name filter:

```python
reviewer_name = filters.get("reviewer_name")
if reviewer_name:
    username = reviewer_name.lstrip("@")
    try:
        member = TeamMember.objects.get(team=team, github_username__iexact=username)

        # Get PRs where reviewer's LATEST review is NOT a completed state
        # Completed states: approved, commented, changes_requested
        # Only 'dismissed' or 'pending' should show (reviewer needs to act)
        from django.db.models import OuterRef, Subquery

        # Subquery to get latest review state for each PR by this reviewer
        latest_review_state = PRReview.objects.filter(
            pull_request=OuterRef("pk"),
            reviewer=member,
        ).order_by("-submitted_at").values("state")[:1]

        # Get all PR IDs where this reviewer has submitted any review
        reviewer_pr_ids = PRReview.objects.filter(
            team=team, reviewer=member
        ).values_list("pull_request_id", flat=True).distinct()

        # Filter to PRs where latest review needs action
        qs = qs.filter(id__in=reviewer_pr_ids).annotate(
            reviewer_latest_state=Subquery(latest_review_state)
        ).exclude(
            # Exclude completed review states
            reviewer_latest_state__in=["approved", "commented", "changes_requested"]
        )
    except TeamMember.DoesNotExist:
        qs = qs.none()
```

**🔵 REFACTOR: Clean Up**

- Extract common patterns
- Ensure query performance is optimal
- Add docstring updates

### Phase 2: Bottleneck Detection Enhancement (Optional)

Update bottleneck detection to also exclude `commented` and `changes_requested` states.

This is **optional** because:
- Current behavior is defensible (reviewer gave feedback but author may need more)
- Could be argued that `commented` means reviewer is still engaged

**Decision:** Skip Phase 2 for now, focus on Phase 1.

## Detailed Tasks

### Phase 1 Tasks (Strict TDD)

| # | Task | Type | Effort | Dependencies |
|---|------|------|--------|--------------|
| 1.1 | Write failing tests for `reviewer_name` filter pending state | RED | M | None |
| 1.2 | Run tests to confirm failure | RED | S | 1.1 |
| 1.3 | Implement `reviewer_name` filter fix | GREEN | M | 1.2 |
| 1.4 | Run tests to confirm pass | GREEN | S | 1.3 |
| 1.5 | Refactor and clean up | REFACTOR | S | 1.4 |
| 1.6 | Run full test suite | QA | S | 1.5 |
| 1.7 | Verify with real data (posthog-demo) | QA | S | 1.6 |

### Acceptance Criteria

**Task 1.1 - Write Failing Tests:**
- [ ] Test file: `apps/metrics/tests/test_pr_list_service.py`
- [ ] New test class: `TestReviewerNameFilterPendingState`
- [ ] At least 7 test methods covering all review states
- [ ] Tests use explicit `state` parameter on PRReviewFactory
- [ ] Tests follow existing patterns in the file

**Task 1.3 - Implement Fix:**
- [ ] `reviewer_name` filter excludes approved/commented/changes_requested
- [ ] Uses subquery for latest review state (performance)
- [ ] Handles edge case of no reviews gracefully
- [ ] Maintains team isolation security

**Task 1.7 - Verify with Real Data:**
- [ ] Navigate to `@@pauldambra` link in posthog-demo team
- [ ] Confirm PR #2810 is NOT shown (he approved it)
- [ ] Confirm only genuinely pending PRs appear

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Query performance degradation | Low | Medium | Use subquery pattern, test with explain |
| Breaking existing tests | Low | Medium | Run full test suite before merge |
| Incorrect state handling | Medium | High | Comprehensive TDD coverage |
| Edge case: No reviews at all | Low | Low | Handle DoesNotExist gracefully |

## Success Metrics

1. **Functional:** `@@username` link shows only PRs needing reviewer action
2. **Performance:** Query time < 200ms for typical team size
3. **Test Coverage:** 100% of new code covered by tests
4. **Regression:** All existing tests pass

## Required Resources

- **Files to Modify:**
  - `apps/metrics/services/pr_list_service.py`
  - `apps/metrics/tests/test_pr_list_service.py`

- **No Model Changes Required** (Phase 1 only uses existing PRReview data)

## Notes

### Why Not Track `requested_reviewers`?

GitHub's `requested_reviewers` API field shows who was asked to review but hasn't yet. This would be ideal but requires:
- New JSONField on PullRequest model
- Migration
- GitHub sync update
- Backfill for existing PRs

**Deferred to Phase 2** if demand exists. Phase 1 solves 80% of the problem.

### State Machine Considerations

GitHub review lifecycle:
```
requested → (pending) → commented|changes_requested|approved|dismissed
                ↑                                      |
                └──────────────────────────────────────┘
                    (author pushes new commits, dismissal)
```

Our Phase 1 approach handles the most common cases:
- Reviewer approved → Not blocking
- Reviewer commented → Ball with author
- Reviewer requested changes → Ball with author
- Review dismissed → Blocking (needs re-review)
