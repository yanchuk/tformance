"""Integration tests for the full reconciliation pipeline.

Uses a minimal fixture set (1 org, 1 repo, 5 PRs with children)
to verify the end-to-end flow.
"""

from datetime import UTC, datetime, timedelta
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import Commit, PRCheckRun, PRFile, PRReview, PullRequest
from apps.metrics.seeding.github_authenticated_fetcher import (
    FetchedCheckRun,
    FetchedCommit,
    FetchedFile,
    FetchedPRFull,
    FetchedReview,
)
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile


def _build_integration_cache_prs():
    """Build 5 realistic FetchedPRFull objects for integration tests."""
    now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    prs = []
    for i in range(5):
        pr = FetchedPRFull(
            github_pr_id=7000 + i,
            number=7000 + i,
            github_repo="integration-org/main-repo",
            title=f"Integration PR #{7000 + i}",
            body=f"Body for integration PR {i}",
            state="merged",
            is_merged=True,
            is_draft=False,
            created_at=now - timedelta(days=i + 2),
            updated_at=now - timedelta(days=i),
            merged_at=now - timedelta(days=i, hours=1),
            closed_at=now - timedelta(days=i, hours=1),
            additions=50 + i * 10,
            deletions=10 + i * 5,
            changed_files=3,
            commits_count=1,
            author_login="dev1",
            author_id=9001,
            author_name="Dev One",
            author_avatar_url=None,
            head_ref="feature",
            base_ref="main",
            labels=[],
            reviews=[
                FetchedReview(
                    github_review_id=8000 + i,
                    reviewer_login="reviewer1",
                    state="APPROVED",
                    submitted_at=now - timedelta(days=i, hours=12),
                    body="LGTM",
                ),
            ],
            commits=[
                FetchedCommit(
                    sha=f"intsha_{i:04d}",
                    message=f"feat: integration commit {i}",
                    author_login="dev1",
                    author_name="Dev One",
                    committed_at=now - timedelta(days=i, hours=6),
                    additions=50 + i * 10,
                    deletions=10 + i * 5,
                ),
            ],
            files=[
                FetchedFile(
                    filename=f"src/feature_{i}.py",
                    status="modified",
                    additions=50 + i * 10,
                    deletions=10 + i * 5,
                ),
            ],
            check_runs=[
                FetchedCheckRun(
                    github_id=9000 + i,
                    name="ci",
                    status="completed",
                    conclusion="success",
                    started_at=now - timedelta(days=i, hours=2),
                    completed_at=now - timedelta(days=i, hours=1, minutes=55),
                ),
            ],
        )
        prs.append(pr)
    return prs


class IntegrationDryRunTests(TestCase):
    """Full dry-run pipeline: exit 0, print summary, no DB writes."""

    @classmethod
    def setUpTestData(cls):
        from apps.public.models import PublicRepoProfile

        cls.team = TeamFactory(slug="int-demo")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="integration",
            industry="analytics",
            display_name="Integration Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        # Reconciliation now resolves repos from DB, not manifest
        PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="integration-org/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )

    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_prerequisites")
    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_cache_files")
    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    @patch(
        "apps.public.services.local_fixture_manifest.FIXTURE_MANIFEST",
        {
            "integration": {
                "repos": [
                    {"github_repo": "integration-org/main-repo", "repo_slug": "main-repo", "is_flagship": True},
                ],
            },
        },
    )
    def test_dry_run_no_writes_with_summary(self, mock_deserialize, mock_cache_cls, mock_validate_cache, mock_prereqs):
        """Full dry-run: prints summary counts and writes nothing."""
        cache_prs = _build_integration_cache_prs()
        mock_cache = MagicMock()
        mock_cache.prs = [{}] * 5
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = (cache_prs, 0)

        pr_count_before = PullRequest.objects.count()
        review_count_before = PRReview.objects.count()

        stdout = StringIO()
        call_command(
            "reconcile_public_repo_local_data",
            "--org",
            "integration",
            "--dry-run",
            stdout=stdout,
        )

        output = stdout.getvalue()
        # Should contain DRY RUN and summary counts
        assert "DRY RUN" in output
        assert "Missing" in output or "missing" in output.lower()

        # No writes
        assert PullRequest.objects.count() == pr_count_before
        assert PRReview.objects.count() == review_count_before


