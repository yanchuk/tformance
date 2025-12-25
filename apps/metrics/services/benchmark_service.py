"""Benchmark service for comparing team metrics against industry data.

Provides functions to:
- Determine team size bucket based on member count
- Calculate team's percentile ranking against industry benchmarks
- Generate interpretive text for benchmark comparisons
"""

from datetime import timedelta
from decimal import Decimal
from typing import TypedDict

from django.db.models import Avg
from django.utils import timezone

from apps.metrics.models import IndustryBenchmark, PullRequest, TeamMember
from apps.teams.models import Team


class BenchmarkResult(TypedDict):
    """Result of a benchmark comparison."""

    team_value: Decimal | None
    percentile: int
    benchmark: dict
    interpretation: str


# Team size thresholds
TEAM_SIZE_SMALL_MAX = 10
TEAM_SIZE_MEDIUM_MAX = 50
TEAM_SIZE_LARGE_MAX = 200


def get_team_size_bucket(team: Team) -> str:
    """Determine the team size bucket based on member count.

    Args:
        team: Team instance

    Returns:
        One of: 'small', 'medium', 'large', 'enterprise'
    """
    member_count = TeamMember.objects.filter(team=team, is_active=True).count()

    if member_count <= TEAM_SIZE_SMALL_MAX:
        return "small"
    elif member_count <= TEAM_SIZE_MEDIUM_MAX:
        return "medium"
    elif member_count <= TEAM_SIZE_LARGE_MAX:
        return "large"
    else:
        return "enterprise"


def calculate_percentile(value: Decimal, benchmark: IndustryBenchmark) -> int:
    """Calculate what percentile a value falls into.

    For time-based metrics (cycle_time, review_time), lower is better.
    The percentile returned represents "better than X% of teams".

    Args:
        value: The team's metric value
        benchmark: IndustryBenchmark instance with p25, p50, p75, p90

    Returns:
        Integer from 0-100 representing percentile rank
    """
    p25 = float(benchmark.p25)
    p50 = float(benchmark.p50)
    p75 = float(benchmark.p75)
    p90 = float(benchmark.p90)
    val = float(value)

    # For time metrics, lower is better, so lower values = higher percentile
    if val <= p25:
        # Elite: top 25%
        # Interpolate between 75-100 based on how far below p25
        if p25 > 0:
            ratio = val / p25
            return int(75 + (1 - ratio) * 25)
        return 100

    elif val <= p50:
        # High: 50th-75th percentile
        # Interpolate between 50-75
        range_size = p50 - p25
        if range_size > 0:
            position = (val - p25) / range_size
            return int(75 - position * 25)
        return 50

    elif val <= p75:
        # Medium: 25th-50th percentile
        # Interpolate between 25-50
        range_size = p75 - p50
        if range_size > 0:
            position = (val - p50) / range_size
            return int(50 - position * 25)
        return 25

    elif val <= p90:
        # Low: 10th-25th percentile
        # Interpolate between 10-25
        range_size = p90 - p75
        if range_size > 0:
            position = (val - p75) / range_size
            return int(25 - position * 15)
        return 10

    else:
        # Below p90: bottom 10%
        # Interpolate down from 10 towards 0
        if p90 > 0:
            over_ratio = min((val - p90) / p90, 1.0)
            return int(10 - over_ratio * 10)
        return 0


def get_interpretation(value: Decimal, benchmark: IndustryBenchmark) -> str:
    """Get human-readable interpretation of benchmark comparison.

    Args:
        value: The team's metric value
        benchmark: IndustryBenchmark instance

    Returns:
        Interpretation string like "Elite performer" or "Needs improvement"
    """
    val = float(value)
    p25 = float(benchmark.p25)
    p50 = float(benchmark.p50)
    p75 = float(benchmark.p75)
    p90 = float(benchmark.p90)

    if val <= p25:
        return "Elite performer - Top 25%"
    elif val <= p50:
        return "High performer - Top 50%"
    elif val <= p75:
        return "Medium performer - Average range"
    elif val <= p90:
        return "Low performer - Below average"
    else:
        return "Needs improvement - Bottom 10%"


def _get_team_metric_value(team: Team, metric_name: str, days: int = 30) -> Decimal | None:
    """Get the team's current value for a metric.

    Args:
        team: Team instance
        metric_name: One of 'cycle_time', 'review_time', 'pr_count', 'ai_adoption'
        days: Number of days to look back

    Returns:
        Decimal value or None if no data
    """
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)

    prs = PullRequest.objects.filter(
        team=team,
        state="merged",
        merged_at__gte=start_date,
        merged_at__lte=end_date,
    )

    if metric_name == "cycle_time":
        result = prs.aggregate(avg=Avg("cycle_time_hours"))
        return Decimal(str(result["avg"])) if result["avg"] else None

    elif metric_name == "review_time":
        result = prs.aggregate(avg=Avg("review_time_hours"))
        return Decimal(str(result["avg"])) if result["avg"] else None

    elif metric_name == "pr_count":
        # PRs per week
        count = prs.count()
        weeks = max(days / 7, 1)
        return Decimal(str(count / weeks))

    elif metric_name == "ai_adoption":
        total = prs.count()
        if total == 0:
            return None
        ai_count = prs.filter(is_ai_assisted=True).count()
        return Decimal(str((ai_count / total) * 100))

    return None


def get_benchmark_for_team(team: Team, metric_name: str, days: int = 30) -> BenchmarkResult:
    """Get benchmark comparison for a team's metric.

    Args:
        team: Team instance
        metric_name: Metric to compare
        days: Number of days to look back for team data

    Returns:
        BenchmarkResult with team_value, percentile, benchmark data, and interpretation
    """
    size_bucket = get_team_size_bucket(team)
    team_value = _get_team_metric_value(team, metric_name, days)

    try:
        benchmark = (
            IndustryBenchmark.objects.filter(
                metric_name=metric_name,
                team_size_bucket=size_bucket,
            )
            .order_by("-year")
            .first()
        )
    except IndustryBenchmark.DoesNotExist:
        benchmark = None

    if not benchmark or team_value is None:
        return {
            "team_value": team_value,
            "percentile": 50,  # Default to median if no benchmark
            "benchmark": {},
            "interpretation": "Insufficient data for comparison",
        }

    percentile = calculate_percentile(team_value, benchmark)
    interpretation = get_interpretation(team_value, benchmark)

    return {
        "team_value": team_value,
        "percentile": percentile,
        "benchmark": {
            "p25": float(benchmark.p25),
            "p50": float(benchmark.p50),
            "p75": float(benchmark.p75),
            "p90": float(benchmark.p90),
            "source": benchmark.source,
            "year": benchmark.year,
        },
        "interpretation": interpretation,
    }


def get_all_benchmarks_for_team(team: Team, days: int = 30) -> dict[str, BenchmarkResult]:
    """Get benchmark comparisons for all available metrics.

    Args:
        team: Team instance
        days: Number of days to look back for team data

    Returns:
        Dict mapping metric_name to BenchmarkResult
    """
    metrics = ["cycle_time", "review_time", "pr_count", "ai_adoption"]
    results = {}

    for metric in metrics:
        results[metric] = get_benchmark_for_team(team, metric, days)

    return results
