"""Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.

NOTE: This file re-exports all functions from the dashboard/ subpackage for
backward compatibility. All actual implementations are in domain-focused
modules under apps/metrics/services/dashboard/.
"""

# Re-export everything from the dashboard package for backward compatibility
# ruff: noqa: F401 - these imports are re-exports for backward compatibility
from apps.metrics.services.dashboard import (
    # Phase 4: PR metrics (re-exported for backward compatibility)
    PR_SIZE_L_MAX,
    PR_SIZE_M_MAX,
    PR_SIZE_S_MAX,
    PR_SIZE_XS_MAX,
    # Private helpers (re-exported for backward compatibility)
    _apply_repo_filter,
    _avatar_url_from_github_id,
    _compute_initials,
    _get_author_name,
    _get_github_url,
    _get_key_metrics_cache_key,
    _get_merged_prs_in_range,
    _is_valid_category,
    # Phase 3: Review metrics (re-exported for backward compatibility)
    detect_review_bottleneck,
    # Phase 2: Core metrics (re-exported for backward compatibility)
    get_ai_adoption_trend,
    get_ai_bot_review_stats,
    get_ai_category_breakdown,
    get_ai_detected_metrics,
    get_ai_detection_metrics,
    get_ai_detective_leaderboard,
    get_ai_impact_stats,
    get_ai_quality_comparison,
    get_ai_tool_breakdown,
    # Phase 4: CI/CD metrics (re-exported for backward compatibility)
    get_cicd_pass_rate,
    get_copilot_by_member,
    # Phase 4: Copilot metrics (re-exported for backward compatibility)
    get_copilot_metrics,
    get_copilot_trend,
    # Phase 3: Trend metrics (re-exported for backward compatibility)
    get_cycle_time_trend,
    get_deployment_metrics,
    # Phase 4: Tech metrics (re-exported for backward compatibility)
    get_file_category_breakdown,
    get_iteration_metrics,
    # Phase 4: Jira metrics (re-exported for backward compatibility)
    get_jira_sprint_metrics,
    get_key_metrics,
    get_linkage_trend,
    get_monthly_ai_adoption,
    get_monthly_cycle_time_trend,
    get_monthly_pr_count,
    get_monthly_pr_type_trend,
    get_monthly_review_time_trend,
    get_monthly_tech_trend,
    get_needs_attention_prs,
    get_open_prs_stats,
    get_pr_jira_correlation,
    get_pr_size_distribution,
    get_pr_type_breakdown,
    # Phase 4: Velocity metrics (re-exported for backward compatibility)
    get_quality_metrics,
    get_recent_prs,
    get_response_channel_distribution,
    get_response_time_metrics,
    get_revert_hotfix_stats,
    get_review_distribution,
    get_review_time_trend,
    get_reviewer_correlations,
    get_reviewer_workload,
    get_sparkline_data,
    get_story_point_correlation,
    get_team_breakdown,
    get_team_health_metrics,
    get_team_velocity,
    get_tech_breakdown,
    get_trend_comparison,
    get_unlinked_prs,
    get_velocity_comparison,
    get_velocity_trend,
    get_weekly_pr_count,
    get_weekly_pr_type_trend,
    get_weekly_tech_trend,
)

# Cache TTL for dashboard metrics (5 minutes)
DASHBOARD_CACHE_TTL = 300
