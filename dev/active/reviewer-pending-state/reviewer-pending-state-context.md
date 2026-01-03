# Reviewer Pending State - Context Document

**Last Updated:** 2026-01-02

## Key Files

### Files to Modify

| File | Purpose | Lines |
|------|---------|-------|
| `apps/metrics/services/pr_list_service.py` | Main service - `reviewer_name` filter | 159-173 |
| `apps/metrics/tests/test_pr_list_service.py` | Tests for PR list service | Add new class |

### Reference Files (Read Only)

| File | Purpose |
|------|---------|
| `apps/metrics/services/dashboard_service.py` | Bottleneck detection logic (2810-2913) |
| `apps/metrics/tests/dashboard/test_bottleneck.py` | Bottleneck test patterns |
| `apps/metrics/factories.py` | Test factories |
| `apps/metrics/models/github.py` | PRReview model definition |

## Key Decisions

### Decision 1: Exclude All "Completed" Review States

**Choice:** Exclude `approved`, `commented`, and `changes_requested` from pending list

**Reasoning:** When a reviewer submits any review, the ball is with the author:
- `commented` = "I have feedback, waiting for author response"
- `changes_requested` = "Author needs to fix issues"
- `approved` = "Done reviewing"

Only `dismissed` means reviewer needs to act again.

**Alternatives Considered:**
- Only exclude `approved` - Rejected: `commented` and `changes_requested` also mean ball is with author
- Track `requested_reviewers` - Deferred: Requires model changes, solves same problem differently

### Decision 2: Phase 1 Only (No Model Changes)

**Choice:** Implement filter fix without adding `requested_reviewers` field

**Reasoning:**
- Solves 80% of the problem with minimal code changes
- No migration needed
- No GitHub sync changes needed
- Can add `requested_reviewers` in Phase 2 if needed

### Decision 3: Use Subquery for Latest Review State

**Choice:** Use Django subquery to find latest review per (reviewer, PR) pair

**Reasoning:**
- More efficient than Python-level iteration
- Consistent with pattern in `dashboard_service.py`
- Allows database-level filtering

## Dependencies

### Model Dependencies

```python
# apps/metrics/models/github.py
class PRReview(BaseTeamModel):
    pull_request = models.ForeignKey(PullRequest, ...)
    reviewer = models.ForeignKey(TeamMember, ...)
    state = models.CharField(...)  # approved, commented, changes_requested, dismissed, pending
    submitted_at = models.DateTimeField(...)
```

### Service Dependencies

```python
# apps/metrics/services/pr_list_service.py
from apps.metrics.models import PRReview, PullRequest, TeamMember
```

### Test Dependencies

```python
# apps/metrics/factories.py
from apps.metrics.factories import (
    PRReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
```

## Code Patterns to Follow

### Test Pattern (from existing tests)

```python
class TestReviewerNameFilterPendingState(TestCase):
    """Tests for reviewer_name filter excluding completed reviews."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="Author")
        self.reviewer = TeamMemberFactory(team=self.team, github_username="test-reviewer")

    def test_example(self):
        """Test description."""
        # Create PR
        pr = PullRequestFactory(team=self.team, author=self.author, state="open")
        # Create review with EXPLICIT state
        PRReviewFactory(
            team=self.team,
            pull_request=pr,
            reviewer=self.reviewer,
            state="approved",  # ALWAYS use explicit state
        )

        result = get_prs_queryset(self.team, {"reviewer_name": "@test-reviewer"})

        self.assertEqual(result.count(), 0)  # Approved = not pending
```

### Subquery Pattern (from dashboard_service.py)

```python
from django.db.models import OuterRef, Subquery

# Get latest review state per PR for a specific reviewer
latest_review_state = PRReview.objects.filter(
    pull_request=OuterRef("pk"),
    reviewer=member,
).order_by("-submitted_at").values("state")[:1]

qs = qs.annotate(
    reviewer_latest_state=Subquery(latest_review_state)
).exclude(
    reviewer_latest_state__in=["approved", "commented", "changes_requested"]
)
```

## Important Notes

### PRReviewFactory State Behavior

The `PRReviewFactory` uses an iterator that alternates states. Always use **explicit `state` parameter** in tests:

```python
# BAD - state is random
PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer)

# GOOD - state is explicit
PRReviewFactory(team=self.team, pull_request=pr, reviewer=reviewer, state="commented")
```

### Team Isolation

All queries must be team-scoped. The `reviewer_name` filter already handles this:
- `TeamMember.objects.get(team=team, github_username__iexact=username)` - team-scoped
- `PRReview.objects.filter(team=team, reviewer=member)` - team-scoped

### Edge Cases to Handle

1. **Reviewer has no reviews on PR** - Not in our scope (we can't find PRs with no reviews)
2. **Reviewer member doesn't exist** - Return empty queryset (already handled)
3. **Multiple reviews on same PR** - Use latest by `submitted_at`
4. **PR is closed/merged** - Still filter correctly (state filter is separate)

## Verification Commands

```bash
# Run specific test file
make test ARGS='apps.metrics.tests.test_pr_list_service'

# Run specific test class
make test ARGS='apps.metrics.tests.test_pr_list_service::TestReviewerNameFilterPendingState'

# Run all tests
make test

# Check linting
make ruff
```
