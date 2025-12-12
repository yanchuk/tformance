from django.urls import path

from . import views

app_name = "metrics"

urlpatterns = []

team_urlpatterns = (
    [
        path("", views.home, name="metrics_home"),
        path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
        path("dashboard/cto/", views.cto_overview, name="cto_overview"),
        path("dashboard/team/", views.team_dashboard, name="team_dashboard"),
        # Chart partials
        path("charts/ai-adoption/", views.ai_adoption_chart, name="chart_ai_adoption"),
        path("charts/ai-quality/", views.ai_quality_chart, name="chart_ai_quality"),
        path("charts/cycle-time/", views.cycle_time_chart, name="chart_cycle_time"),
        # Card partials
        path("cards/metrics/", views.key_metrics_cards, name="cards_metrics"),
        # Table partials
        path("tables/breakdown/", views.team_breakdown_table, name="table_breakdown"),
        path("tables/leaderboard/", views.leaderboard_table, name="table_leaderboard"),
    ],
    "metrics",
)
