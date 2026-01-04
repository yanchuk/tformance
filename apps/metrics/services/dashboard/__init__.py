"""Dashboard service modules.

This package contains domain-focused modules for dashboard metrics.
All public functions are re-exported here for backward compatibility.

Internal helpers are in _helpers.py and should not be imported directly.
"""

# Internal helpers (for use within this package only)
from apps.metrics.services.dashboard._helpers import (
    _apply_repo_filter,
    _avatar_url_from_github_id,
    _calculate_ai_percentage,
    _calculate_ai_percentage_from_detection,
    _calculate_average_response_times,
    _calculate_channel_percentages,
    _compute_initials,
    _filter_by_date_range,
    _get_author_name,
    _get_github_url,
    _get_key_metrics_cache_key,
    _get_merged_prs_in_range,
    _get_metric_trend,
    _get_monthly_metric_trend,
    _is_valid_category,
)

# Phase 2: Core metrics
from apps.metrics.services.dashboard.ai_metrics import (
    get_ai_adoption_trend,
    get_ai_bot_review_stats,
    get_ai_category_breakdown,
    get_ai_detected_metrics,
    get_ai_detection_metrics,
    get_ai_detective_leaderboard,
    get_ai_impact_stats,
    get_ai_quality_comparison,
    get_ai_tool_breakdown,
)

# Phase 4: CI/CD metrics
from apps.metrics.services.dashboard.cicd_metrics import (
    get_cicd_pass_rate,
    get_deployment_metrics,
)

# Phase 4: Copilot metrics
from apps.metrics.services.dashboard.copilot_metrics import (
    get_copilot_metrics,
    get_copilot_trend,
)

# Phase 4: Jira metrics
from apps.metrics.services.dashboard.jira_metrics import (
    get_jira_sprint_metrics,
    get_linkage_trend,
    get_pr_jira_correlation,
    get_story_point_correlation,
)
from apps.metrics.services.dashboard.key_metrics import get_key_metrics

# Phase 4: PR metrics
from apps.metrics.services.dashboard.pr_metrics import (
    PR_SIZE_L_MAX,
    PR_SIZE_M_MAX,
    PR_SIZE_S_MAX,
    PR_SIZE_XS_MAX,
    get_iteration_metrics,
    get_monthly_pr_type_trend,
    get_needs_attention_prs,
    get_open_prs_stats,
    get_pr_size_distribution,
    get_pr_type_breakdown,
    get_recent_prs,
    get_revert_hotfix_stats,
    get_unlinked_prs,
    get_weekly_pr_type_trend,
)

# Phase 3: Trend and review metrics
from apps.metrics.services.dashboard.review_metrics import (
    detect_review_bottleneck,
    get_response_channel_distribution,
    get_response_time_metrics,
    get_review_distribution,
    get_reviewer_correlations,
    get_reviewer_workload,
)
from apps.metrics.services.dashboard.team_metrics import (
    get_copilot_by_member,
    get_team_breakdown,
    get_team_velocity,
)

# Phase 4: Tech metrics
from apps.metrics.services.dashboard.tech_metrics import (
    get_file_category_breakdown,
    get_monthly_tech_trend,
    get_tech_breakdown,
    get_weekly_tech_trend,
)
from apps.metrics.services.dashboard.trend_metrics import (
    get_cycle_time_trend,
    get_monthly_ai_adoption,
    get_monthly_cycle_time_trend,
    get_monthly_pr_count,
    get_monthly_review_time_trend,
    get_review_time_trend,
    get_sparkline_data,
    get_trend_comparison,
    get_velocity_trend,
    get_weekly_pr_count,
)

# Phase 4: Velocity metrics
from apps.metrics.services.dashboard.velocity_metrics import (
    get_quality_metrics,
    get_team_health_metrics,
    get_velocity_comparison,
)

__all__ = [
    # Private helpers (for internal package use)
    "_apply_repo_filter",
    "_avatar_url_from_github_id",
    "_calculate_ai_percentage",
    "_calculate_ai_percentage_from_detection",
    "_calculate_average_response_times",
    "_calculate_channel_percentages",
    "_compute_initials",
    "_filter_by_date_range",
    "_get_author_name",
    "_get_github_url",
    "_get_key_metrics_cache_key",
    "_get_merged_prs_in_range",
    "_get_metric_trend",
    "_get_monthly_metric_trend",
    "_is_valid_category",
    # Key metrics
    "get_key_metrics",
    # AI metrics
    "get_ai_adoption_trend",
    "get_ai_bot_review_stats",
    "get_ai_category_breakdown",
    "get_ai_detected_metrics",
    "get_ai_detection_metrics",
    "get_ai_detective_leaderboard",
    "get_ai_impact_stats",
    "get_ai_quality_comparison",
    "get_ai_tool_breakdown",
    # Team metrics
    "get_copilot_by_member",
    "get_team_breakdown",
    "get_team_velocity",
    # Phase 3: Trend metrics
    "get_cycle_time_trend",
    "get_monthly_ai_adoption",
    "get_monthly_cycle_time_trend",
    "get_monthly_pr_count",
    "get_monthly_review_time_trend",
    "get_review_time_trend",
    "get_sparkline_data",
    "get_trend_comparison",
    "get_velocity_trend",
    "get_weekly_pr_count",
    # Phase 3: Review metrics
    "detect_review_bottleneck",
    "get_response_channel_distribution",
    "get_response_time_metrics",
    "get_review_distribution",
    "get_reviewer_correlations",
    "get_reviewer_workload",
    # Phase 4: PR metrics
    "PR_SIZE_L_MAX",
    "PR_SIZE_M_MAX",
    "PR_SIZE_S_MAX",
    "PR_SIZE_XS_MAX",
    "get_iteration_metrics",
    "get_monthly_pr_type_trend",
    "get_needs_attention_prs",
    "get_open_prs_stats",
    "get_pr_size_distribution",
    "get_pr_type_breakdown",
    "get_recent_prs",
    "get_revert_hotfix_stats",
    "get_unlinked_prs",
    "get_weekly_pr_type_trend",
    # Phase 4: Copilot metrics
    "get_copilot_metrics",
    "get_copilot_trend",
    # Phase 4: CI/CD metrics
    "get_cicd_pass_rate",
    "get_deployment_metrics",
    # Phase 4: Tech metrics
    "get_file_category_breakdown",
    "get_monthly_tech_trend",
    "get_tech_breakdown",
    "get_weekly_tech_trend",
    # Phase 4: Velocity metrics
    "get_quality_metrics",
    "get_team_health_metrics",
    "get_velocity_comparison",
    # Phase 4: Jira metrics
    "get_jira_sprint_metrics",
    "get_linkage_trend",
    "get_pr_jira_correlation",
    "get_story_point_correlation",
]