class IntegrationApplyTests(TestCase):
    """Full apply pipeline: creates/repairs PRs, bootstraps entities."""

    @classmethod
    def setUpTestData(cls):
        from apps.public.models import PublicRepoProfile

        cls.team = TeamFactory(slug="int-apply-demo")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="integration-apply",
            industry="analytics",
            display_name="Integration Apply Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        # Reconciliation now resolves repos from DB, not manifest
        PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="integration-org/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )

    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_prerequisites")
    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_cache_files")
    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    @patch(
        "apps.public.services.local_fixture_manifest.FIXTURE_MANIFEST",
        {
            "integration-apply": {
                "repos": [
                    {"github_repo": "integration-org/main-repo", "repo_slug": "main-repo", "is_flagship": True},
                ],
            },
        },
    )
    def test_apply_creates_prs_and_children(self, mock_deserialize, mock_cache_cls, mock_validate_cache, mock_prereqs):
        """Apply mode should create PRs with all children."""
        cache_prs = _build_integration_cache_prs()
        mock_cache = MagicMock()
        mock_cache.prs = [{}] * 5
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = (cache_prs, 0)

        stdout = StringIO()
        call_command(
            "reconcile_public_repo_local_data",
            "--org",
            "integration-apply",
            stdout=stdout,
        )

        # PRs created
        prs = PullRequest.objects.filter(team=self.team, github_repo="integration-org/main-repo")
        assert prs.count() == 5

        # Children created
        for pr in prs:
            assert PRReview.objects.filter(pull_request=pr).count() >= 1
            assert Commit.objects.filter(pull_request=pr).count() >= 1
            assert PRFile.objects.filter(pull_request=pr).count() >= 1
            assert PRCheckRun.objects.filter(pull_request=pr).count() >= 1

        # Repo profile bootstrapped
        assert PublicRepoProfile.objects.filter(org_profile=self.org_profile, repo_slug="main-repo").exists()


class IntegrationIdempotencyTests(TestCase):
    """Idempotent rerun: second apply writes zero changes."""

    @classmethod
    def setUpTestData(cls):
        from apps.public.models import PublicRepoProfile

        cls.team = TeamFactory(slug="int-idem-demo")
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="integration-idem",
            industry="analytics",
            display_name="Integration Idem Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        # Reconciliation now resolves repos from DB, not manifest
        PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="integration-org/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )

    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_prerequisites")
    @patch("apps.public.services.local_reconciliation.LocalReconciliationService.validate_cache_files")
    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    @patch(
        "apps.public.services.local_fixture_manifest.FIXTURE_MANIFEST",
        {
            "integration-idem": {
                "repos": [
                    {"github_repo": "integration-org/main-repo", "repo_slug": "main-repo", "is_flagship": True},
                ],
            },
        },
    )
    def test_second_run_zero_changes(self, mock_deserialize, mock_cache_cls, mock_validate_cache, mock_prereqs):
        """Running apply twice with same data should report zero changes on second run."""
        cache_prs = _build_integration_cache_prs()
        mock_cache = MagicMock()
        mock_cache.prs = [{}] * 5
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = (cache_prs, 0)

        # First run
        call_command(
            "reconcile_public_repo_local_data",
            "--org",
            "integration-idem",
            stdout=StringIO(),
        )
        pr_count_after_first = PullRequest.objects.filter(
            team=self.team, github_repo="integration-org/main-repo"
        ).count()
        review_count_after_first = PRReview.objects.filter(team=self.team).count()

        # Second run
        stdout2 = StringIO()
        call_command(
            "reconcile_public_repo_local_data",
            "--org",
            "integration-idem",
            stdout=stdout2,
        )

        # Counts unchanged
        assert (
            PullRequest.objects.filter(team=self.team, github_repo="integration-org/main-repo").count()
            == pr_count_after_first
        )
        assert PRReview.objects.filter(team=self.team).count() == review_count_after_first

        # Output should show zero missing/stale/partial on second run
        output = stdout2.getvalue()
        assert "Missing: 0" in output
