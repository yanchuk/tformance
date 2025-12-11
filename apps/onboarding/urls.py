from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("", views.onboarding_start, name="start"),
    path("github/", views.github_connect, name="github_connect"),
    path("github/callback/", views.github_callback, name="github_callback"),
    path("org/", views.select_organization, name="select_org"),
    path("repos/", views.select_repositories, name="select_repos"),
    path("jira/", views.connect_jira, name="connect_jira"),
    path("slack/", views.connect_slack, name="connect_slack"),
    path("complete/", views.onboarding_complete, name="complete"),
]
