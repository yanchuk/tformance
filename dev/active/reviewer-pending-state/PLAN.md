# Reviewer Pending State - Distinguishing "Awaiting Review" from "Already Reviewed"

**Last Updated:** 2026-01-02

## Problem Statement

When clicking `@@pauldambra` link from insights, the PR list shows **all PRs where pauldambra has reviewed**, including PRs he has already approved or commented on. This is incorrect.

**Example:** PR #2810 appears in pauldambra's "pending" list, but he already approved it on Dec 23, 2025. He is NOT blocking this PR.

### Current Behavior (Incorrect)

| Component | Logic | Issue |
|-----------|-------|-------|
| Bottleneck detection | Excludes `approved`, includes `commented`/`changes_requested` | Over-counts pending |
| `@@username` link filter | Shows ALL PRs where user submitted any review | Shows approved PRs |

### Desired Behavior

A PR should only appear in reviewer's "pending" list if they **genuinely need to take action**:

| Review State | Blocking? | Reasoning |
|--------------|-----------|-----------|
| No review submitted | **YES** | Reviewer requested but hasn't reviewed |
| `commented` | **NO** | Reviewer provided feedback, ball with author |
| `changes_requested` | **NO** | Reviewer requested changes, ball with author |
| `approved` | **NO** | Reviewer approved, done |
| `dismissed` | **YES** | Review was dismissed, needs re-review |

## Root Cause Analysis

### Missing Data: `requested_reviewers`

GitHub tracks two separate concepts:
1. **Review requests** - People asked to review (in `requested_reviewers` list)
2. **Submitted reviews** - Reviews actually submitted (with state)

We only store #2 (PRReview records). We **don't** track #1 (who was requested).

This creates a fundamental limitation:
- We can only find PRs via existing PRReview records
- We can't find "PRs where reviewer was requested but hasn't reviewed yet"

### Current Data Model

```
PullRequest
  └── PRReview (many)
        ├── reviewer (TeamMember)
        ├── state (approved|commented|changes_requested|dismissed|pending)
        └── submitted_at
```

## Solution Options

### Option 1: Simple Fix - Exclude All Completed Reviews (Recommended for MVP)

**Logic:** If reviewer has submitted ANY review, they're not blocking. Ball is with author.

**Changes:**
1. Update `@@username` link filter to exclude PRs where reviewer's latest review is submitted
2. Update bottleneck detection to match

**Pros:**
- Simple to implement (1-2 hours)
- Fixes immediate user pain point
- No data model changes

**Cons:**
- Can't show "PRs awaiting reviewer's first review" (no review = no PRReview record)
- Doesn't handle re-review scenarios (author pushed new commits)

**Implementation:**
```python
# pr_list_service.py - reviewer_name filter
# Only include PRs where reviewer has no review OR latest is dismissed
reviewer_pr_ids = (
    PRReview.objects.filter(team=team, reviewer=member)
    .values("pull_request_id")
    .annotate(latest_state=Max("state"))  # Need custom logic
    .exclude(latest_state__in=["approved", "commented", "changes_requested"])
)
```

**Problem:** This would return ZERO PRs because:
- If reviewer has any review, it's one of those states
- We can't find PRs where reviewer has NO review (no record exists)

### Option 2: Track Requested Reviewers (Most Accurate)

**Add new field to PullRequest:**
```python
requested_reviewers = models.JSONField(
    default=list,
    help_text="List of GitHub usernames requested to review"
)
```

**Logic:** A PR is "awaiting review" from reviewer X if:
- X is in `requested_reviewers` list, AND
- X has no submitted review, OR X's latest review is `dismissed`

**Pros:**
- Most accurate representation of GitHub's state
- Can find PRs awaiting first review
- Handles re-request scenarios

**Cons:**
- Requires data model change + migration
- Requires GitHub sync update to populate field
- Requires backfill for existing PRs

**Effort:** Medium (4-6 hours)

