"""Service functions for managing insights on the dashboard."""

from datetime import timedelta

from django.db.models import Avg
from django.utils import timezone

from apps.metrics.models import DailyInsight, PullRequest

# Thresholds for generating insights
TREND_CHANGE_THRESHOLD = 0.15  # 15% change triggers insight
AI_ADOPTION_MILESTONES = [25, 50, 75, 90]  # Percentage milestones
PR_COUNT_MILESTONES = [50, 100, 250, 500, 1000]  # PR count milestones


def get_recent_insights(team, limit=5):
    """Get recent non-dismissed insights for a team.

    Args:
        team: Team instance to get insights for
        limit: Maximum number of insights to return (default: 5)

    Returns:
        list of DailyInsight objects ordered by date desc, priority, category
    """
    return list(
        DailyInsight.objects.filter(
            team=team,
            is_dismissed=False,
        ).order_by("-date", "priority", "category")[:limit]
    )


def _get_week_metrics(team, start_date, end_date):
    """Get metrics for a date range.

    Args:
        team: Team instance
        start_date: Start of the period (inclusive)
        end_date: End of the period (exclusive)

    Returns dict with avg_cycle_time, avg_review_time, ai_adoption_pct, pr_count.
    """
    prs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__gte=start_date,
        merged_at__lt=end_date,  # Exclusive end to avoid overlap between periods
    )

    pr_count = prs.count()
    if pr_count == 0:
        return None

    avg_cycle_time = prs.exclude(cycle_time_hours__isnull=True).aggregate(avg=Avg("cycle_time_hours"))["avg"]

    avg_review_time = prs.exclude(review_time_hours__isnull=True).aggregate(avg=Avg("review_time_hours"))["avg"]

    ai_count = prs.filter(is_ai_assisted=True).count()
    ai_adoption_pct = (ai_count / pr_count * 100) if pr_count > 0 else 0

    return {
        "avg_cycle_time": avg_cycle_time,
        "avg_review_time": avg_review_time,
        "ai_adoption_pct": ai_adoption_pct,
        "pr_count": pr_count,
    }


def generate_trend_insights(team, insight_date):
    """Generate trend-based insights by comparing this week vs last week.

    Args:
        team: Team instance
        insight_date: Date to generate insights for

    Returns:
        List of unsaved DailyInsight objects
    """
    insights = []

    # Get this week and last week metrics
    # end_date is midnight of insight_date, we want to include the full day
    end_date = timezone.make_aware(timezone.datetime.combine(insight_date, timezone.datetime.min.time()))

    # This week: 7 days before insight_date to end of insight_date
    this_week_start = end_date - timedelta(days=7)
    this_week_end = end_date + timedelta(days=1)  # Include the full insight_date
    this_week = _get_week_metrics(team, this_week_start, this_week_end)

    # Last week: 14 days before insight_date to 7 days before (non-overlapping)
    last_week_start = end_date - timedelta(days=14)
    last_week_end = end_date - timedelta(days=7)  # Ends where this_week starts
    last_week = _get_week_metrics(team, last_week_start, last_week_end)

    if not this_week or not last_week:
        return insights

    # Cycle time trend
    if this_week["avg_cycle_time"] and last_week["avg_cycle_time"]:
        change = (this_week["avg_cycle_time"] - last_week["avg_cycle_time"]) / last_week["avg_cycle_time"]
        if abs(change) >= TREND_CHANGE_THRESHOLD:
            if change > 0:
                # Cycle time increased (negative trend)
                insights.append(
                    DailyInsight(
                        team=team,
                        date=insight_date,
                        category="trend",
                        priority="high" if change > 0.3 else "medium",
                        title=f"Cycle time increase of {abs(change) * 100:.0f}%",
                        description=(
                            f"Your average cycle time increased from "
                            f"{last_week['avg_cycle_time']:.1f}h to "
                            f"{this_week['avg_cycle_time']:.1f}h this week."
                        ),
                        metric_type="cycle_time",
                        metric_value={
                            "current": float(this_week["avg_cycle_time"]),
                            "previous": float(last_week["avg_cycle_time"]),
                            "change_pct": float(change * 100),
                        },
                        comparison_period="week_over_week",
                    )
                )
            else:
                # Cycle time improved (positive trend)
                insights.append(
                    DailyInsight(
                        team=team,
                        date=insight_date,
                        category="trend",
                        priority="low",
                        title=f"Cycle time improved by {abs(change) * 100:.0f}%",
                        description=(
                            f"Your average cycle time improved from "
                            f"{last_week['avg_cycle_time']:.1f}h to "
                            f"{this_week['avg_cycle_time']:.1f}h this week."
                        ),
                        metric_type="cycle_time",
                        metric_value={
                            "current": float(this_week["avg_cycle_time"]),
                            "previous": float(last_week["avg_cycle_time"]),
                            "change_pct": float(change * 100),
                        },
                        comparison_period="week_over_week",
                    )
                )

    # AI adoption trend
    if this_week["ai_adoption_pct"] > 0 or last_week["ai_adoption_pct"] > 0:
        change_pct = this_week["ai_adoption_pct"] - last_week["ai_adoption_pct"]
        if abs(change_pct) >= 10:  # 10 percentage point change
            insights.append(
                DailyInsight(
                    team=team,
                    date=insight_date,
                    category="trend",
                    priority="medium",
                    title=f"AI adoption {'up' if change_pct > 0 else 'down'} {abs(change_pct):.0f}pp",
                    description=(
                        f"AI-assisted PRs changed from {last_week['ai_adoption_pct']:.0f}% "
                        f"to {this_week['ai_adoption_pct']:.0f}% this week."
                    ),
                    metric_type="ai_adoption",
                    metric_value={
                        "current": float(this_week["ai_adoption_pct"]),
                        "previous": float(last_week["ai_adoption_pct"]),
                        "change_pct": float(change_pct),
                    },
                    comparison_period="week_over_week",
                )
            )

    return insights


