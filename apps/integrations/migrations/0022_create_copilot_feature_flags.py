"""Create Copilot feature flags.

This migration creates the Waffle flags needed for Copilot feature gating.
All flags are created but disabled by default for controlled rollout.
"""

from django.db import migrations


def create_copilot_flags(apps, schema_editor):
    """Create Copilot feature flags if they don't exist."""
    # Use custom Flag model from teams app (WAFFLE_FLAG_MODEL = "teams.Flag")
    Flag = apps.get_model("teams", "Flag")

    copilot_flags = [
        {
            "name": "copilot_enabled",
            "note": "Master switch for all Copilot features. Must be enabled for any sub-feature to work.",
            "everyone": False,
            "superusers": True,  # Enable for superusers by default for testing
        },
        {
            "name": "copilot_seat_utilization",
            "note": "Show Copilot seat utilization and ROI metrics on dashboard.",
            "everyone": False,
            "superusers": True,
        },
        {
            "name": "copilot_language_insights",
            "note": "Show Copilot language and editor breakdown charts.",
            "everyone": False,
            "superusers": True,
        },
        {
            "name": "copilot_delivery_impact",
            "note": "Show Copilot vs Non-Copilot PR comparison metrics.",
            "everyone": False,
            "superusers": True,
        },
        {
            "name": "copilot_llm_insights",
            "note": "Include Copilot metrics in LLM-generated insights.",
            "everyone": False,
            "superusers": True,
        },
    ]

    for flag_data in copilot_flags:
        Flag.objects.get_or_create(
            name=flag_data["name"],
            defaults={
                "note": flag_data["note"],
                "everyone": flag_data["everyone"],
                "superusers": flag_data["superusers"],
            },
        )


def remove_copilot_flags(apps, schema_editor):
    """Remove Copilot feature flags."""
    # Use custom Flag model from teams app (WAFFLE_FLAG_MODEL = "teams.Flag")
    Flag = apps.get_model("teams", "Flag")

    flag_names = [
        "copilot_enabled",
        "copilot_seat_utilization",
        "copilot_language_insights",
        "copilot_delivery_impact",
        "copilot_llm_insights",
    ]

    Flag.objects.filter(name__in=flag_names).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("integrations", "0021_make_tracked_repository_integration_nullable"),
        ("teams", "0001_initial"),  # teams.Flag model
    ]

    operations = [
        migrations.RunPython(create_copilot_flags, remove_copilot_flags),
    ]
