"""Cleanup unused indexes and add missing composite indexes.

Database audit findings:
- 13 indexes with 0 scans consuming ~10MB storage
- 2 missing composite indexes for dashboard date range queries

This migration:
1. Drops unused single-column indexes (covered by composites or never queried)
2. Drops Django auto-generated _like indexes (no LIKE queries in codebase)
3. Adds composite indexes for PRReview and PRSurveyReview date filtering
"""

from django.db import migrations


class Migration(migrations.Migration):
    atomic = False  # Required for CONCURRENTLY operations

    dependencies = [
        ("metrics", "0025_add_ai_confidence_score"),
    ]

    operations = [
        # =============================================================
        # DROP unused TeamMember indexes (saves ~5MB)
        # =============================================================

        # github_username: covered by member_team_gh_username_idx (team_id, github_username)
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_github_username_fbd68b66;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_github_username_fbd68b66 "
            "ON metrics_teammember (github_username);",
        ),
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_github_username_fbd68b66_like;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_github_username_fbd68b66_like "
            "ON metrics_teammember (github_username varchar_pattern_ops);",
        ),

        # github_id: covered by unique_team_github_id (team_id, github_id)
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_github_id_e1885e95;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_github_id_e1885e95 "
            "ON metrics_teammember (github_id);",
        ),
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_github_id_e1885e95_like;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_github_id_e1885e95_like "
            "ON metrics_teammember (github_id varchar_pattern_ops);",
        ),

        # jira_account_id: 0 scans - not queried
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_jira_account_id_d5a53f1c;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_jira_account_id_d5a53f1c "
            "ON metrics_teammember (jira_account_id);",
        ),
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_jira_account_id_d5a53f1c_like;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_jira_account_id_d5a53f1c_like "
            "ON metrics_teammember (jira_account_id varchar_pattern_ops);",
        ),

        # slack_user_id: 0 scans - not queried
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_slack_user_id_8714cc99;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_slack_user_id_8714cc99 "
            "ON metrics_teammember (slack_user_id);",
        ),
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS metrics_teammember_slack_user_id_8714cc99_like;",
            "CREATE INDEX CONCURRENTLY metrics_teammember_slack_user_id_8714cc99_like "
            "ON metrics_teammember (slack_user_id varchar_pattern_ops);",
        ),

        # =============================================================
        # DROP unused JiraIssue indexes (saves ~1.8MB)
        # =============================================================

        # resolved_at: 0 scans - not queried
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS jira_resolved_at_idx;",
            "CREATE INDEX CONCURRENTLY jira_resolved_at_idx ON metrics_jiraissue (resolved_at);",
        ),

        # sprint_id: 0 scans - not queried
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS jira_sprint_idx;",
            "CREATE INDEX CONCURRENTLY jira_sprint_idx ON metrics_jiraissue (sprint_id);",
        ),

        # assignee + status composite: 0 scans - not queried
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS jira_assignee_status_idx;",
            "CREATE INDEX CONCURRENTLY jira_assignee_status_idx "
            "ON metrics_jiraissue (assignee_id, status);",
        ),

        # =============================================================
        # DROP unused PullRequest GIN indexes (saves ~900KB)
        # =============================================================

        # labels GIN: 0 scans - label filtering not implemented
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS pr_labels_gin_idx;",
            "CREATE INDEX CONCURRENTLY pr_labels_gin_idx "
            "ON metrics_pullrequest USING gin (labels);",
        ),

        # ai_tools_detected GIN: 0 scans - queries use llm_summary instead
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS pr_ai_tools_gin_idx;",
            "CREATE INDEX CONCURRENTLY pr_ai_tools_gin_idx "
            "ON metrics_pullrequest USING gin (ai_tools_detected);",
        ),

        # =============================================================
        # DROP unused PRCheckRun index (saves ~700KB)
        # =============================================================

        # started_at: 0 scans - not queried
        migrations.RunSQL(
            "DROP INDEX CONCURRENTLY IF EXISTS check_run_started_at_idx;",
            "CREATE INDEX CONCURRENTLY check_run_started_at_idx "
            "ON metrics_prcheckrun (started_at);",
        ),

        # =============================================================
        # ADD missing composite indexes for dashboard queries
        # =============================================================

        # PRReview: team + submitted_at for get_reviewer_workload()
        # Query: PRReview.objects.filter(team=team, submitted_at__gte=start, submitted_at__lte=end)
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "review_team_submitted_idx" '
            'ON "metrics_prreview" (team_id, submitted_at);',
            'DROP INDEX CONCURRENTLY IF EXISTS "review_team_submitted_idx";',
        ),

        # PRSurveyReview: team + responded_at for get_ai_detective_leaderboard()
        # Query: PRSurveyReview.objects.filter(team=team, responded_at__gte=start, responded_at__lte=end)
        migrations.RunSQL(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS "survey_review_team_responded_idx" '
            'ON "metrics_prsurveyreview" (team_id, responded_at);',
            'DROP INDEX CONCURRENTLY IF EXISTS "survey_review_team_responded_idx";',
        ),
    ]
