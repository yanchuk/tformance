"""Add AI confidence score and signal breakdown fields.

Phase 5 of Enhanced AI Detection - composite scoring for multi-signal detection.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add ai_confidence_score and ai_signals fields to PullRequest."""

    dependencies = [
        ("metrics", "0024_add_ai_signal_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="pullrequest",
            name="ai_confidence_score",
            field=models.DecimalField(
                max_digits=4,
                decimal_places=3,
                null=True,
                blank=True,
                verbose_name="AI confidence score",
                help_text="Weighted score (0.000-1.000) combining all AI detection signals",
            ),
        ),
        migrations.AddField(
            model_name="pullrequest",
            name="ai_signals",
            field=models.JSONField(
                default=dict,
                blank=True,
                verbose_name="AI signal breakdown",
                help_text="Detailed breakdown of each detection signal source",
            ),
        ),
        # Add index for filtering by confidence score
        migrations.AddIndex(
            model_name="pullrequest",
            index=models.Index(
                fields=["team", "ai_confidence_score"],
                name="metrics_pr_team_ai_conf_idx",
            ),
        ),
    ]
