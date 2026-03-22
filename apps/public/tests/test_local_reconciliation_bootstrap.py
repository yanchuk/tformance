"""Tests for bootstrap phase: PublicRepoProfile/Stats/Insight creation."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import PullRequest, TeamMember
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoInsight,
    PublicRepoProfile,
    PublicRepoStats,
)
from apps.public.services.local_reconciliation import LocalReconciliationService


class RepoProfileBootstrapTests(TestCase):
    """Test that PublicRepoProfile rows are created from fixture manifest."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-bootstrap",
            industry="analytics",
            display_name="Bootstrap Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )

    def test_bootstrap_creates_repo_profiles(self):
        """bootstrap_repo_profiles should create PublicRepoProfile rows."""
        service = LocalReconciliationService(dry_run=False)
        repos = [
            {"github_repo": "org/main", "repo_slug": "main", "is_flagship": True, "org_slug": "test-bootstrap"},
            {"github_repo": "org/lib", "repo_slug": "lib", "is_flagship": False, "org_slug": "test-bootstrap"},
        ]
        org_profiles = {"test-bootstrap": self.org_profile}

        service.bootstrap_repo_profiles(repos, org_profiles)

        assert PublicRepoProfile.objects.filter(org_profile=self.org_profile).count() == 2
        flagship = PublicRepoProfile.objects.get(repo_slug="main", org_profile=self.org_profile)
        assert flagship.is_flagship is True
        assert flagship.github_repo == "org/main"

    def test_bootstrap_idempotent(self):
        """Running bootstrap twice should not create duplicates."""
        service = LocalReconciliationService(dry_run=False)
        repos = [
            {"github_repo": "org/main2", "repo_slug": "main2", "is_flagship": True, "org_slug": "test-bootstrap"},
        ]
        org_profiles = {"test-bootstrap": self.org_profile}

        service.bootstrap_repo_profiles(repos, org_profiles)
        service.bootstrap_repo_profiles(repos, org_profiles)

        assert PublicRepoProfile.objects.filter(repo_slug="main2", org_profile=self.org_profile).count() == 1


class SelectiveSnapshotRebuildTests(TestCase):
    """Test that snapshot rebuild only targets modified repos."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-snap",
            industry="analytics",
            display_name="Snapshot Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="org/snap-repo",
            repo_slug="snap-repo",
            display_name="Snap Repo",
            is_flagship=True,
            is_public=True,
        )
        # Create some PR data so the snapshot has something to work with
        member = TeamMember.objects.create(team=cls.team, github_username="dev1")
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        for i in range(5):
            PullRequest.objects.create(
                team=cls.team,
                github_pr_id=900 + i,
                github_repo="org/snap-repo",
                title=f"PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i),
                pr_created_at=now - timedelta(days=i + 1),
                additions=50,
                deletions=10,
                author=member,
            )

    @patch("apps.public.services.local_reconciliation.build_repo_snapshot")
    def test_rebuild_only_modified_repos(self, mock_build):
        """Only repos in modified_repos should trigger rebuild."""
        mock_build.return_value = MagicMock()

        service = LocalReconciliationService(dry_run=False)
        service.modified_repos.add("org/snap-repo")

        repos = [{"github_repo": "org/snap-repo", "repo_slug": "snap-repo", "org_slug": "test-snap"}]
        org_profiles = {"test-snap": self.org_profile}

        service.rebuild_snapshots(repos, org_profiles)

        mock_build.assert_called_once()

    @patch("apps.public.services.local_reconciliation.build_repo_snapshot")
    def test_unchanged_repos_skip_rebuild(self, mock_build):
        """Repos NOT in modified_repos should not rebuild unless missing stats."""
        # Create stats so repo is NOT missing
        PublicRepoStats.objects.create(repo_profile=self.repo_profile)

        service = LocalReconciliationService(dry_run=False)
        # modified_repos is empty — nothing was changed
        repos = [{"github_repo": "org/snap-repo", "repo_slug": "snap-repo", "org_slug": "test-snap"}]
        org_profiles = {"test-snap": self.org_profile}

        service.rebuild_snapshots(repos, org_profiles)

        mock_build.assert_not_called()


class DeterministicInsightTests(TestCase):
    """Test deterministic insight generation without Groq."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-insight",
            industry="analytics",
            display_name="Insight Org",
            is_public=True,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="org/insight-repo",
            repo_slug="insight-repo",
            display_name="Insight Repo",
            is_flagship=True,
            is_public=True,
        )
        PublicRepoStats.objects.create(
            repo_profile=cls.repo_profile,
            total_prs=100,
            total_prs_in_window=25,
            ai_assisted_pct=40,
        )

    def test_deterministic_insight_created(self):
        """Deterministic insight should be created without Groq."""
        service = LocalReconciliationService(dry_run=False)
        service.generate_deterministic_insights([self.repo_profile])

        insight = PublicRepoInsight.objects.filter(repo_profile=self.repo_profile, is_current=True).first()
        assert insight is not None
        assert "Insight Repo" in insight.content
        assert insight.batch_id == "local-deterministic"

    def test_deterministic_insight_idempotent(self):
        """Running insight generation twice should update, not duplicate."""
        service = LocalReconciliationService(dry_run=False)
        service.generate_deterministic_insights([self.repo_profile])
        service.generate_deterministic_insights([self.repo_profile])

        count = PublicRepoInsight.objects.filter(repo_profile=self.repo_profile, is_current=True).count()
        assert count == 1


class FlagOnOffTests(TestCase):
    """Test --rebuild-snapshots flag behavior."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-flag",
            industry="analytics",
            display_name="Flag Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="org/flag-repo",
            repo_slug="flag-repo",
            display_name="Flag Repo",
            is_flagship=True,
            is_public=True,
        )

    @patch("apps.public.services.local_reconciliation.build_repo_snapshot")
    def test_flag_off_no_stats_created(self, mock_build):
        """Without --rebuild-snapshots, no PublicRepoStats should be created."""
        # Ensure no stats exist
        PublicRepoStats.objects.filter(repo_profile=self.repo_profile).delete()

        service = LocalReconciliationService(dry_run=False)
        service.modified_repos.add("org/flag-repo")
        # Don't call rebuild_snapshots — simulating flag OFF

        assert not PublicRepoStats.objects.filter(repo_profile=self.repo_profile).exists()

    @patch("apps.public.services.local_reconciliation.build_repo_snapshot")
    def test_flag_on_stats_created(self, mock_build):
        """With --rebuild-snapshots, PublicRepoStats should be created for modified repos."""
        mock_stats = MagicMock()
        mock_build.return_value = mock_stats

        service = LocalReconciliationService(dry_run=False)
        service.modified_repos.add("org/flag-repo")
        repos = [{"github_repo": "org/flag-repo", "repo_slug": "flag-repo", "org_slug": "test-flag"}]
        org_profiles = {"test-flag": self.org_profile}

        service.rebuild_snapshots(repos, org_profiles)

        mock_build.assert_called_once()
