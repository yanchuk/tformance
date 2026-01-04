"""CI/CD metrics for dashboard.

Functions for CI/CD pass rates and deployment metrics (DORA).
"""

from datetime import date
from decimal import Decimal

from django.db.models import Count, Q

from apps.metrics.models import Deployment, PRCheckRun
from apps.teams.models import Team
from apps.utils.date_utils import end_of_day, start_of_day


def get_cicd_pass_rate(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get CI/CD pass rate metrics for a team within a date range.

    Aggregates check run results to show overall CI/CD health and
    identifies the most problematic checks.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_runs (int): Total check runs
            - pass_rate (Decimal): Percentage of successful runs (0.00 to 100.00)
            - success_count (int): Number of successful runs
            - failure_count (int): Number of failed runs
            - top_failing_checks (list): Top 5 checks with highest failure rates
    """
    check_runs = PRCheckRun.objects.filter(
        team=team,
        pull_request__merged_at__gte=start_of_day(start_date),
        pull_request__merged_at__lte=end_of_day(end_date),
        status="completed",
    )
    if repo:
        check_runs = check_runs.filter(pull_request__github_repo=repo)

    total_runs = check_runs.count()
    success_count = check_runs.filter(conclusion="success").count()
    failure_count = check_runs.filter(conclusion="failure").count()

    pass_rate = Decimal(str(round(success_count * 100.0 / total_runs, 2))) if total_runs > 0 else Decimal("0.00")

    # Get top failing checks
    check_stats = (
        check_runs.values("name")
        .annotate(
            total=Count("id"),
            failures=Count("id", filter=Q(conclusion="failure")),
        )
        .filter(failures__gt=0)
        .order_by("-failures")[:5]
    )

    top_failing_checks = [
        {
            "name": stat["name"],
            "total": stat["total"],
            "failures": stat["failures"],
            "failure_rate": Decimal(str(round(stat["failures"] * 100.0 / stat["total"], 2))),
        }
        for stat in check_stats
    ]

    return {
        "total_runs": total_runs,
        "pass_rate": pass_rate,
        "success_count": success_count,
        "failure_count": failure_count,
        "top_failing_checks": top_failing_checks,
    }


def get_deployment_metrics(team: Team, start_date: date, end_date: date, repo: str | None = None) -> dict:
    """Get DORA-style deployment metrics for a team within a date range.

    Calculates deployment frequency and success rate, key DevOps metrics.

    Args:
        team: Team instance
        start_date: Start date (inclusive)
        end_date: End date (inclusive)
        repo: Optional repository to filter by (owner/repo format)

    Returns:
        dict with keys:
            - total_deployments (int): Total deployments
            - production_deployments (int): Production deployments
            - success_rate (Decimal): Percentage of successful deployments
            - deployments_per_week (Decimal): Average deployments per week
            - by_environment (list): Breakdown by environment
    """
    deployments = Deployment.objects.filter(
        team=team,
        deployed_at__gte=start_of_day(start_date),
        deployed_at__lte=end_of_day(end_date),
    )
    if repo:
        deployments = deployments.filter(github_repo=repo)

    total = deployments.count()
    production = deployments.filter(environment="production").count()
    successful = deployments.filter(status="success").count()

    success_rate = Decimal(str(round(successful * 100.0 / total, 2))) if total > 0 else Decimal("0.00")

    # Calculate deployments per week
    days = (end_date - start_date).days or 1
    weeks = max(days / 7, 1)
    deployments_per_week = Decimal(str(round(total / weeks, 2)))

    # Breakdown by environment
    by_environment = (
        deployments.values("environment")
        .annotate(
            total=Count("id"),
            successful=Count("id", filter=Q(status="success")),
        )
        .order_by("-total")
    )

    env_breakdown = [
        {
            "environment": env["environment"],
            "total": env["total"],
            "successful": env["successful"],
            "success_rate": Decimal(str(round(env["successful"] * 100.0 / env["total"], 2)))
            if env["total"] > 0
            else Decimal("0.00"),
        }
        for env in by_environment
    ]

    return {
        "total_deployments": total,
        "production_deployments": production,
        "success_rate": success_rate,
        "deployments_per_week": deployments_per_week,
        "by_environment": env_breakdown,
    }
