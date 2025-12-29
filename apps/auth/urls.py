"""URL patterns for unified OAuth callbacks."""

from django.urls import path

from . import views

app_name = "tformance_auth"

urlpatterns = [
    path("github/login/", views.github_login, name="github_login"),
    path("github/callback/", views.github_callback, name="github_callback"),
    path("jira/callback/", views.jira_callback, name="jira_callback"),
    path("slack/callback/", views.slack_callback, name="slack_callback"),
]
