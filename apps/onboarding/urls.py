from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("", views.onboarding_start, name="start"),
    path("skip/", views.skip_onboarding, name="skip"),
    path("github/", views.github_connect, name="github_connect"),
    path("org/", views.select_organization, name="select_org"),
    path("repos/", views.select_repositories, name="select_repos"),
    path("sync/", views.sync_progress, name="sync_progress"),
    path("sync/start/", views.start_sync, name="start_sync"),
    path("jira/", views.connect_jira, name="connect_jira"),
    path("jira/projects/", views.select_jira_projects, name="select_jira_projects"),
    path("slack/", views.connect_slack, name="connect_slack"),
    path("complete/", views.onboarding_complete, name="complete"),
]
