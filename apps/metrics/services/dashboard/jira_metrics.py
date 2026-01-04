"""Jira-related metrics for dashboard.

Functions for Jira sprint metrics, PR-Jira correlation, and story point analysis.
"""

from datetime import date, timedelta

from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import TruncWeek
from django.utils import timezone

from apps.metrics.models import JiraIssue, PullRequest
from apps.metrics.services.dashboard._helpers import _get_merged_prs_in_range
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day


def get_jira_sprint_metrics(team: Team, start_date: date, end_date: date) -> dict:
    """Get sprint-level metrics from Jira issues.

    Aggregates metrics for issues resolved within the date range.

    Args:
        team: The team to get metrics for
        start_date: Start of date range
        end_date: End of date range

    Returns:
        dict with:
            - issues_resolved: Count of issues resolved in range
            - story_points_completed: Sum of story points
            - avg_cycle_time_hours: Average cycle time
            - issue_types: Breakdown by issue type
    """
    issues = JiraIssue.objects.filter(
        team=team,
        resolved_at__gte=start_of_day(start_date),
        resolved_at__lte=end_of_day(end_date),
    )

    # Aggregate metrics
    aggregates = issues.aggregate(
        count=Count("id"),
        story_points=Sum("story_points"),
        avg_cycle_time=Avg("cycle_time_hours"),
    )

    # Get breakdown by issue type
    issue_types = dict(issues.values("issue_type").annotate(count=Count("id")).values_list("issue_type", "count"))

    return {
        "issues_resolved": aggregates["count"] or 0,
        "story_points_completed": aggregates["story_points"] or 0,
        "avg_cycle_time_hours": aggregates["avg_cycle_time"],
        "issue_types": issue_types,
    }


def get_pr_jira_correlation(team: Team, start_date: date, end_date: date) -> dict:
    """Correlate PR metrics with Jira linkage.

    Compares metrics between PRs that have Jira keys and those that don't.

    Args:
        team: The team to analyze
        start_date: Start of date range
        end_date: End of date range

    Returns:
        dict with:
            - total_prs: Total merged PRs in range
            - linked_count: PRs with jira_key
            - unlinked_count: PRs without jira_key
            - linkage_rate: Percentage of PRs with Jira links
            - linked_avg_cycle_time: Average cycle time for linked PRs
            - unlinked_avg_cycle_time: Average cycle time for unlinked PRs
    """
    prs = _get_merged_prs_in_range(team, start_date, end_date)

    total = prs.count()

    if total == 0:
        return {
            "total_prs": 0,
            "linked_count": 0,
            "unlinked_count": 0,
            "linkage_rate": 0,
            "linked_avg_cycle_time": None,
            "unlinked_avg_cycle_time": None,
        }

    linked = prs.exclude(jira_key="")
    unlinked = prs.filter(jira_key="")

    linked_count = linked.count()
    unlinked_count = unlinked.count()

    # Calculate linkage rate
    linkage_rate = round(linked_count / total * 100, 1)

    # Calculate average cycle times
    linked_avg = linked.aggregate(avg=Avg("cycle_time_hours"))["avg"]
    unlinked_avg = unlinked.aggregate(avg=Avg("cycle_time_hours"))["avg"]

    return {
        "total_prs": total,
        "linked_count": linked_count,
        "unlinked_count": unlinked_count,
        "linkage_rate": linkage_rate,
        "linked_avg_cycle_time": linked_avg,
        "unlinked_avg_cycle_time": unlinked_avg,
    }


def get_linkage_trend(team: Team, weeks: int = 4) -> list[dict]:
    """Get PR-Jira linkage rate trend over time.

    Args:
        team: Team instance
        weeks: Number of weeks to return (default 4)

    Returns:
        List of dicts with week_start, linkage_rate, linked_count, total_prs
        ordered from oldest to newest
    """
    # Calculate date range (weeks ago from today)
    end_date = timezone.now()
    start_date = end_date - timedelta(weeks=weeks)

    # Query merged PRs, group by week
    weekly_data = (
        PullRequest.objects.filter(
            team=team,
            state="merged",
            merged_at__gte=start_date,
            merged_at__lte=end_date,
        )
        .annotate(week=TruncWeek("merged_at"))
        .values("week")
        .annotate(
            total_prs=Count("id"),
            linked_count=Count("id", filter=Q(jira_key__gt="")),
        )
        .order_by("week")
    )

    result = []
    for data in weekly_data:
        total = data["total_prs"]
        linked = data["linked_count"]
        linkage_rate = (linked / total * 100) if total > 0 else 0
        result.append(
            {
                "week_start": data["week"].strftime("%Y-%m-%d"),
                "linkage_rate": round(linkage_rate, 1),
                "linked_count": linked,
                "total_prs": total,
            }
        )

    # Return only the requested number of weeks (most recent)
    return result[-weeks:] if len(result) > weeks else result


