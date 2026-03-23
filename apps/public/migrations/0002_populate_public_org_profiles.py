"""Populate PublicOrgProfile from REAL_PROJECTS seeding config.

Creates a PublicOrgProfile for each team that matches a demo project,
linking it to the corresponding Team with clean slug, industry, and description.
"""

from django.db import migrations


# Inline the data to avoid import dependency on seeding module
# This ensures the migration works even if the seeding config changes
def _get_project_data():
    """Return project mapping: team_slug -> (public_slug, industry, description, display_name, github_org_url)."""
    from apps.metrics.seeding.real_projects import REAL_PROJECTS

    data = {}
    for config in REAL_PROJECTS.values():
        public_slug = config.team_slug.removesuffix("-demo")
        # Derive GitHub org URL from the first repo
        github_org = ""
        if config.repos:
            owner = config.repos[0].split("/")[0]
            github_org = f"https://github.com/{owner}"
        data[config.team_slug] = (
            public_slug,
            config.industry,
            config.description,
            config.team_name,
            github_org,
        )
    return data


def populate_profiles(apps, schema_editor):
    Team = apps.get_model("teams", "Team")
    PublicOrgProfile = apps.get_model("public", "PublicOrgProfile")

    project_data = _get_project_data()
    profiles_to_create = []

    for team in Team.objects.filter(slug__in=project_data.keys()):
        public_slug, industry, description, display_name, github_org_url = project_data[team.slug]
        profiles_to_create.append(
            PublicOrgProfile(
                team=team,
                public_slug=public_slug,
                industry=industry,
                description=description,
                display_name=display_name,
                github_org_url=github_org_url,
                is_public=True,
            )
        )

    PublicOrgProfile.objects.bulk_create(profiles_to_create, ignore_conflicts=True)


def reverse_populate(apps, schema_editor):
    PublicOrgProfile = apps.get_model("public", "PublicOrgProfile")
    PublicOrgProfile.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("public", "0001_initial"),
        ("teams", "0012_add_copilot_price_tier"),
    ]

    operations = [
        migrations.RunPython(populate_profiles, reverse_populate),
    ]
