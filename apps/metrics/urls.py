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
    ],
    "metrics",
)
