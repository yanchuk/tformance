"""Tests for ensure_all_public management command."""

from django.core.management import call_command
from django.test import TestCase

from apps.public.models import PublicOrgProfile, PublicRepoProfile
from apps.teams.models import Team


class EnsureAllPublicTests(TestCase):
    def test_flips_matching_orgs_only(self):
        # Matching demo slug (antiwork-demo is in REAL_PROJECTS)
        matching_team = Team.objects.create(name="Antiwork", slug="antiwork-demo")
        matching_org = PublicOrgProfile.objects.create(
            team=matching_team,
            public_slug="antiwork",
            display_name="Antiwork",
            is_public=False,
        )
        # Non-matching slug
        other_team = Team.objects.create(name="Other", slug="other-team")
        other_org = PublicOrgProfile.objects.create(
            team=other_team,
            public_slug="other",
            display_name="Other",
            is_public=False,
        )

        call_command("ensure_all_public", verbosity=0)

        matching_org.refresh_from_db()
        other_org.refresh_from_db()
        assert matching_org.is_public is True
        assert other_org.is_public is False

    def test_creates_missing_repo_profiles_from_real_projects(self):
        """Repos defined in REAL_PROJECTS are auto-created as PublicRepoProfile."""
        # antiwork has 3 repos: gumroad (flagship), flexile, helper
        team = Team.objects.create(name="Antiwork", slug="antiwork-demo")
        org = PublicOrgProfile.objects.create(
            team=team,
            public_slug="antiwork",
            display_name="Antiwork",
            is_public=True,
        )

        call_command("ensure_all_public", verbosity=0)

        repos = PublicRepoProfile.objects.filter(org_profile=org).order_by("repo_slug")
        assert repos.count() == 3

        # Check flagship assignment: first repo in tuple is flagship
        flagship = repos.get(repo_slug="gumroad")
        assert flagship.is_flagship is True
        assert flagship.github_repo == "antiwork/gumroad"
        assert flagship.github_url == "https://github.com/antiwork/gumroad"
        assert flagship.is_public is True
        assert flagship.sync_enabled is True

        # Non-flagship repos
        flexile = repos.get(repo_slug="flexile")
        assert flexile.is_flagship is False
        helper = repos.get(repo_slug="helper")
        assert helper.is_flagship is False
