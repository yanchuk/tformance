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
        path("charts/review-time/", views.review_time_chart, name="chart_review_time"),
        path("charts/pr-size/", views.pr_size_chart, name="chart_pr_size"),
        path("charts/review-distribution/", views.review_distribution_chart, name="chart_review_distribution"),
        path("charts/copilot-trend/", views.copilot_trend_chart, name="chart_copilot_trend"),
        # Card partials
        path("cards/metrics/", views.key_metrics_cards, name="cards_metrics"),
        path("cards/revert-rate/", views.revert_rate_card, name="cards_revert_rate"),
        path("cards/copilot/", views.copilot_metrics_card, name="cards_copilot"),
        # Table partials
        path("tables/breakdown/", views.team_breakdown_table, name="table_breakdown"),
        path("tables/leaderboard/", views.leaderboard_table, name="table_leaderboard"),
        path("tables/recent-prs/", views.recent_prs_table, name="table_recent_prs"),
        path("tables/unlinked-prs/", views.unlinked_prs_table, name="table_unlinked_prs"),
        path("tables/reviewer-workload/", views.reviewer_workload_table, name="table_reviewer_workload"),
        path("tables/copilot-members/", views.copilot_members_table, name="table_copilot_members"),
    ],
    "metrics",
)
