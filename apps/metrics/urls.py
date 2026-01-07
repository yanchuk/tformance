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
        path("charts/jira-linkage/", views.jira_linkage_chart, name="jira_linkage_chart"),
        path("charts/sp-correlation/", views.sp_correlation_chart, name="sp_correlation_chart"),
        path("charts/velocity-trend/", views.velocity_trend_chart, name="velocity_trend_chart"),
        # Card partials
        path("cards/metrics/", views.key_metrics_cards, name="cards_metrics"),
        path("cards/revert-rate/", views.revert_rate_card, name="cards_revert_rate"),
        path("cards/copilot/", views.copilot_metrics_card, name="cards_copilot"),
        path("cards/copilot-seats/", views.copilot_seat_stats_card, name="cards_copilot_seats"),
        path("cards/copilot-languages/", views.copilot_language_chart, name="cards_copilot_languages"),
        path("cards/copilot-editors/", views.copilot_editor_chart, name="cards_copilot_editors"),
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
        # Analytics pages
        path("analytics/", views.analytics_overview, name="analytics_overview"),
        path("analytics/ai-adoption/", views.analytics_ai_adoption, name="analytics_ai_adoption"),
        path("analytics/delivery/", views.analytics_delivery, name="analytics_delivery"),
        path("analytics/quality/", views.analytics_quality, name="analytics_quality"),
        path("analytics/team/", views.analytics_team, name="analytics_team"),
        # Trends pages
        path("analytics/trends/", views.trends_overview, name="trends_overview"),
        path("charts/trend/", views.trend_chart_data, name="chart_trend"),
        path("charts/wide-trend/", views.wide_trend_chart, name="chart_wide_trend"),
        path("charts/pr-type-breakdown/", views.pr_type_breakdown_chart, name="chart_pr_type_breakdown"),
        path("charts/tech-breakdown/", views.tech_breakdown_chart, name="chart_tech_breakdown"),
        # Benchmarks API
        path("api/benchmarks/<str:metric>/", views.benchmark_data, name="benchmark_data"),
        path("panels/benchmark/<str:metric>/", views.benchmark_panel, name="benchmark_panel"),
        # Dashboard partials (new unified dashboard)
        path("partials/needs-attention/", views.needs_attention_view, name="needs_attention"),
        path("partials/ai-impact/", views.ai_impact_view, name="ai_impact"),
        path("partials/team-velocity/", views.team_velocity_view, name="team_velocity"),
        path("partials/engineering-insights/", views.engineering_insights, name="engineering_insights"),
        path("partials/engineering-insights/refresh/", views.refresh_insight, name="refresh_insight"),
        path("partials/background-progress/", views.background_progress, name="background_progress"),
    ],
    "metrics",
)