### Option 3: Hybrid - Use Review Request Events (Advanced)

GitHub has "review_requested" webhook events. We could:
1. Track review request events separately
2. Mark request as "fulfilled" when review is submitted
3. Query unfulfilled requests

**Pros:**
- Very accurate
- Handles complex workflows

**Cons:**
- High complexity
- Requires webhook handling changes
- Overkill for current needs

**Effort:** Large (1-2 days)

## Recommended Approach

### Phase 1: Quick Fix (Option 1 Variant)

**Instead of filtering PRs, change the semantics of `@@username` link:**

Current: "PRs where @username is a reviewer"
New: "PRs where @username is listed as reviewer with pending action"

**Implementation:**
1. **Bottleneck detection** - Already fixed to exclude `approved`
   - Consider also excluding `commented` and `changes_requested`

2. **`@@username` link** - Change to show:
   - Keep current behavior (all PRs where user reviewed) BUT
   - Add visual indicator showing review state
   - Or filter to only show PRs where latest review is NOT in terminal states

**Quick fix for PR list filter:**
```python
# Instead of showing ALL PRs where reviewer submitted review,
# Only show PRs where their latest review needs follow-up

# Get PRs where reviewer's LATEST review is not terminal
from django.db.models import Max, Subquery, OuterRef

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

### Phase 2: Proper Solution (Option 2)

Add `requested_reviewers` field and update GitHub sync.

## Implementation Plan

### Phase 1 Tasks (Quick Fix)

| # | Task | File | Effort |
|---|------|------|--------|
| 1 | Update bottleneck detection to exclude `commented`/`changes_requested` | `dashboard_service.py` | S |
| 2 | Update `@@username` link filter to only show PRs needing action | `pr_list_service.py` | M |
| 3 | Update template tags to match new semantics | `pr_list_tags.py` | S |
| 4 | Add tests for new filter logic | `test_pr_list_service.py` | M |
| 5 | Regenerate insights cache | - | S |

### Phase 2 Tasks (Proper Solution)

| # | Task | Effort |
|---|------|--------|
| 1 | Add `requested_reviewers` JSONField to PullRequest | S |
| 2 | Create migration | S |
| 3 | Update GitHub sync to populate field | M |
| 4 | Backfill existing PRs from GitHub API | M |
| 5 | Update bottleneck detection to use requested_reviewers | M |
| 6 | Update PR list filter to use requested_reviewers | M |
| 7 | Add comprehensive tests | M |

## Decision Required

**Question for user:** Which approach do you prefer?

**A) Quick Fix (Phase 1 only)**
- Change logic: Reviewer with ANY submitted review is not pending
- `@@link` shows only PRs where reviewer has NOT submitted any review
- Limitation: Link may show empty results since we can't find PRs with no reviews

**B) Semantic Change**
- Keep current filter (all PRs reviewer touched)
- Change insight wording to "PRs @username has reviewed" instead of "pending"
- Add separate "needs review" indicator

**C) Full Solution (Phase 1 + Phase 2)**
- Add `requested_reviewers` field
- Accurately track who needs to review
- Most work but most accurate

## Technical Notes

### GitHub Review States

| State | Meaning |
|-------|---------|
| `APPROVED` | Reviewer approved changes |
| `COMMENTED` | General comment, not approval/rejection |
| `CHANGES_REQUESTED` | Reviewer requested changes |
| `DISMISSED` | Review was dismissed |
| `PENDING` | Review started but not submitted (rare in DB) |

### GitHub `requested_reviewers` API

```json
// GET /repos/{owner}/{repo}/pulls/{pull_number}
{
  "requested_reviewers": [
    {"login": "octocat", "id": 1},
    {"login": "hubot", "id": 2}
  ],
  "requested_teams": [
    {"name": "justice-league", "id": 1}
  ]
}
```

This list shows reviewers who:
- Were requested to review
- Have NOT yet submitted a review

Once they submit a review, they're removed from this list.
