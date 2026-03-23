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

    def test_sanitizes_dotted_repo_slugs(self):
        """Repos with dots in their name get slugs with dashes instead."""
        # calcom has repo "calcom/cal.com" — the slug must be "cal-com" not "cal.com"
        team = Team.objects.create(name="Cal.com", slug="calcom-demo")
        org = PublicOrgProfile.objects.create(
            team=team,
            public_slug="calcom",
            display_name="Cal.com",
            is_public=True,
        )

        call_command("ensure_all_public", verbosity=0)

        repo = PublicRepoProfile.objects.get(org_profile=org)
        assert repo.repo_slug == "cal-com", f"Expected 'cal-com', got '{repo.repo_slug}'"
        assert repo.github_repo == "calcom/cal.com"

    def test_fixes_existing_dotted_slugs(self):
        """Pre-existing repo profiles with dots in slugs are cleaned up."""
        team = Team.objects.create(name="Cal.com", slug="calcom-demo")
        org = PublicOrgProfile.objects.create(
            team=team,
            public_slug="calcom",
            display_name="Cal.com",
            is_public=True,
        )
        # Simulate the old bad slug
        bad_repo = PublicRepoProfile.objects.create(
            org_profile=org,
            team=team,
            repo_slug="cal.com",
            github_repo="calcom/cal.com",
            display_name="Cal.com",
            github_url="https://github.com/calcom/cal.com",
            is_public=True,
            sync_enabled=True,
        )

        call_command("ensure_all_public", verbosity=0)

        bad_repo.refresh_from_db()
        assert bad_repo.repo_slug == "cal-com", f"Expected 'cal-com', got '{bad_repo.repo_slug}'"
