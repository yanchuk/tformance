from django.urls import path
from django.views.generic import TemplateView

from . import views

app_name = "web"
urlpatterns = [
    path("", views.home, name="home"),
    path("report/", views.ai_impact_report, name="ai_impact_report"),
    path("report/llms.md", views.report_llms_data, name="report_llms_data"),
    path("terms/", TemplateView.as_view(template_name="web/terms.html"), name="terms"),
    path("privacy/", TemplateView.as_view(template_name="web/privacy.html"), name="privacy"),
    path("robots.txt", TemplateView.as_view(template_name="robots.txt", content_type="text/plain"), name="robots.txt"),
    path("llms.txt", TemplateView.as_view(template_name="llms.txt", content_type="text/plain"), name="llms.txt"),
    # these views are just for testing error pages
    # actual error handling is handled by Django: https://docs.djangoproject.com/en/stable/ref/views/#error-views
    path("400/", TemplateView.as_view(template_name="400.html"), name="400"),
    path("403/", TemplateView.as_view(template_name="403.html"), name="403"),
    path("404/", TemplateView.as_view(template_name="404.html"), name="404"),
    path("429/", TemplateView.as_view(template_name="429.html"), name="429"),
    path("500/", TemplateView.as_view(template_name="500.html"), name="500"),
    path("simulate_error/", views.simulate_error),
    path("health/", views.HealthCheck.as_view(), name="health_check"),
    path("webhooks/github/", views.github_webhook, name="github_webhook"),
    path("webhooks/github-app/", views.github_app_webhook, name="github_app_webhook"),
    # Survey views (public, token-based access)
    path("survey/<str:token>/", views.survey_landing, name="survey_landing"),
    path("survey/<str:token>/author/", views.survey_author, name="survey_author"),
    path("survey/<str:token>/reviewer/", views.survey_reviewer, name="survey_reviewer"),
    path("survey/<str:token>/submit/", views.survey_submit, name="survey_submit"),
    path("survey/<str:token>/complete/", views.survey_complete, name="survey_complete"),
]


team_urlpatterns = (
    [
        path("", views.team_home, name="home"),
        path("sync-indicator/", views.sync_indicator_partial, name="sync_indicator"),
    ],
    "web_team",
)