def generate_benchmark_insights(team, insight_date):
    """Generate benchmark comparison insights.

    Args:
        team: Team instance
        insight_date: Date to generate insights for

    Returns:
        List of unsaved DailyInsight objects
    """
    from apps.metrics.services import benchmark_service

    insights = []

    # Get cycle time benchmark
    result = benchmark_service.get_benchmark_for_team(team, "cycle_time", days=30)

    if result.get("team_value") is not None and result.get("percentile") is not None:
        percentile = result["percentile"]

        # Elite performance (top 25%)
        if percentile >= 75:
            insights.append(
                DailyInsight(
                    team=team,
                    date=insight_date,
                    category="comparison",
                    priority="low",
                    title=f"Elite performance: Top {100 - percentile}% for cycle time",
                    description=(
                        f"Your team's cycle time of {result['team_value']:.1f}h puts you in "
                        "the elite category compared to industry benchmarks."
                    ),
                    metric_type="cycle_time",
                    metric_value={
                        "value": float(result["team_value"]),
                        "percentile": percentile,
                        "benchmark_p50": float(result["benchmark"]["p50"]),
                    },
                    comparison_period="30_days",
                )
            )
        # Needs improvement (bottom 10%)
        elif percentile <= 10:
            insights.append(
                DailyInsight(
                    team=team,
                    date=insight_date,
                    category="comparison",
                    priority="high",
                    title="Opportunity to improve cycle time",
                    description=(
                        f"Your team's cycle time of {result['team_value']:.1f}h is above the "
                        f"industry median of {result['benchmark']['p50']:.1f}h. "
                        "Consider smaller PRs or async reviews."
                    ),
                    metric_type="cycle_time",
                    metric_value={
                        "value": float(result["team_value"]),
                        "percentile": percentile,
                        "benchmark_p50": float(result["benchmark"]["p50"]),
                    },
                    comparison_period="30_days",
                )
            )
        # Don't generate insights for average performance (between 10-75%)

    return insights


def generate_achievement_insights(team, insight_date):
    """Generate achievement/milestone insights.

    Args:
        team: Team instance
        insight_date: Date to generate insights for

    Returns:
        List of unsaved DailyInsight objects
    """
    insights = []

    # Get all-time stats
    total_prs = PullRequest.objects.filter(team=team, state="merged").count()
    ai_prs = PullRequest.objects.filter(team=team, state="merged", is_ai_assisted=True).count()

    if total_prs == 0:
        return insights

    # AI adoption milestone
    ai_pct = (ai_prs / total_prs) * 100
    for milestone in AI_ADOPTION_MILESTONES:
        if ai_pct >= milestone and ai_pct < milestone + 5:
            insights.append(
                DailyInsight(
                    team=team,
                    date=insight_date,
                    category="action",
                    priority="low",
                    title=f"AI adoption milestone: {milestone}% reached!",
                    description=f"Congratulations! {ai_pct:.0f}% of your PRs are now AI-assisted.",
                    metric_type="ai_adoption",
                    metric_value={
                        "value": float(ai_pct),
                        "milestone": milestone,
                        "total_prs": total_prs,
                        "ai_prs": ai_prs,
                    },
                    comparison_period="all_time",
                )
            )
            break

    # PR count milestone
    for milestone in PR_COUNT_MILESTONES:
        if total_prs >= milestone and total_prs < milestone + 10:
            insights.append(
                DailyInsight(
                    team=team,
                    date=insight_date,
                    category="action",
                    priority="low",
                    title=f"Milestone: {milestone} PRs merged!",
                    description=f"Your team has merged {total_prs} pull requests. Keep up the great work!",
                    metric_type="pr_count",
                    metric_value={
                        "value": total_prs,
                        "milestone": milestone,
                    },
                    comparison_period="all_time",
                )
            )
            break

    return insights


def generate_all_insights(team, insight_date):
    """Generate all insight types and save to database.

    Args:
        team: Team instance
        insight_date: Date to generate insights for

    Returns:
        List of created DailyInsight objects
    """
    # Collect all insights
    all_insights = []
    all_insights.extend(generate_trend_insights(team, insight_date))
    all_insights.extend(generate_benchmark_insights(team, insight_date))
    all_insights.extend(generate_achievement_insights(team, insight_date))

    # Get existing dismissed insights for this date
    dismissed_ids = set(
        DailyInsight.objects.filter(
            team=team,
            date=insight_date,
            is_dismissed=True,
        ).values_list("title", flat=True)
    )

    # Delete non-dismissed insights for this date (to refresh)
    DailyInsight.objects.filter(
        team=team,
        date=insight_date,
        is_dismissed=False,
    ).delete()

    # Save new insights (skip if same title was dismissed)
    created = []
    for insight in all_insights:
        if insight.title not in dismissed_ids:
            insight.save()
            created.append(insight)

    return created
