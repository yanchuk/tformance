"""Metrics views package."""

from apps.metrics.views.chart_views import (
    ai_adoption_chart,
    ai_quality_chart,
    cycle_time_chart,
    key_metrics_cards,
    leaderboard_table,
    recent_prs_table,
    review_distribution_chart,
    team_breakdown_table,
)
from apps.metrics.views.dashboard_views import cto_overview, dashboard_redirect, home, team_dashboard

__all__ = [
    "ai_adoption_chart",
    "ai_quality_chart",
    "cycle_time_chart",
    "key_metrics_cards",
    "team_breakdown_table",
    "leaderboard_table",
    "review_distribution_chart",
    "recent_prs_table",
    "home",
    "dashboard_redirect",
    "cto_overview",
    "team_dashboard",
]
