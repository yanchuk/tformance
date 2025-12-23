from django.urls import path

from . import views

app_name = "metrics"

urlpatterns = []

team_urlpatterns = (
    [
        path("", views.home, name="metrics_home"),
        path("dashboard/", views.dashboard_redirect, name="dashboard_redirect"),
        path("overview/", views.cto_overview, name="cto_overview"),
        path("dashboard/team/", views.team_dashboard, name="team_dashboard"),
        # Insights
        path("insights/<int:insight_id>/dismiss/", views.dismiss_insight, name="dismiss_insight"),
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
        path("cards/iteration-metrics/", views.iteration_metrics_card, name="cards_iteration_metrics"),
        # Table partials
        path("tables/breakdown/", views.team_breakdown_table, name="table_breakdown"),
        path("tables/leaderboard/", views.leaderboard_table, name="table_leaderboard"),
        path("tables/recent-prs/", views.recent_prs_table, name="table_recent_prs"),
        path("tables/unlinked-prs/", views.unlinked_prs_table, name="table_unlinked_prs"),
        path("tables/reviewer-workload/", views.reviewer_workload_table, name="table_reviewer_workload"),
        path("tables/copilot-members/", views.copilot_members_table, name="table_copilot_members"),
        path("tables/reviewer-correlations/", views.reviewer_correlations_table, name="table_reviewer_correlations"),
        # New metrics sections
        path("cards/cicd-pass-rate/", views.cicd_pass_rate_card, name="cards_cicd_pass_rate"),
        path("cards/deployments/", views.deployment_metrics_card, name="cards_deployments"),
        path("cards/file-categories/", views.file_category_card, name="cards_file_categories"),
        # AI Detection metrics (from content analysis)
        path("cards/ai-detected/", views.ai_detected_metrics_card, name="cards_ai_detected"),
        path("charts/ai-tools/", views.ai_tool_breakdown_chart, name="chart_ai_tools"),
        path("cards/ai-bot-reviews/", views.ai_bot_reviews_card, name="cards_ai_bot_reviews"),
        # Survey channel metrics
        path("cards/survey-channels/", views.survey_channel_distribution_card, name="cards_survey_channels"),
        path("cards/survey-ai-detection/", views.survey_ai_detection_card, name="cards_survey_ai_detection"),
        path("cards/survey-response-time/", views.survey_response_time_card, name="cards_survey_response_time"),
        # Pull Requests data explorer
        path("pull-requests/", views.pr_list, name="pr_list"),
        path("pull-requests/table/", views.pr_list_table, name="pr_list_table"),
        path("pull-requests/export/", views.pr_list_export, name="pr_list_export"),
    ],
    "metrics",
)
