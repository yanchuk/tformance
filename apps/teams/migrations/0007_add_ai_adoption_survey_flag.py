"""Add AI adoption survey feature flag.

When this flag is active, AI adoption metrics use survey data (PRSurvey.author_ai_assisted)
as the primary source. When inactive (default), only LLM and pattern detection are used.
"""

from django.db import migrations


def create_flag(apps, schema_editor):
    """Create the AI adoption survey feature flag."""
    Flag = apps.get_model("teams", "Flag")
    Flag.objects.get_or_create(
        name="rely_on_surveys_for_ai_adoption",
        defaults={
            "everyone": None,  # Not active for everyone by default
            "superusers": False,
            "staff": False,
            "authenticated": False,
            "note": (
                "When active for a team, AI adoption metrics prioritize survey responses "
                "(PRSurvey.author_ai_assisted). When inactive (default), only LLM and pattern "
                "detection (effective_is_ai_assisted) are used."
            ),
        },
    )


def delete_flag(apps, schema_editor):
    """Remove the AI adoption survey feature flag."""
    Flag = apps.get_model("teams", "Flag")
    Flag.objects.filter(name="rely_on_surveys_for_ai_adoption").delete()


class Migration(migrations.Migration):
    """Create the AI adoption survey feature flag."""

    dependencies = [
        ("teams", "0006_add_two_phase_onboarding_fields"),
    ]

    operations = [
        migrations.RunPython(create_flag, delete_flag),
    ]
