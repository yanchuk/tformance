"""
Copilot Champions Service.

Identifies "Copilot Champions" - team members who effectively use Copilot,
ship fast, and maintain quality. These power users can mentor/train
struggling teammates.

Scoring uses team-relative percentiles:
- Copilot Score (40%): Based on acceptance rate percentile
- Delivery Score (35%): Based on cycle time percentile (lower is better)
- Quality Score (25%): Based on revert rate percentile (lower is better)
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Q, Sum

from apps.metrics.models import AIUsageDaily, PullRequest
from apps.teams.models import Team

# Qualification thresholds
MIN_ACTIVE_DAYS = 5
MIN_MERGED_PRS = 3
MIN_ACCEPTANCE_RATE = Decimal("20")

# Scoring weights
COPILOT_WEIGHT = Decimal("0.40")
DELIVERY_WEIGHT = Decimal("0.35")
QUALITY_WEIGHT = Decimal("0.25")


def get_copilot_champions(
    team: Team,
    start_date: date,
    end_date: date,
    top_n: int = 3,
) -> list[dict]:
    """Get top Copilot champions for a team.

    Champions are users who:
    1. Use Copilot heavily (high acceptance rate)
    2. Ship fast (low cycle time)
    3. Have good quality (low revert rate)

    Args:
        team: The team to find champions for.
        start_date: Start date of the period (inclusive).
        end_date: End date of the period (inclusive).
        top_n: Number of champions to return (default 3).

    Returns:
        List of champion dictionaries, ordered by overall score (highest first):
        [
            {
                "member_id": 123,
                "display_name": "Alice",
                "github_username": "alice",
                "overall_score": 86.2,
                "stats": {
                    "acceptance_rate": 52.3,
                    "prs_merged": 18,
                    "avg_cycle_time_hours": 24.5,
                    "revert_rate": 0.0,
                }
            },
            ...
        ]
    """
    # Get Copilot usage aggregated by member
    copilot_data = _get_copilot_usage_by_member(team, start_date, end_date)
    if not copilot_data:
        return []

    # Get PR metrics aggregated by member
    pr_data = _get_pr_metrics_by_member(team, start_date, end_date)

    # Combine and filter by thresholds
    qualified_members = _get_qualified_members(copilot_data, pr_data)
    if not qualified_members:
        return []

    # Calculate percentile-based scores
    scored_members = _calculate_percentile_scores(qualified_members)

    # Sort by overall score (descending), then by member_id for deterministic ordering
    sorted_members = sorted(
        scored_members,
        key=lambda x: (-x["overall_score"], x["member_id"]),
    )

    return sorted_members[:top_n]


def _get_copilot_usage_by_member(
    team: Team,
    start_date: date,
    end_date: date,
) -> dict[int, dict]:
    """Aggregate Copilot usage data by team member.

    Returns:
        Dict keyed by member_id with aggregated Copilot metrics.
    """
    # Explicit team filter for TEAM001 compliance (noqa: TEAM001 - explicit team parameter)
    usage_qs = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        date__gte=start_date,
        date__lte=end_date,
    )

    # Aggregate by member
    member_usage = (
        usage_qs.values("member_id", "member__display_name", "member__github_username")
        .annotate(
            active_days=Count("date", distinct=True),
            total_suggestions=Sum("suggestions_shown"),
            total_acceptances=Sum("suggestions_accepted"),
            avg_acceptance_rate=Avg("acceptance_rate"),
        )
        .filter(active_days__gte=1)  # At least some activity
    )

    return {
        item["member_id"]: {
            "member_id": item["member_id"],
            "display_name": item["member__display_name"],
            "github_username": item["member__github_username"],
            "active_days": item["active_days"],
            "total_suggestions": item["total_suggestions"] or 0,
            "total_acceptances": item["total_acceptances"] or 0,
            "avg_acceptance_rate": float(item["avg_acceptance_rate"] or 0),
        }
        for item in member_usage
    }


def _get_pr_metrics_by_member(
    team: Team,
    start_date: date,
    end_date: date,
) -> dict[int, dict]:
    """Aggregate PR metrics by team member.

    Returns:
        Dict keyed by member_id with aggregated PR metrics.
    """
    # Explicit team filter for TEAM001 compliance (noqa: TEAM001 - explicit team parameter)
    # Filter by merged_at date to match the period
    pr_qs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__date__gte=start_date,
        merged_at__date__lte=end_date,
    )

    # Aggregate by author
    member_prs = (
        pr_qs.values("author_id")
        .annotate(
            prs_merged=Count("id"),
            revert_count=Count("id", filter=Q(is_revert=True)),
            avg_cycle_time=Avg("cycle_time_hours"),
        )
        .filter(prs_merged__gte=1)  # At least some PRs
    )

    result = {}
    for item in member_prs:
        prs_merged = item["prs_merged"]
        revert_count = item["revert_count"]
        revert_rate = revert_count / prs_merged if prs_merged > 0 else 0

        result[item["author_id"]] = {
            "prs_merged": prs_merged,
            "revert_count": revert_count,
            "revert_rate": revert_rate,
            "avg_cycle_time_hours": float(item["avg_cycle_time"] or 0),
        }

    return result


def _get_qualified_members(
    copilot_data: dict[int, dict],
    pr_data: dict[int, dict],
) -> list[dict]:
    """Filter and combine data for members meeting all thresholds.

    Thresholds:
    - Minimum 5 days active with Copilot
    - Minimum 3 merged PRs
    - Minimum 20% acceptance rate
    """
    qualified = []

    for member_id, copilot in copilot_data.items():
        # Check Copilot thresholds
        if copilot["active_days"] < MIN_ACTIVE_DAYS:
            continue
        if copilot["avg_acceptance_rate"] < float(MIN_ACCEPTANCE_RATE):
            continue

        # Check PR thresholds
        pr = pr_data.get(member_id)
        if not pr or pr["prs_merged"] < MIN_MERGED_PRS:
            continue

        # Combine data
        qualified.append(
            {
                "member_id": member_id,
                "display_name": copilot["display_name"],
                "github_username": copilot["github_username"],
                "acceptance_rate": copilot["avg_acceptance_rate"],
                "prs_merged": pr["prs_merged"],
                "avg_cycle_time_hours": pr["avg_cycle_time_hours"],
                "revert_rate": pr["revert_rate"],
            }
        )

    return qualified


def _calculate_percentile_scores(members: list[dict]) -> list[dict]:
    """Calculate percentile-based scores for qualified members.

    Scores are relative to the team:
    - Copilot Score: Higher acceptance rate = higher score
    - Delivery Score: Lower cycle time = higher score
    - Quality Score: Lower revert rate = higher score
    """
    if not members:
        return []

    # Extract values for percentile calculation
    acceptance_rates = sorted([m["acceptance_rate"] for m in members])
    cycle_times = sorted([m["avg_cycle_time_hours"] for m in members])
    revert_rates = sorted([m["revert_rate"] for m in members])

    scored = []
    for member in members:
        # Calculate percentiles (0-100 scale)
        copilot_score = _percentile_of(member["acceptance_rate"], acceptance_rates)
        # For cycle time and revert rate, lower is better (invert percentile)
        delivery_score = 100 - _percentile_of(member["avg_cycle_time_hours"], cycle_times)
        quality_score = 100 - _percentile_of(member["revert_rate"], revert_rates)

        # Weighted average
        overall = (
            Decimal(str(copilot_score)) * COPILOT_WEIGHT
            + Decimal(str(delivery_score)) * DELIVERY_WEIGHT
            + Decimal(str(quality_score)) * QUALITY_WEIGHT
        )

        scored.append(
            {
                "member_id": member["member_id"],
                "display_name": member["display_name"],
                "github_username": member["github_username"],
                "overall_score": float(overall),
                "stats": {
                    "acceptance_rate": member["acceptance_rate"],
                    "prs_merged": member["prs_merged"],
                    "avg_cycle_time_hours": member["avg_cycle_time_hours"],
                    "revert_rate": member["revert_rate"],
                },
            }
        )

    return scored


def _percentile_of(value: float, sorted_values: list[float]) -> float:
    """Calculate the percentile of a value within a sorted list.

    Returns a value between 0 and 100 indicating what percentage
    of values in the list are less than or equal to the given value.
    """
    if not sorted_values:
        return 50.0

    n = len(sorted_values)
    if n == 1:
        return 50.0  # Only one value, return middle percentile

    # Count how many values are strictly less than our value
    count_below = sum(1 for v in sorted_values if v < value)
    # Count how many are equal
    count_equal = sum(1 for v in sorted_values if v == value)

    # Percentile formula: (count_below + 0.5 * count_equal) / n * 100
    percentile = ((count_below + 0.5 * count_equal) / n) * 100

    return percentile
