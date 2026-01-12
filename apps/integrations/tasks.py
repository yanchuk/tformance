"""Celery tasks for integrations.

This module serves as the main entry point for all integration tasks.
All tasks are organized into domain-focused modules in _task_modules/:
- github_sync: Repository and member sync tasks
- metrics: Weekly metrics aggregation and LLM analysis
- pr_data: PR data fetch, surveys, and repository languages
- jira_sync: Jira project and user sync tasks
- slack: Slack surveys, reveals, leaderboards
- copilot: GitHub Copilot metrics sync

All tasks are re-exported here for backward compatibility.
"""

# =============================================================================
# Re-exports from _task_modules/
# =============================================================================

# Copilot tasks
from apps.integrations._task_modules.copilot import (  # noqa: E402
    sync_all_copilot_metrics,
    sync_copilot_metrics_task,
)

# GitHub sync tasks
from apps.integrations._task_modules.github_sync import (  # noqa: E402
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
from apps.integrations._task_modules.jira_sync import (  # noqa: E402
    sync_all_jira_projects_task,
    sync_jira_project_task,
    sync_jira_users_task,
)

# Metrics tasks
from apps.integrations._task_modules.metrics import (  # noqa: E402
    aggregate_all_teams_weekly_metrics_task,
    aggregate_team_weekly_metrics_task,
    queue_llm_analysis_batch_task,
)

# PR data tasks
from apps.integrations._task_modules.pr_data import (  # noqa: E402
    _fetch_pr_core_data_with_graphql_or_rest,
    fetch_pr_complete_data_task,
    post_survey_comment_task,
    refresh_all_repo_languages_task,
    refresh_repo_languages_task,
    update_pr_description_survey_task,
)

# Slack tasks
from apps.integrations._task_modules.slack import (  # noqa: E402
    post_weekly_leaderboards_task,
    schedule_slack_survey_fallback_task,
    send_pr_surveys_task,
    send_reveal_task,
    sync_slack_users_task,
)

# GitHub PR description module (for patch targets like github_pr_description.update_pr_description_with_survey)
from apps.integrations.services import github_pr_description  # noqa: E402, F401

# =============================================================================
# Service re-imports for backward compatibility with test patches
# =============================================================================
from apps.integrations.services.github_sync import sync_repository_incremental  # noqa: E402, F401

# Jira-related services
from apps.integrations.services.jira_sync import sync_project_issues  # noqa: E402, F401
from apps.integrations.services.jira_user_matching import sync_jira_users  # noqa: E402, F401

# Slack-related services
from apps.integrations.services.slack_client import get_slack_client, send_dm  # noqa: E402, F401
from apps.integrations.services.slack_surveys import (  # noqa: E402, F401
    build_author_survey_blocks,
    build_reviewer_survey_blocks,
)
from apps.integrations.services.slack_user_matching import sync_slack_users  # noqa: E402, F401
from apps.metrics.services.aggregation_service import aggregate_team_weekly_metrics  # noqa: E402, F401

# Survey services
from apps.metrics.services.survey_service import (  # noqa: E402, F401
    create_pr_survey,
    create_reviewer_survey,
    get_reviewer_accuracy_stats,
)

# =============================================================================
# Exports
# =============================================================================

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
    "_fetch_pr_core_data_with_graphql_or_rest",
    # Jira tasks
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
