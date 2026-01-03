"""Add feature flags for integration availability.

Creates 4 flags to control which integrations are available:
- integration_jira_enabled: Control Jira integration availability
- integration_copilot_enabled: Control GitHub Copilot integration availability
- integration_slack_enabled: Control Slack integration availability
- integration_google_workspace_enabled: Control Google Workspace (future) availability

All flags default to disabled (everyone=None). Enable via Django admin.
"""

from django.db import migrations

# Flag definitions with metadata
FLAGS = [
    {
        "name": "integration_jira_enabled",
        "note": (
            "When active, users can connect Jira integration. "
            "When inactive, Jira shows as 'Coming Soon' on integrations page "
            "and is skipped in onboarding."
        ),
    },
    {
        "name": "integration_copilot_enabled",
        "note": (
            "When active, users can access GitHub Copilot metrics. "
            "When inactive, Copilot shows as 'Coming Soon' on integrations page."
        ),
    },
    {
        "name": "integration_slack_enabled",
        "note": (
            "When active, users can connect Slack integration. "
            "When inactive, Slack shows as 'Coming Soon' on integrations page "
            "and is skipped in onboarding."
        ),
    },
    {
        "name": "integration_google_workspace_enabled",
        "note": (
            "Future integration for Google Workspace calendar tracking. "
            "Always shows as 'Coming Soon' for now."
        ),
    },
]


def create_flags(apps, schema_editor):
    """Create the integration feature flags."""
    Flag = apps.get_model("teams", "Flag")
    for flag_data in FLAGS:
        Flag.objects.get_or_create(
            name=flag_data["name"],
            defaults={
                "everyone": None,  # Not active for everyone by default
                "superusers": False,
                "staff": False,
                "authenticated": False,
                "note": flag_data["note"],
            },
        )


def delete_flags(apps, schema_editor):
    """Remove the integration feature flags."""
    Flag = apps.get_model("teams", "Flag")
    Flag.objects.filter(name__in=[f["name"] for f in FLAGS]).delete()


class Migration(migrations.Migration):
    """Create integration availability feature flags."""

    dependencies = [
        ("teams", "0007_add_ai_adoption_survey_flag"),
    ]

    operations = [
        migrations.RunPython(create_flags, delete_flags),
    ]
