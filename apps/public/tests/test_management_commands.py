"""Tests for Unraid management commands (Task 8).

Covers: bootstrap_site_domain, init_public_repo_sync_state,
rebuild_public_catalog_snapshots.
"""

from unittest.mock import patch

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.test import TestCase

from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoProfile,
    PublicRepoStats,
    PublicRepoSyncState,
)
from apps.teams.models import Team


class BootstrapSiteDomainTests(TestCase):
    """Step 8.1: bootstrap_site_domain command."""

    def test_command_creates_site_with_domain(self):
        call_command("bootstrap_site_domain", "--domain", "dev2.ianchuk.com", "--name", "Tformance", verbosity=0)
        site = Site.objects.get(pk=1)
        assert site.domain == "dev2.ianchuk.com"
        assert site.name == "Tformance"

    def test_command_is_idempotent(self):
        call_command("bootstrap_site_domain", "--domain", "first.com", "--name", "First", verbosity=0)
        call_command("bootstrap_site_domain", "--domain", "second.com", "--name", "Second", verbosity=0)
        site = Site.objects.get(pk=1)
        assert site.domain == "second.com"
        assert site.name == "Second"


class InitPublicRepoSyncStateTests(TestCase):
    """Step 8.2: init_public_repo_sync_state command."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Init Team", slug="init-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="init-org",
            industry="analytics",
            display_name="Init Org",
            is_public=True,
        )

    def test_command_creates_sync_state_for_repos_without_one(self):
        # Create repos (save() auto-creates sync state)
        repo_with_stats = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="init-org/with-stats",
            repo_slug="with-stats",
            display_name="With Stats",
        )
        repo_without_stats = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="init-org/without-stats",
            repo_slug="without-stats",
            display_name="Without Stats",
        )

        # Give one repo stats
        PublicRepoStats.objects.create(repo_profile=repo_with_stats, total_prs=100)

        # Delete auto-created sync states to simulate pre-migration data
        PublicRepoSyncState.objects.filter(repo_profile__in=[repo_with_stats, repo_without_stats]).delete()

        call_command("init_public_repo_sync_state", verbosity=0)

        # Both should now have sync states
        state_with = PublicRepoSyncState.objects.get(repo_profile=repo_with_stats)
        state_without = PublicRepoSyncState.objects.get(repo_profile=repo_without_stats)

        assert state_with.status == "ready"  # has stats
        assert state_without.status == "pending_backfill"  # no stats


class RebuildPublicCatalogSnapshotsTests(TestCase):
    """Step 8.3: rebuild_public_catalog_snapshots command."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Rebuild Team", slug="rebuild-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="rebuild-org",
            industry="analytics",
            display_name="Rebuild Org",
            is_public=True,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="rebuild-org/rebuild-repo",
            repo_slug="rebuild-repo",
            display_name="Rebuild Repo",
            is_public=True,
        )

    @patch("apps.public.repo_snapshot_service.build_repo_snapshot")
    def test_command_rebuilds_all_public_repo_snapshots(self, mock_snapshot):
        call_command("rebuild_public_catalog_snapshots", verbosity=0)

        # build_repo_snapshot should have been called for our repo
        called_profiles = [call.args[0] for call in mock_snapshot.call_args_list]
        assert any(p.pk == self.repo.pk for p in called_profiles)

    @patch("apps.public.repo_snapshot_service.build_repo_snapshot")
    def test_command_rebuilds_org_stats_after_repo_snapshots(self, mock_snapshot):
        call_command("rebuild_public_catalog_snapshots", verbosity=0)

        # Org stats should exist after rebuild
        assert PublicOrgStats.objects.filter(org_profile=self.org).exists()
