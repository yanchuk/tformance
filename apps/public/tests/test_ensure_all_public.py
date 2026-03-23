"""Tests for ensure_all_public management command."""

from django.core.management import call_command
from django.test import TestCase

from apps.public.models import PublicOrgProfile
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
