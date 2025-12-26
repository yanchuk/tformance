from django.urls import path

from . import views
from .webhooks import slack_interactions

# Non-team URLs (webhooks, etc.) - no namespace needed for webhooks
urlpatterns = [
    path("webhooks/slack/interactions/", slack_interactions.slack_interactions, name="slack_interactions_webhook"),
]

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
        path("github/repos/<int:repo_id>/progress/", views.github_repo_sync_progress, name="github_repo_sync_progress"),
        path("copilot/sync/", views.copilot_sync, name="copilot_sync"),
        path("jira/connect/", views.jira_connect, name="jira_connect"),
        path("jira/callback/", views.jira_callback, name="jira_callback"),
        path("jira/disconnect/", views.jira_disconnect, name="jira_disconnect"),
        path("jira/select-site/", views.jira_select_site, name="jira_select_site"),
        path("jira/projects/", views.jira_projects_list, name="jira_projects_list"),
        path("jira/projects/toggle/", views.jira_project_toggle, name="jira_project_toggle"),
        path("slack/connect/", views.slack_connect, name="slack_connect"),
        path("slack/callback/", views.slack_callback, name="slack_callback"),
        path("slack/disconnect/", views.slack_disconnect, name="slack_disconnect"),
        path("slack/settings/", views.slack_settings, name="slack_settings"),
    ],
    "integrations",
)
