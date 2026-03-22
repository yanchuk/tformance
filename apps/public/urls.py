from django.urls import path

from apps.public.views import analytics_views, chart_views, directory_views, org_views, repo_views

app_name = "public"

urlpatterns = [
    path("", directory_views.directory, name="directory"),
    path("request/", directory_views.request_repo, name="request_repo"),
    path("request/success/", directory_views.request_success, name="request_success"),
    path("industry/<slug:industry>/", directory_views.industry_comparison, name="industry"),
    path("<slug:slug>/analytics/", analytics_views.org_analytics, name="org_analytics"),
    path("<slug:slug>/pull-requests/", org_views.org_pr_list, name="org_pr_list"),
    path("<slug:slug>/pull-requests/table/", org_views.pr_list_table, name="pr_list_table"),
    path("<slug:slug>/charts/combined-trend/", chart_views.public_combined_trend_chart, name="chart_combined_trend"),
    path("<slug:slug>/charts/ai-adoption/", chart_views.public_ai_adoption_chart, name="chart_ai_adoption"),
    path("<slug:slug>/charts/cycle-time/", chart_views.public_cycle_time_chart, name="chart_cycle_time"),
    path("<slug:slug>/charts/ai-quality/", chart_views.public_ai_quality_chart, name="chart_ai_quality"),
    path("<slug:slug>/charts/ai-tools/", chart_views.public_ai_tools_chart, name="chart_ai_tools"),
    path("<slug:slug>/charts/pr-size/", chart_views.public_pr_size_chart, name="chart_pr_size"),
    path(
        "<slug:slug>/charts/review-distribution/",
        chart_views.public_review_distribution_chart,
        name="chart_review_distribution",
    ),
    path("<slug:slug>/cards/metrics/", chart_views.public_key_metrics_cards, name="cards_metrics"),
    path("<slug:slug>/cards/team-health/", chart_views.public_team_health_cards, name="cards_team_health"),
    # Repo-level routes (before org catch-all)
    path("<slug:slug>/repos/<slug:repo_slug>/", repo_views.repo_detail, name="repo_detail"),
    path("<slug:slug>/repos/<slug:repo_slug>/pull-requests/", repo_views.repo_pr_list, name="repo_pr_list"),
    path(
        "<slug:slug>/repos/<slug:repo_slug>/pull-requests/table/",
        repo_views.repo_pr_list_table,
        name="repo_pr_list_table",
    ),
    # Org catch-all (must be last)
    path("<slug:slug>/", org_views.org_detail, name="org_detail"),
]
