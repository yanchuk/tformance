from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("", views.onboarding_start, name="start"),
    path("skip/", views.skip_onboarding, name="skip"),
    path("github/", views.github_connect, name="github_connect"),
    path("org/", views.select_organization, name="select_org"),
    path("repos/", views.select_repositories, name="select_repos"),
    path("repos/fetch/", views.fetch_repos, name="fetch_repos"),
    path("sync/", views.sync_progress, name="sync_progress"),
    path("sync/start/", views.start_sync, name="start_sync"),
    path("sync/status/", views.sync_status, name="sync_status"),
    path("jira/", views.connect_jira, name="connect_jira"),
    path("jira/projects/", views.select_jira_projects, name="select_jira_projects"),
    path("jira/sync-status/", views.jira_sync_status, name="jira_sync_status"),
    path("slack/", views.connect_slack, name="connect_slack"),
    path("complete/", views.onboarding_complete, name="complete"),
]
