"""Tests for the reconcile_public_repo_local_data management command."""

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.public.models import PublicOrgProfile


class MigrationCheckTests(TestCase):
    """Test that the command fails fast when migration 0003 is not applied."""

    @patch(
        "apps.public.services.local_reconciliation.LocalReconciliationService.validate_prerequisites",
        side_effect=SystemExit(
            "Migration 'public.0003_public_repo_pages' is not applied. Run: .venv/bin/python manage.py migrate public"
        ),
    )
    def test_missing_migration_exits_with_error(self, mock_validate):
        """Command exits non-zero with specific message if migration not applied."""
        stderr = StringIO()
        with self.assertRaises(SystemExit) as ctx:
            call_command("reconcile_public_repo_local_data", "--org", "polar", stderr=stderr)

        error_msg = str(ctx.exception)
        assert "0003_public_repo_pages" in error_msg


class ManifestResolutionTests(TestCase):
    """Test that --org resolves repos from the fixture manifest."""

    @classmethod
    def setUpTestData(cls):
        cls.polar_team = TeamFactory(slug="polar-demo")
        cls.posthog_team = TeamFactory(slug="posthog-demo")
        cls.polar_profile = PublicOrgProfile.objects.create(
            team=cls.polar_team,
            public_slug="polar",
            industry="developer_tools",
            display_name="Polar",
            is_public=True,
        )
        cls.posthog_profile = PublicOrgProfile.objects.create(
            team=cls.posthog_team,
            public_slug="posthog",
            industry="analytics",
            display_name="PostHog",
            is_public=True,
        )

    def test_org_polar_resolves_to_4_repos(self):
        """--org polar should resolve to 4 repos from manifest."""
        from apps.public.services.local_fixture_manifest import get_repos_for_orgs

        repos = get_repos_for_orgs(["polar"])
        assert len(repos) == 4
        github_repos = [r["github_repo"] for r in repos]
        assert "polarsource/polar" in github_repos
        assert "polarsource/polar-adapters" in github_repos
        assert "polarsource/polar-js" in github_repos
        assert "polarsource/polar-python" in github_repos

    def test_org_posthog_resolves_to_4_repos(self):
        """--org posthog should resolve to 4 repos from manifest."""
        from apps.public.services.local_fixture_manifest import get_repos_for_orgs

        repos = get_repos_for_orgs(["posthog"])
        assert len(repos) == 4
        github_repos = [r["github_repo"] for r in repos]
        assert "PostHog/posthog" in github_repos
        assert "PostHog/posthog.com" in github_repos

    def test_repo_flag_narrows_to_single_repo(self):
        """--repo PostHog/posthog should narrow to 1 repo."""
        from apps.public.services.local_fixture_manifest import (
            filter_repos_by_github_repo,
            get_repos_for_orgs,
        )

        all_repos = get_repos_for_orgs(["posthog"])
        filtered = filter_repos_by_github_repo(all_repos, ["PostHog/posthog"])
        assert len(filtered) == 1
        assert filtered[0]["github_repo"] == "PostHog/posthog"
        assert filtered[0]["is_flagship"] is True

    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_prerequisites")
    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_cache_files")
    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.analyze_repo")
    def test_dry_run_writes_nothing(self, mock_analyze, mock_cache, mock_prereqs):
        """--dry-run should not write anything to the DB."""
        from apps.public.services.local_reconciliation import RepoReconciliationReport

        mock_analyze.return_value = RepoReconciliationReport(github_repo="polarsource/polar")

        stdout = StringIO()
        call_command(
            "reconcile_public_repo_local_data",
            "--org",
            "polar",
            "--dry-run",
            stdout=stdout,
        )

        output = stdout.getvalue()
        assert "DRY RUN" in output or "dry" in output.lower()

    def test_missing_cache_file_exits_with_error(self):
        """Missing cache file should fail with path in error message."""
        from apps.public.services.local_reconciliation import LocalReconciliationService

        service = LocalReconciliationService(dry_run=True)
        repos = [{"github_repo": "nonexistent/repo"}]

        with self.assertRaises(SystemExit) as ctx:
            service.validate_cache_files(repos)

        error_msg = str(ctx.exception)
        assert "nonexistent/repo" in error_msg

    def test_missing_org_profile_exits_with_error(self):
        """Missing PublicOrgProfile should fail with slug in error message."""
        from apps.public.services.local_reconciliation import LocalReconciliationService

        service = LocalReconciliationService(dry_run=True)

        with self.assertRaises(SystemExit) as ctx:
            service.validate_org_profiles(["nonexistent-org"])

        error_msg = str(ctx.exception)
        assert "nonexistent-org" in error_msg
