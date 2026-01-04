# Dashboard Service Split - Context

**Last Updated:** 2026-01-04

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/dashboard_service.py` | Current monolithic file (3,712 lines) |
| `apps/metrics/tests/dashboard/` | Existing test suite (25+ files) |
| `apps/metrics/services/dashboard/__init__.py` | Target: Re-exports module |
| `apps/metrics/constants.py` | PR size constants (already extracted) |

## Function Distribution

### _helpers.py (Private Utilities)
```python
_apply_repo_filter          # Line 51 - Filter queryset by repo
_get_merged_prs_in_range    # Line 69 - Common query pattern
_calculate_ai_percentage    # Line 90 - Survey-based AI %
_calculate_ai_percentage_from_detection  # Line 106 - Detection-based AI %
_get_github_url             # Line 129 - Construct PR URL
_get_author_name            # Line 141 - Author display name
_compute_initials           # Line 153 - 2-letter initials
_avatar_url_from_github_id  # Line 170 - GitHub avatar URL
_get_key_metrics_cache_key  # Line 187 - Cache key generator
_get_metric_trend           # Line 337 - Calculate trend data
_filter_by_date_range       # Line 1553 - Date range filter
_calculate_channel_percentages  # Line 1574 - Channel stats
_calculate_average_response_times  # Line 1736 - Response time calc
_get_monthly_metric_trend   # Line 1863 - Monthly trend calc
_is_valid_category          # Line 2499 - Category validation
```

### key_metrics.py
```python
get_key_metrics             # Line 192 - Core KPIs for dashboard
```

### ai_metrics.py
```python
get_ai_adoption_trend       # Line 267
get_ai_quality_comparison   # Line 306
get_ai_detective_leaderboard  # Line 527
get_ai_detected_metrics     # Line 1361
get_ai_tool_breakdown       # Line 1399
get_ai_category_breakdown   # Line 1444
get_ai_bot_review_stats     # Line 1500
get_ai_detection_metrics    # Line 1666
get_ai_impact_stats         # Line 2810
```

### team_metrics.py
```python
get_team_breakdown          # Line 406
get_copilot_by_member       # Line 1096
get_team_velocity           # Line 2919
```

### review_metrics.py
```python
get_review_distribution     # Line 574
get_review_time_trend       # Line 631
get_reviewer_workload       # Line 844
get_reviewer_correlations   # Line 1059
detect_review_bottleneck    # Line 2983
```

### pr_metrics.py
```python
get_cycle_time_trend        # Line 389
get_recent_prs              # Line 648
get_revert_hotfix_stats     # Line 713
get_pr_size_distribution    # Line 756
get_unlinked_prs            # Line 806
get_iteration_metrics       # Line 1009
get_pr_type_breakdown       # Line 2319
get_monthly_pr_type_trend   # Line 2375
get_weekly_pr_type_trend    # Line 2437
get_needs_attention_prs     # Line 2711
```

### copilot_metrics.py
```python
get_copilot_metrics         # Line 899
get_copilot_trend           # Line 952
```

### cicd_metrics.py
```python
get_cicd_pass_rate          # Line 1158
get_deployment_metrics      # Line 1223
```

### tech_metrics.py
```python
get_file_category_breakdown # Line 1292
get_tech_breakdown          # Line 2507
get_monthly_tech_trend      # Line 2570
get_weekly_tech_trend       # Line 2638
```

### survey_metrics.py
```python
get_response_channel_distribution  # Line 1590
get_response_time_metrics   # Line 1765
```

### trend_metrics.py
```python
get_monthly_cycle_time_trend   # Line 1914
get_monthly_review_time_trend  # Line 1931
get_monthly_pr_count        # Line 1948
get_weekly_pr_count         # Line 1982
get_monthly_ai_adoption     # Line 2014
get_trend_comparison        # Line 2057
get_sparkline_data          # Line 2118
```

## Test File Mapping

| Test File | Service Module |
|-----------|----------------|
| `test_key_metrics.py` | `key_metrics.py` |
| `test_ai_metrics.py` | `ai_metrics.py` |
| `test_ai_detective_leaderboard.py` | `ai_metrics.py` |
| `test_ai_bot_reviews.py` | `ai_metrics.py` |
| `test_ai_impact.py` | `ai_metrics.py` |
| `test_team_breakdown.py` | `team_metrics.py` |
| `test_team_velocity.py` | `team_metrics.py` |
| `test_review_metrics.py` | `review_metrics.py` |
| `test_reviewer_correlations.py` | `review_metrics.py` |
| `test_bottleneck.py` | `review_metrics.py` |
| `test_pr_metrics.py` | `pr_metrics.py` |
| `test_cycle_time.py` | `pr_metrics.py` |
| `test_pr_type_breakdown.py` | `pr_metrics.py` |
| `test_needs_attention.py` | `pr_metrics.py` |
| `test_copilot_metrics.py` | `copilot_metrics.py` |
| `test_cicd_metrics.py` | `cicd_metrics.py` |
| `test_deployment_metrics.py` | `cicd_metrics.py` |
| `test_file_categories.py` | `tech_metrics.py` |
| `test_channel_metrics.py` | `survey_metrics.py` |
| `test_sparkline_data.py` | `trend_metrics.py` |
| `test_trend_comparison.py` | `trend_metrics.py` |
| `test_velocity_comparison.py` | `trend_metrics.py` |

## Key Decisions

1. **Use `dashboard/` directory** (not `_service_modules/`) since there's no package conflict
2. **Start with helpers** - they have no dependencies on other modules
3. **Group by test file** - existing test organization matches proposed module structure
4. **Re-export everything** - maintain backward compatibility with `from dashboard_service import X`

## Dependencies Between Modules

```
_helpers.py (no deps)
    ↓
key_metrics.py (uses _helpers)
    ↓
ai_metrics.py (uses _helpers)
team_metrics.py (uses _helpers)
review_metrics.py (uses _helpers)
pr_metrics.py (uses _helpers)
copilot_metrics.py (uses _helpers)
cicd_metrics.py (uses _helpers)
tech_metrics.py (uses _helpers)
survey_metrics.py (uses _helpers)
trend_metrics.py (uses _helpers, may use other modules)
```

## Import Patterns

After split, both patterns will work:
```python
# New pattern (preferred)
from apps.metrics.services.dashboard import get_key_metrics

# Legacy pattern (still works via re-export)
from apps.metrics.services.dashboard_service import get_key_metrics
```

## Constants

Already extracted to `apps/metrics/constants.py`:
- `PR_SIZE_XS_MAX`, `PR_SIZE_S_MAX`, `PR_SIZE_M_MAX`, `PR_SIZE_L_MAX`

Module-specific constants (keep in `dashboard_service.py` or move to modules):
- `DASHBOARD_CACHE_TTL = 300`
- `MIN_SPARKLINE_SAMPLE_SIZE = 3`
- `MAX_TREND_PERCENTAGE = 500`
