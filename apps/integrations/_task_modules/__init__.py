"""Celery tasks for integrations.

This package contains domain-focused task modules:
- github_sync: Repository and member sync tasks
- metrics: Weekly metrics aggregation and LLM analysis
- pr_data: PR data fetch, surveys, and repository languages
- jira_sync: Jira project and user sync tasks
- slack: Slack surveys, reveals, leaderboards
- copilot: GitHub Copilot metrics sync

All tasks are re-exported here for Celery autodiscover compatibility.
"""

# Copilot tasks
from apps.integrations._task_modules.copilot import (
    sync_all_copilot_metrics,
    sync_copilot_metrics_task,
)

# GitHub sync tasks
from apps.integrations._task_modules.github_sync import (
    _filter_prs_by_days,
    _sync_incremental_with_graphql_or_rest,
    _sync_members_with_graphql_or_rest,
    _sync_with_graphql_or_rest,
    create_repository_webhook_task,
    sync_all_github_members_task,
    sync_all_repositories_task,
    sync_full_history_task,
    sync_github_app_members_task,
    sync_github_members_task,
    sync_historical_data_task,
    sync_quick_data_task,
    sync_repository_initial_task,
    sync_repository_manual_task,
    sync_repository_task,
)

# Jira sync tasks
from apps.integrations._task_modules.jira_sync import (
    sync_all_jira_projects_task,
    sync_jira_project_task,
    sync_jira_users_task,
)

# Metrics tasks
from apps.integrations._task_modules.metrics import (
    aggregate_all_teams_weekly_metrics_task,
    aggregate_team_weekly_metrics_task,
    queue_llm_analysis_batch_task,
)

# PR data tasks
from apps.integrations._task_modules.pr_data import (
    _fetch_pr_core_data_with_graphql_or_rest,
    fetch_pr_complete_data_task,
    post_survey_comment_task,
    refresh_all_repo_languages_task,
    refresh_repo_languages_task,
    update_pr_description_survey_task,
)

# Slack tasks
from apps.integrations._task_modules.slack import (
    post_weekly_leaderboards_task,
    schedule_slack_survey_fallback_task,
    send_pr_surveys_task,
    send_reveal_task,
    sync_slack_users_task,
)

__all__ = [
    # GitHub sync tasks
    "sync_repository_task",
    "create_repository_webhook_task",
    "sync_repository_initial_task",
    "sync_repository_manual_task",
    "sync_all_repositories_task",
    "sync_github_members_task",
    "sync_all_github_members_task",
    "sync_github_app_members_task",
    "sync_quick_data_task",
    "sync_full_history_task",
    "sync_historical_data_task",
    # GitHub sync helpers
    "_sync_with_graphql_or_rest",
    "_sync_incremental_with_graphql_or_rest",
    "_sync_members_with_graphql_or_rest",
    "_filter_prs_by_days",
    # Metrics tasks
    "aggregate_team_weekly_metrics_task",
    "aggregate_all_teams_weekly_metrics_task",
    "queue_llm_analysis_batch_task",
    # PR data tasks
    "fetch_pr_complete_data_task",
    "post_survey_comment_task",
    "update_pr_description_survey_task",
    "refresh_repo_languages_task",
    "refresh_all_repo_languages_task",
    # PR data helpers
    "_fetch_pr_core_data_with_graphql_or_rest",
    # Jira sync tasks
    "sync_jira_project_task",
    "sync_all_jira_projects_task",
    "sync_jira_users_task",
    # Slack tasks
    "send_pr_surveys_task",
    "send_reveal_task",
    "sync_slack_users_task",
    "post_weekly_leaderboards_task",
    "schedule_slack_survey_fallback_task",
    # Copilot tasks
    "sync_copilot_metrics_task",
    "sync_all_copilot_metrics",
]
