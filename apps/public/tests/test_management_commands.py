"""Tests for Unraid management commands (Task 8).

Covers: bootstrap_site_domain, init_public_repo_sync_state,
rebuild_public_catalog_snapshots.
"""

import logging
import os
import tempfile
from io import StringIO
from unittest.mock import patch

from django.contrib.sites.models import Site
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoProfile,
    PublicRepoStats,
    PublicRepoSyncState,
)
from apps.teams.models import Team

# CSV header for import_public_catalog tests (long by nature)
_CSV_HEADER = (
    "org_public_slug,org_display_name,org_industry,org_description,"
    "org_github_org_url,org_logo_url,team_slug,team_name,org_is_public,"
    "repo_github_repo,repo_slug,repo_display_name,repo_description,"
    "repo_github_url,is_flagship,repo_is_public,sync_enabled,"
    "insights_enabled,initial_backfill_days,display_order"
)

_ACME_CORE_ROW = (
    "acme,Acme,analytics,Acme analytics org,https://github.com/acme,,"
    "acme-demo,Acme Public,false,acme/core,core,Core Repo,Core repo,"
    "https://github.com/acme/core,true,true,true,false,180,0"
)

_ACME_SDK_ROW = (
    "acme,Acme,analytics,Acme analytics org,https://github.com/acme,,"
    "acme-demo,Acme Public,false,acme/sdk,sdk,SDK Repo,SDK repo,"
    "https://github.com/acme/sdk,false,true,true,false,180,1"
)

_ACME_CORE_UPDATED_ROW = (
    "acme,Acme New,analytics,Acme analytics org,https://github.com/acme,,"
    "acme-demo,Acme Public,true,acme/core,core,Core Repo,Core repo,"
    "https://github.com/acme/core,true,true,true,true,365,2"
)


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

    @patch("apps.public.repo_snapshot_service.build_repo_snapshot")
    def test_command_generates_org_and_repo_og_images(self, mock_snapshot):
        PublicRepoStats.objects.create(
            repo_profile=self.repo,
            total_prs=125,
            ai_assisted_pct=22.0,
            median_cycle_time_hours=3.4,
            median_review_time_hours=1.2,
        )

        with tempfile.TemporaryDirectory() as tmp, override_settings(MEDIA_ROOT=tmp):
            call_command("rebuild_public_catalog_snapshots", verbosity=0)

            assert os.path.exists(os.path.join(tmp, "public_og", "rebuild-org.png"))
            assert os.path.exists(os.path.join(tmp, "public_og", "rebuild-org_rebuild-repo.png"))


class ImportPublicCatalogTests(TestCase):
    """CSV import for DB-driven public catalog."""

    def _write_csv(self, content: str) -> str:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as tmp:
            self.addCleanup(lambda: os.path.exists(tmp.name) and os.unlink(tmp.name))
            tmp.write(content)
            tmp.flush()
            return tmp.name

    def test_dry_run_does_not_create_rows(self):
        path = self._write_csv(f"{_CSV_HEADER}\n{_ACME_CORE_ROW}\n")

        call_command("import_public_catalog", path, "--dry-run", verbosity=0)

        assert PublicOrgProfile.objects.count() == 0
        assert PublicRepoProfile.objects.count() == 0
        assert Team.objects.count() == 0

    def test_import_creates_team_org_repo_and_sync_state(self):
        path = self._write_csv(f"{_CSV_HEADER}\n{_ACME_CORE_ROW}\n{_ACME_SDK_ROW}\n")

        call_command("import_public_catalog", path, verbosity=0)

        team = Team.objects.get(slug="acme-demo")
        org = PublicOrgProfile.objects.get(public_slug="acme")
        repo = PublicRepoProfile.objects.get(org_profile=org, repo_slug="core")
        repo2 = PublicRepoProfile.objects.get(org_profile=org, repo_slug="sdk")

        assert org.team == team
        assert org.is_public is False
        assert repo.is_flagship is True
        assert repo.sync_enabled is True
        assert repo.insights_enabled is False
        assert repo.sync_state.status == "pending_backfill"
        assert repo2.display_order == 1

    def test_import_is_idempotent_and_updates_existing_rows(self):
        team = Team.objects.create(name="Old Team", slug="acme-demo")
        org = PublicOrgProfile.objects.create(
            team=team,
            public_slug="acme",
            industry="analytics",
            display_name="Old Acme",
            is_public=False,
        )
        PublicRepoProfile.objects.create(
            org_profile=org,
            github_repo="acme/core",
            repo_slug="core",
            display_name="Old Repo",
            sync_enabled=False,
            insights_enabled=False,
            is_public=True,
        )

        path = self._write_csv(f"{_CSV_HEADER}\n{_ACME_CORE_UPDATED_ROW}\n")

        call_command("import_public_catalog", path, verbosity=0)

        org.refresh_from_db()
        repo = PublicRepoProfile.objects.get(org_profile=org, repo_slug="core")
        team.refresh_from_db()

        assert Team.objects.filter(slug="acme-demo").count() == 1
        assert PublicOrgProfile.objects.filter(public_slug="acme").count() == 1
        assert PublicRepoProfile.objects.filter(org_profile=org, repo_slug="core").count() == 1
        assert team.name == "Acme Public"
        assert org.display_name == "Acme New"
        assert org.is_public is True
        assert repo.display_name == "Core Repo"
        assert repo.sync_enabled is True
        assert repo.insights_enabled is True
        assert repo.initial_backfill_days == 365
        assert repo.display_order == 2

    def test_import_rejects_unknown_industry(self):
        path = self._write_csv(
            """org_public_slug,org_display_name,org_industry,org_description,org_github_org_url,org_logo_url,team_slug,team_name,org_is_public,repo_github_repo,repo_slug,repo_display_name,repo_description,repo_github_url,is_flagship,repo_is_public,sync_enabled,insights_enabled,initial_backfill_days,display_order
acme,Acme,unknown,Acme analytics org,https://github.com/acme,,acme-demo,Acme Public,false,acme/core,core,Core Repo,Core repo,https://github.com/acme/core,true,true,true,false,180,0
"""
        )

        with self.assertRaises(CommandError):
            call_command("import_public_catalog", path, verbosity=0)


