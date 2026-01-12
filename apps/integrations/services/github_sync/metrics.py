"""Metrics calculation functions for PR and reviewer analytics.

These functions analyze synced data to compute derived metrics like iteration counts,
response times, and reviewer correlations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest


def calculate_pr_iteration_metrics(pr: PullRequest) -> None:
    """Calculate iteration metrics for a pull request from synced data.

    Updates the following fields on the PullRequest:
    - total_comments: Count of all comments on this PR
    - commits_after_first_review: Commits made after the first review
    - review_rounds: Number of changes_requested → commit cycles
    - avg_fix_response_hours: Average time from changes_requested to next commit

    Args:
        pr: PullRequest instance to calculate metrics for
    """
    from decimal import Decimal

    from apps.metrics.models import Commit, PRComment, PRReview

    # Count total comments: PRComment records + PRReview records with body text
    # PRComment tracks issue/review comments, PRReview tracks review submissions
    comment_count = PRComment.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
        pull_request=pr
    ).count()
    review_comment_count = (
        PRReview.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
            pull_request=pr
        )
        .exclude(body="")
        .exclude(body__isnull=True)
        .count()
    )
    pr.total_comments = comment_count + review_comment_count

    # Get first review timestamp
    first_review = (
        PRReview.objects.filter(pull_request=pr)  # noqa: TEAM001 - filtering by PR which is team-scoped
        .order_by("submitted_at")
        .first()
    )

    if first_review and first_review.submitted_at:
        # Count commits after first review
        pr.commits_after_first_review = Commit.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
            pull_request=pr, committed_at__gt=first_review.submitted_at
        ).count()
    else:
        pr.commits_after_first_review = 0

    # Get all changes_requested reviews and commits in chronological order
    changes_requested_reviews = (
        PRReview.objects.filter(  # noqa: TEAM001 - filtering by PR which is team-scoped
            pull_request=pr, state="changes_requested"
        )
        .order_by("submitted_at")
        .values_list("submitted_at", flat=True)
    )

    commits = (
        Commit.objects.filter(pull_request=pr)  # noqa: TEAM001 - filtering by PR which is team-scoped
        .exclude(committed_at__isnull=True)
        .order_by("committed_at")
        .values_list("committed_at", flat=True)
    )
    commits_list = list(commits)

    # Calculate review rounds and fix response times
    review_rounds = 0
    fix_response_times = []

    for review_time in changes_requested_reviews:
        if review_time is None:
            continue

        # Find the first commit after this review
        for commit_time in commits_list:
            if commit_time > review_time:
                # This is a review round
                review_rounds += 1
                # Calculate response time in hours
                response_time = (commit_time - review_time).total_seconds() / 3600
                fix_response_times.append(response_time)
                break

    pr.review_rounds = review_rounds

    # Calculate average fix response time
    if fix_response_times:
        avg_hours = sum(fix_response_times) / len(fix_response_times)
        pr.avg_fix_response_hours = Decimal(str(round(avg_hours, 2)))
    else:
        pr.avg_fix_response_hours = None

    pr.save(update_fields=["total_comments", "commits_after_first_review", "review_rounds", "avg_fix_response_hours"])


def calculate_reviewer_correlations(team) -> int:
    """Calculate reviewer correlation statistics for a team.

    Analyzes PRReview records to find pairs of reviewers who reviewed the same PRs
    and calculates their agreement/disagreement statistics.

    Args:
        team: Team instance to calculate correlations for

    Returns:
        Number of correlation records created/updated
    """
    from collections import defaultdict
    from itertools import combinations

    from apps.metrics.models import PRReview, ReviewerCorrelation

    # Get all reviews with definitive states (approved or changes_requested)
    reviews = (
        PRReview.objects.filter(team=team, state__in=["approved", "changes_requested"])
        .select_related("pull_request", "reviewer")
        .values("pull_request_id", "reviewer_id", "state")
    )

    # Group reviews by PR
    pr_reviews = defaultdict(dict)  # {pr_id: {reviewer_id: state}}
    for review in reviews:
        pr_id = review["pull_request_id"]
        reviewer_id = review["reviewer_id"]
        state = review["state"]
        # If multiple reviews by same reviewer on same PR, take the last one
        pr_reviews[pr_id][reviewer_id] = state

    # Count agreements/disagreements for each pair
    pair_stats = defaultdict(lambda: {"prs_reviewed_together": 0, "agreements": 0, "disagreements": 0})

    for _pr_id, reviewers in pr_reviews.items():
        # Get all reviewer pairs who reviewed this PR
        reviewer_ids = list(reviewers.keys())
        if len(reviewer_ids) < 2:
            continue

        for r1_id, r2_id in combinations(reviewer_ids, 2):
            # Ensure consistent ordering (smaller ID first)
            if r1_id > r2_id:
                r1_id, r2_id = r2_id, r1_id

            pair_key = (r1_id, r2_id)
            pair_stats[pair_key]["prs_reviewed_together"] += 1

            # Check agreement
            r1_state = reviewers[r1_id]
            r2_state = reviewers[r2_id]
            if r1_state == r2_state:
                pair_stats[pair_key]["agreements"] += 1
            else:
                pair_stats[pair_key]["disagreements"] += 1

    # Clear existing correlations for this team and create fresh ones
    ReviewerCorrelation.objects.filter(team=team).delete()

    correlations_created = 0
    for (r1_id, r2_id), stats in pair_stats.items():
        ReviewerCorrelation.objects.create(
            team=team,
            reviewer_1_id=r1_id,
            reviewer_2_id=r2_id,
            prs_reviewed_together=stats["prs_reviewed_together"],
            agreements=stats["agreements"],
            disagreements=stats["disagreements"],
        )
        correlations_created += 1

    return correlations_created
