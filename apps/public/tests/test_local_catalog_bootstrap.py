"""Tests for catalog drift removal (Task 3).

Covers: DB-driven reconciliation, curated field preservation,
bootstrap_public_repo_fixtures command.
"""

from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.public.models import PublicOrgProfile, PublicRepoProfile, PublicRepoSyncState
from apps.teams.models import Team


class DBDrivenReconciliationTests(TestCase):
    """Step 3.1: Reconciliation resolves repos from DB, not manifest."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Recon Team", slug="recon-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="recon-org",
            industry="analytics",
            display_name="Recon Org",
            is_public=True,
        )
        # Create a repo in DB that is NOT in the fixture manifest
        cls.db_only_repo = PublicRepoProfile.objects.create(
            org_profile=cls.org,
            github_repo="recon-org/db-only-repo",
            repo_slug="db-only-repo",
            display_name="DB Only Repo",
            is_public=True,
        )

    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.analyze_repo")
    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_prerequisites")
    def test_reconcile_resolves_repos_from_db(self, mock_prereq, mock_analyze):
        """Reconciliation should process DB repos, not manifest repos."""
        from unittest.mock import MagicMock

        mock_analyze.return_value = MagicMock(
            db_pr_count=10,
            cache_pr_count=0,
            missing_pr_count=0,
            stale_pr_count=0,
            partial_pr_count=0,
            llm_candidate_count=0,
        )

        call_command(
            "reconcile_public_repo_local_data",
            "--org",
            "recon-org",
            "--dry-run",
            "--allow-backup-fallback",
            verbosity=0,
        )

        # Should have been called with our DB-only repo's team and github_repo
        analyzed_repos = [call.args[1] for call in mock_analyze.call_args_list]
        assert "recon-org/db-only-repo" in analyzed_repos


class CuratedFieldPreservationTests(TestCase):
    """Step 3.2: Reconciliation preserves curated fields."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Curate Team", slug="curate-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="polar",
            industry="billing",
            display_name="Polar",
            is_public=True,
        )

    def test_reconciliation_preserves_display_name(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="polarsource/polar",
            repo_slug="polar",
            display_name="My Custom Name",
            is_public=True,
        )

        from apps.public.services.local_reconciliation import LocalReconciliationService

        service = LocalReconciliationService(dry_run=False)
        service.bootstrap_repo_profiles(
            [{"org_slug": "polar", "github_repo": "polarsource/polar", "repo_slug": "polar", "is_flagship": True}],
            {"polar": self.org},
        )

        repo.refresh_from_db()
        assert repo.display_name == "My Custom Name"

    def test_reconciliation_preserves_is_flagship(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="polarsource/polar-2",
            repo_slug="polar-2",
            display_name="Polar 2",
            is_flagship=False,
            is_public=True,
        )

        from apps.public.services.local_reconciliation import LocalReconciliationService

        service = LocalReconciliationService(dry_run=False)
        service.bootstrap_repo_profiles(
            [{"org_slug": "polar", "github_repo": "polarsource/polar-2", "repo_slug": "polar-2", "is_flagship": True}],
            {"polar": self.org},
        )

        repo.refresh_from_db()
        assert repo.is_flagship is False  # should NOT be overwritten

    def test_reconciliation_preserves_sync_enabled(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="polarsource/polar-3",
            repo_slug="polar-3",
            display_name="Polar 3",
            is_public=True,
            sync_enabled=False,
        )

        from apps.public.services.local_reconciliation import LocalReconciliationService

        service = LocalReconciliationService(dry_run=False)
        service.bootstrap_repo_profiles(
            [{"org_slug": "polar", "github_repo": "polarsource/polar-3", "repo_slug": "polar-3", "is_flagship": False}],
            {"polar": self.org},
        )

        repo.refresh_from_db()
        assert repo.sync_enabled is False  # should NOT be overwritten


class BootstrapFixturesCommandTests(TestCase):
    """Step 3.3: bootstrap_public_repo_fixtures command."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Boot Team", slug="boot-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="polar",
            industry="billing",
            display_name="Polar",
            is_public=True,
        )

    def test_bootstrap_creates_missing_repo_profiles(self):
        call_command("bootstrap_public_repo_fixtures", "--org", "polar", verbosity=0)

        repos = PublicRepoProfile.objects.filter(org_profile=self.org)
        assert repos.count() >= 1
        assert repos.filter(repo_slug="polar").exists()

    def test_bootstrap_does_not_overwrite_existing_curated_fields(self):
        PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="polarsource/polar",
            repo_slug="polar",
            display_name="Custom Name",
            is_public=True,
        )

        call_command("bootstrap_public_repo_fixtures", "--org", "polar", verbosity=0)

        repo = PublicRepoProfile.objects.get(org_profile=self.org, repo_slug="polar")
        assert repo.display_name == "Custom Name"

    def test_bootstrap_force_overwrite_resets_fields(self):
        PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="polarsource/polar",
            repo_slug="polar",
            display_name="Custom Name",
            is_public=True,
        )

        call_command("bootstrap_public_repo_fixtures", "--org", "polar", "--force-overwrite", verbosity=0)

        repo = PublicRepoProfile.objects.get(org_profile=self.org, repo_slug="polar")
        # Should be overwritten to the manifest-derived value
        assert repo.display_name != "Custom Name"

    def test_bootstrap_creates_sync_state_for_new_repos(self):
        call_command("bootstrap_public_repo_fixtures", "--org", "polar", verbosity=0)

        for repo in PublicRepoProfile.objects.filter(org_profile=self.org):
            assert PublicRepoSyncState.objects.filter(repo_profile=repo).exists()
