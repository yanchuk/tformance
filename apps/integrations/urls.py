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
        path("github/members/", views.github_members, name="github_members"),
        path("github/members/sync/", views.github_members_sync, name="github_members_sync"),
        path("github/members/<int:member_id>/toggle/", views.github_member_toggle, name="github_member_toggle"),
        path("github/repos/", views.github_repos, name="github_repos"),
        path("github/repos/<int:repo_id>/toggle/", views.github_repo_toggle, name="github_repo_toggle"),
        path("github/repos/<int:repo_id>/sync/", views.github_repo_sync, name="github_repo_sync"),
        path("jira/connect/", views.jira_connect, name="jira_connect"),
        path("jira/callback/", views.jira_callback, name="jira_callback"),
        path("jira/disconnect/", views.jira_disconnect, name="jira_disconnect"),
        path("jira/select-site/", views.jira_select_site, name="jira_select_site"),
    ],
    "integrations",
)