class RunPublicSyncTests(TestCase):
    """Tests for the run_public_sync management command."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Sync Team", slug="sync-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="sync-org",
            industry="analytics",
            display_name="Sync Org",
            is_public=True,
        )
        cls.repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="sync-org/repo-a",
            repo_slug="repo-a",
            display_name="Repo A",
            is_public=True,
            sync_enabled=True,
        )
        # Not eligible (sync_enabled=False)
        cls.disabled_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="sync-org/repo-b",
            repo_slug="repo-b",
            display_name="Repo B",
            is_public=True,
            sync_enabled=False,
        )

    @patch("apps.public.management.commands.run_public_sync.GitHubTokenPool")
    @patch("apps.public.management.commands.run_public_sync.SyncOrchestrator")
    def test_syncs_eligible_repos(self, mock_orch_cls, mock_pool_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.sync_repo.return_value = {"fetched": 10, "created": 5, "updated": 3, "skipped": 2, "errors": 0}

        call_command("run_public_sync", verbosity=0)

        synced_repos = [call.args[0] for call in mock_orch.sync_repo.call_args_list]
        synced_pks = {r.pk for r in synced_repos}
        assert self.repo.pk in synced_pks
        assert self.disabled_repo.pk not in synced_pks

    @patch("apps.public.management.commands.run_public_sync.GitHubTokenPool")
    @patch("apps.public.management.commands.run_public_sync.SyncOrchestrator")
    def test_project_filter_limits_repos(self, mock_orch_cls, mock_pool_cls):
        other_team = Team.objects.create(name="Other", slug="other-team")
        other_org = PublicOrgProfile.objects.create(
            team=other_team,
            public_slug="other-org",
            industry="analytics",
            display_name="Other Org",
            is_public=True,
        )
        other_repo = PublicRepoProfile.objects.create(
            org_profile=other_org,
            github_repo="other-org/repo-c",
            repo_slug="repo-c",
            display_name="Repo C",
            is_public=True,
            sync_enabled=True,
        )

        mock_orch = mock_orch_cls.return_value
        mock_orch.sync_repo.return_value = {"fetched": 1, "created": 1, "updated": 0, "skipped": 0, "errors": 0}

        call_command("run_public_sync", "--project", "sync-team", verbosity=0)

        synced_pks = {call.args[0].pk for call in mock_orch.sync_repo.call_args_list}
        assert self.repo.pk in synced_pks
        assert other_repo.pk not in synced_pks

    @patch("apps.public.management.commands.run_public_sync.GitHubTokenPool")
    @patch("apps.public.management.commands.run_public_sync.SyncOrchestrator")
    def test_rebuild_flag_calls_rebuild_command(self, mock_orch_cls, mock_pool_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.sync_repo.return_value = {"fetched": 0, "created": 0, "updated": 0, "skipped": 0, "errors": 0}

        with patch("apps.public.management.commands.run_public_sync.call_command") as mock_call:
            call_command("run_public_sync", "--rebuild", verbosity=0)
            mock_call.assert_called_once_with("rebuild_public_catalog_snapshots", verbosity=0)

    @patch("apps.public.management.commands.run_public_sync.GitHubTokenPool")
    @patch("apps.public.management.commands.run_public_sync.SyncOrchestrator")
    def test_continues_on_single_repo_failure(self, mock_orch_cls, mock_pool_cls):
        mock_orch = mock_orch_cls.return_value
        mock_orch.sync_repo.side_effect = [
            Exception("API error"),
            {"fetched": 5, "created": 3, "updated": 2, "skipped": 0, "errors": 0},
        ]

        # Create a second eligible repo so we have 2 to iterate
        PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="sync-org/repo-extra",
            repo_slug="repo-extra",
            display_name="Repo Extra",
            is_public=True,
            sync_enabled=True,
        )

        # Should not raise — continues past the failure
        call_command("run_public_sync", verbosity=0)

    @patch("apps.public.management.commands.run_public_sync.GitHubTokenPool")
    @patch("apps.public.management.commands.run_public_sync.SyncOrchestrator")
    def test_errors_visible_in_quiet_mode(self, mock_orch_cls, mock_pool_cls):
        """FAILED must appear in stderr even without --verbose."""
        mock_orch = mock_orch_cls.return_value
        mock_orch.sync_repo.side_effect = Exception("API error")

        stderr = StringIO()
        call_command("run_public_sync", stderr=stderr, verbosity=0)

        assert "FAILED" in stderr.getvalue()

    @patch("apps.public.management.commands.run_public_sync.GitHubTokenPool")
    @patch("apps.public.management.commands.run_public_sync.SyncOrchestrator")
    def test_verbose_flag_does_not_suppress_logging(self, mock_orch_cls, mock_pool_cls):
        """--verbose should leave the 'apps' logger level unchanged."""
        mock_orch = mock_orch_cls.return_value
        mock_orch.sync_repo.return_value = {"fetched": 1, "created": 1, "updated": 0}

        apps_logger = logging.getLogger("apps")
        level_before = apps_logger.level

        call_command("run_public_sync", "--verbose", verbosity=0)

        assert apps_logger.level == level_before
