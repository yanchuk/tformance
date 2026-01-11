"""Configure autovacuum settings for high-churn tables.

This migration sets more aggressive autovacuum thresholds for tables that experience
frequent UPDATE/DELETE operations during sync processes.

Default PostgreSQL settings:
- autovacuum_vacuum_scale_factor = 0.2 (20% of table must change to trigger vacuum)
- autovacuum_analyze_scale_factor = 0.1 (10% of table must change to trigger analyze)

For high-churn tables, we use more aggressive thresholds:
- Most tables: 0.05 (5%) vacuum, 0.02 (2%) analyze
- aiusagedaily (3M+ rows): 0.01 (1%) vacuum, 0.005 (0.5%) analyze

This prevents bloat accumulation between manual maintenance runs.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("metrics", "0040_add_copilot_fields_to_team_member"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
            -- High-churn PR-related tables (5% threshold)
            ALTER TABLE metrics_pullrequest SET (
                autovacuum_vacuum_scale_factor = 0.05,
                autovacuum_analyze_scale_factor = 0.02
            );
            ALTER TABLE metrics_prfile SET (
                autovacuum_vacuum_scale_factor = 0.05,
                autovacuum_analyze_scale_factor = 0.02
            );
            ALTER TABLE metrics_commit SET (
                autovacuum_vacuum_scale_factor = 0.05,
                autovacuum_analyze_scale_factor = 0.02
            );
            ALTER TABLE metrics_prreview SET (
                autovacuum_vacuum_scale_factor = 0.05,
                autovacuum_analyze_scale_factor = 0.02
            );
            ALTER TABLE metrics_weeklymetrics SET (
                autovacuum_vacuum_scale_factor = 0.05,
                autovacuum_analyze_scale_factor = 0.02
            );

            -- Very large table with frequent updates (1% threshold)
            ALTER TABLE metrics_aiusagedaily SET (
                autovacuum_vacuum_scale_factor = 0.01,
                autovacuum_analyze_scale_factor = 0.005
            );

            -- Team members synced frequently
            ALTER TABLE metrics_teammember SET (
                autovacuum_vacuum_scale_factor = 0.05,
                autovacuum_analyze_scale_factor = 0.02
            );
            """,
            reverse_sql="""
            -- Reset to PostgreSQL defaults
            ALTER TABLE metrics_pullrequest RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            ALTER TABLE metrics_prfile RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            ALTER TABLE metrics_commit RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            ALTER TABLE metrics_prreview RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            ALTER TABLE metrics_weeklymetrics RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            ALTER TABLE metrics_aiusagedaily RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            ALTER TABLE metrics_teammember RESET (
                autovacuum_vacuum_scale_factor,
                autovacuum_analyze_scale_factor
            );
            """,
        ),
    ]