def get_story_point_correlation(team: Team, start_date: date, end_date: date) -> dict:
    """Correlate story points with actual PR delivery time.

    Groups PRs by story point buckets and calculates average cycle time per bucket.
    PRs are linked to Jira issues via the jira_key field (string match).

    Args:
        team: The team to analyze
        start_date: Start of date range
        end_date: End of date range

    Returns:
        dict with:
            - buckets: List of dicts with sp_range, avg_hours, pr_count, expected_hours
            - total_linked_prs: Count of PRs with jira_key
            - total_with_sp: Count of PRs with valid story_points
    """
    # Define story point bucket ranges and expected hours
    # Buckets: 1-2, 3-5, 5-8, 8-13, 13+
    BUCKET_CONFIG = [
        {"sp_range": "1-2", "min_sp": 1, "max_sp": 2, "expected_hours": 4.0},
        {"sp_range": "3-5", "min_sp": 3, "max_sp": 5, "expected_hours": 8.0},
        {"sp_range": "5-8", "min_sp": 5, "max_sp": 8, "expected_hours": 16.0},
        {"sp_range": "8-13", "min_sp": 8, "max_sp": 13, "expected_hours": 26.0},
        {"sp_range": "13+", "min_sp": 13, "max_sp": None, "expected_hours": 40.0},
    ]

    # Get merged PRs in date range with jira_key
    prs = _get_merged_prs_in_range(team, start_date, end_date)
    linked_prs = prs.exclude(jira_key="")
    total_linked_prs = linked_prs.count()

    if total_linked_prs == 0:
        # Return empty buckets with zero counts
        buckets = [
            {
                "sp_range": bucket["sp_range"],
                "avg_hours": None,
                "pr_count": 0,
                "expected_hours": bucket["expected_hours"],
            }
            for bucket in BUCKET_CONFIG
        ]
        return {
            "buckets": buckets,
            "total_linked_prs": 0,
            "total_with_sp": 0,
        }

    # Build a dict of jira_key -> story_points for efficient lookup
    jira_keys = list(linked_prs.values_list("jira_key", flat=True).distinct())
    sp_lookup = dict(
        JiraIssue.objects.filter(team=team, jira_key__in=jira_keys)
        .exclude(story_points__isnull=True)
        .values_list("jira_key", "story_points")
    )

    # Group PRs by story point buckets
    bucket_data = {bucket["sp_range"]: {"hours": [], "count": 0} for bucket in BUCKET_CONFIG}

    total_with_sp = 0
    for pr in linked_prs.only("jira_key", "cycle_time_hours"):
        sp = sp_lookup.get(pr.jira_key)
        if sp is None:
            continue  # Skip PRs without story points

        total_with_sp += 1
        sp_float = float(sp)

        # Find the right bucket for this story point value
        for bucket in BUCKET_CONFIG:
            min_sp = bucket["min_sp"]
            max_sp = bucket["max_sp"]

            # Check if SP falls in this bucket
            # Buckets have overlapping boundaries (e.g., 5 is in both 3-5 and 5-8)
            # Use the first matching bucket (lower bucket takes priority)
            if max_sp is None:
                # 13+ bucket: anything >= 13
                if sp_float >= min_sp:
                    if pr.cycle_time_hours is not None:
                        bucket_data[bucket["sp_range"]]["hours"].append(float(pr.cycle_time_hours))
                    bucket_data[bucket["sp_range"]]["count"] += 1
                    break
            else:
                # Regular bucket: min_sp <= sp <= max_sp
                if min_sp <= sp_float <= max_sp:
                    if pr.cycle_time_hours is not None:
                        bucket_data[bucket["sp_range"]]["hours"].append(float(pr.cycle_time_hours))
                    bucket_data[bucket["sp_range"]]["count"] += 1
                    break

    # Build result buckets with averages
    buckets = []
    for bucket in BUCKET_CONFIG:
        sp_range = bucket["sp_range"]
        data = bucket_data[sp_range]
        hours_list = data["hours"]
        pr_count = data["count"]

        avg_hours = None
        if hours_list:
            avg_hours = sum(hours_list) / len(hours_list)

        buckets.append(
            {
                "sp_range": sp_range,
                "avg_hours": avg_hours,
                "pr_count": pr_count,
                "expected_hours": bucket["expected_hours"],
            }
        )

    return {
        "buckets": buckets,
        "total_linked_prs": total_linked_prs,
        "total_with_sp": total_with_sp,
    }
