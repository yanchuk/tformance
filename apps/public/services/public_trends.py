"""Combined trend and correlation builders for public pages.

Reuses existing trend services from apps/metrics -- does NOT create
separate ORM queries. Aligns weekly data for dual-axis Chart.js rendering.
"""

import logging
import statistics
from datetime import date

from apps.metrics.services.dashboard.ai_metrics import get_ai_adoption_trend
from apps.metrics.services.dashboard.trend_metrics import get_cycle_time_trend, get_review_time_trend
from apps.public.constants import (
    CORRELATION_MODERATE_NEGATIVE,
    CORRELATION_MODERATE_POSITIVE,
    CORRELATION_STRONG_NEGATIVE,
    CORRELATION_STRONG_POSITIVE,
    MIN_CORRELATION_WEEKS,
)
from apps.teams.models import Team

logger = logging.getLogger(__name__)


def build_combined_trend(
    team: Team,
    start_date: date,
    end_date: date,
    secondary: str = "cycle_time",
    repo: str | None = None,
) -> dict:
    """Build aligned dual-axis trend data for Chart.js.

    Args:
        team: Team instance for data queries.
        start_date: Start of trend window.
        end_date: End of trend window.
        secondary: "cycle_time" or "review_time" for the second axis.
        repo: Optional repo filter (owner/repo format).

    Returns:
        {
            "labels": ["2026-01-05", ...],
            "datasets": {
                "ai_adoption": {"values": [...], "label": "AI Adoption %", "yAxisID": "y"},
                "<secondary>": {"values": [...], "label": "...", "yAxisID": "y1"},
            }
        }
    """
    ai_data = get_ai_adoption_trend(team, start_date, end_date, repo=repo)

    if secondary == "review_time":
        delivery_data = get_review_time_trend(team, start_date, end_date, repo=repo)
        delivery_label = "Median Review Time (h)"
    else:
        delivery_data = get_cycle_time_trend(team, start_date, end_date, repo=repo)
        delivery_label = "Median Cycle Time (h)"

    # Build lookup dicts keyed by week string
    ai_by_week = {row["week"]: row["value"] for row in ai_data}
    delivery_by_week = {row["week"]: row["value"] for row in delivery_data}

    # Union of all weeks, sorted
    all_weeks = sorted(set(ai_by_week.keys()) | set(delivery_by_week.keys()))

    return {
        "labels": all_weeks,
        "datasets": {
            "ai_adoption": {
                "values": [ai_by_week.get(w) for w in all_weeks],
                "label": "AI Adoption %",
                "yAxisID": "y",
            },
            secondary: {
                "values": [delivery_by_week.get(w) for w in all_weeks],
                "label": delivery_label,
                "yAxisID": "y1",
            },
        },
    }


def compute_weekly_correlation(
    ai_values: list[float],
    delivery_values: list[float],
    min_weeks: int = MIN_CORRELATION_WEEKS,
) -> float | None:
    """Compute Pearson correlation between two weekly series.

    Args:
        ai_values: Weekly AI adoption percentages.
        delivery_values: Weekly delivery metric values (cycle/review time).
        min_weeks: Minimum data points required (default 6).

    Returns:
        Pearson r value, or None if insufficient data or zero-variance series.
    """
    if len(ai_values) < min_weeks or len(delivery_values) < min_weeks:
        return None

    # Pair up values (use min length for safety)
    n = min(len(ai_values), len(delivery_values))
    ai = ai_values[:n]
    delivery = delivery_values[:n]

    try:
        return statistics.correlation(ai, delivery)
    except statistics.StatisticsError:
        # Zero-variance series (e.g., all 0% AI adoption)
        return None


def classify_correlation(r: float) -> str:
    """Classify a Pearson r value into a human-readable label.

    Thresholds:
        r <= -0.6: strong negative
        -0.6 < r <= -0.3: moderate negative
        -0.3 < r < 0.3: weak or no clear relationship
        0.3 <= r < 0.6: moderate positive
        r >= 0.6: strong positive
    """
    if r <= CORRELATION_STRONG_NEGATIVE:
        return "strong negative"
    elif r <= CORRELATION_MODERATE_NEGATIVE:
        return "moderate negative"
    elif r < CORRELATION_MODERATE_POSITIVE:
        return "weak or no clear relationship"
    elif r < CORRELATION_STRONG_POSITIVE:
        return "moderate positive"
    else:
        return "strong positive"


def build_correlation_scatter(
    team: Team,
    start_date: date,
    end_date: date,
    repo: str | None = None,
) -> dict:
    """Build scatter plot data with correlation analysis.

    Returns:
        {
            "points": [{"x": ai_pct, "y": cycle_time, "week": "..."}, ...],
            "r_value": float | None,
            "classification": str | None,
        }
    """
    ai_data = get_ai_adoption_trend(team, start_date, end_date, repo=repo)
    delivery_data = get_cycle_time_trend(team, start_date, end_date, repo=repo)

    ai_by_week = {row["week"]: row["value"] for row in ai_data}
    delivery_by_week = {row["week"]: row["value"] for row in delivery_data}

    # Only include weeks present in both series
    common_weeks = sorted(set(ai_by_week.keys()) & set(delivery_by_week.keys()))

    points = [{"x": ai_by_week[w], "y": delivery_by_week[w], "week": w} for w in common_weeks]

    ai_values = [p["x"] for p in points]
    delivery_values = [p["y"] for p in points]

    r = compute_weekly_correlation(ai_values, delivery_values)

    return {
        "points": points,
        "r_value": r,
        "classification": classify_correlation(r) if r is not None else None,
    }
