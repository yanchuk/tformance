"""Add optimized indexes for common query patterns.

Adds composite indexes for team-scoped queries and GIN indexes for JSONB fields.
"""

from django.contrib.postgres.operations import AddIndexConcurrently
from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False  # Required for concurrent index creation

    dependencies = [
        ("metrics", "0019_add_llm_summary"),
    ]

    operations = [
        # =============================================================
        # Composite indexes for common query patterns
        # =============================================================

        # Team + Repo: Used heavily in PR list filtering
        AddIndexConcurrently(
            model_name="pullrequest",
            index=models.Index(
                fields=["team", "github_repo"],
                name="pr_team_repo_idx",
            ),
        ),

        # Team + AI Assisted: For AI filtering in PR list and dashboards
        AddIndexConcurrently(
            model_name="pullrequest",
            index=models.Index(
                fields=["team", "is_ai_assisted"],
                name="pr_team_ai_assisted_idx",
            ),
        ),

        # Team + AI Assisted + Merged At: For AI metrics over time ranges
        AddIndexConcurrently(
            model_name="pullrequest",
            index=models.Index(
                fields=["team", "is_ai_assisted", "merged_at"],
                name="pr_team_ai_merged_idx",
            ),
        ),

        # =============================================================
        # GIN indexes for JSONB array fields (containment queries)
        # =============================================================

        # ai_tools_detected: For queries like ai_tools_detected__contains=['claude']
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "pr_ai_tools_gin_idx" '
                'ON "metrics_pullrequest" USING gin ("ai_tools_detected");',
            reverse_sql='DROP INDEX IF EXISTS "pr_ai_tools_gin_idx";',
        ),

        # labels: For filtering PRs by label
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "pr_labels_gin_idx" '
                'ON "metrics_pullrequest" USING gin ("labels");',
            reverse_sql='DROP INDEX IF EXISTS "pr_labels_gin_idx";',
        ),

        # =============================================================
        # GIN indexes for JSONB nested object queries (llm_summary)
        # Supports queries like:
        #   llm_summary @> '{"ai": {"is_assisted": true}}'
        #   llm_summary @> '{"tech": {"categories": ["backend"]}}'
        #   llm_summary->'ai'->'tools' ? 'claude'
        # =============================================================

        # Full llm_summary GIN index for containment (@>) and existence (?) queries
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "pr_llm_summary_gin_idx" '
                'ON "metrics_pullrequest" USING gin ("llm_summary" jsonb_path_ops);',
            reverse_sql='DROP INDEX IF EXISTS "pr_llm_summary_gin_idx";',
        ),

        # Partial index for LLM-detected AI-assisted PRs (fast lookup)
        migrations.RunSQL(
            sql="CREATE INDEX CONCURRENTLY IF NOT EXISTS \"pr_llm_ai_assisted_idx\" "
                "ON \"metrics_pullrequest\" (team_id, merged_at) "
                "WHERE (llm_summary->'ai'->>'is_assisted')::boolean = true;",
            reverse_sql='DROP INDEX IF EXISTS "pr_llm_ai_assisted_idx";',
        ),

        # =============================================================
        # Expression indexes for common JSONB extractions
        # =============================================================

        # Index on LLM-detected AI tools array for tool-specific queries
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "pr_llm_ai_tools_gin_idx" '
                "ON \"metrics_pullrequest\" USING gin ((llm_summary->'ai'->'tools'));",
            reverse_sql='DROP INDEX IF EXISTS "pr_llm_ai_tools_gin_idx";',
        ),

        # Index on tech categories for technology filtering
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "pr_llm_tech_categories_gin_idx" '
                "ON \"metrics_pullrequest\" USING gin ((llm_summary->'tech'->'categories'));",
            reverse_sql='DROP INDEX IF EXISTS "pr_llm_tech_categories_gin_idx";',
        ),

        # Index on tech languages for language filtering
        migrations.RunSQL(
            sql='CREATE INDEX CONCURRENTLY IF NOT EXISTS "pr_llm_tech_languages_gin_idx" '
                "ON \"metrics_pullrequest\" USING gin ((llm_summary->'tech'->'languages'));",
            reverse_sql='DROP INDEX IF EXISTS "pr_llm_tech_languages_gin_idx";',
        ),
    ]
