"""Celery tasks for integrations.

This package contains domain-focused task modules:
- github_sync: Repository and member sync tasks
- metrics: Weekly metrics aggregation and LLM analysis
- pr_data: PR data fetch, surveys, and repository languages

All tasks are re-exported here for Celery autodiscover compatibility.
"""

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
]
