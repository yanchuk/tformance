from django.urls import path

from . import views

app_name = "integrations"

team_urlpatterns = (
    [
        path("", views.integrations_home, name="integrations_home"),
        path("github/connect/", views.github_connect, name="github_connect"),
        path("github/callback/", views.github_callback, name="github_callback"),
        path("github/disconnect/", views.github_disconnect, name="github_disconnect"),
        path("github/select-org/", views.github_select_org, name="github_select_org"),
    ],
    "integrations",
)
