from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import PullRequest
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile
from apps.public.repo_snapshot_service import build_repo_snapshot


class RepoSnapshotServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="snapshot-org",
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
            github_repo="snapshot-org/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
        )
        cls.member = TeamMemberFactory(team=cls.team)

        # Create PRs in the last 30 days for this repo
        now = timezone.now()
        for i in range(5):
            pr_date = now - timedelta(days=i + 1)
            PullRequest.objects.create(
                team=cls.team,
                github_repo="snapshot-org/main-repo",
                github_pr_id=1000 + i,
                title=f"PR {i}",
                state="merged",
                pr_created_at=pr_date,
                merged_at=pr_date + timedelta(hours=6),
                cycle_time_hours=Decimal("6.0"),
                review_time_hours=Decimal("2.0"),
                is_ai_assisted=i % 2 == 0,
                author=cls.member,
                additions=100,
                deletions=50,
            )

        # Create PRs for a DIFFERENT repo (should NOT be included)
        for i in range(3):
            pr_date = now - timedelta(days=i + 1)
            PullRequest.objects.create(
                team=cls.team,
                github_repo="snapshot-org/other-repo",
                github_pr_id=2000 + i,
                title=f"Other PR {i}",
                state="merged",
                pr_created_at=pr_date,
                merged_at=pr_date + timedelta(hours=12),
                cycle_time_hours=Decimal("12.0"),
                review_time_hours=Decimal("4.0"),
                is_ai_assisted=False,
                author=cls.member,
                additions=200,
                deletions=100,
            )

    def test_snapshot_builder_uses_30_day_summary_window(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert snapshot.summary_window_days == 30

    def test_snapshot_builder_uses_90_day_trend_window(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert snapshot.trend_window_days == 90

    def test_snapshot_counts_only_target_repo_prs(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        # Only 5 PRs from main-repo, not 8 total
        assert snapshot.total_prs_in_window == 5

    def test_snapshot_computes_ai_pct(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        # 3 out of 5 are AI-assisted (i=0,2,4)
        assert snapshot.ai_assisted_pct == Decimal("60.00")

    def test_snapshot_stores_best_and_watchout_signals(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert isinstance(snapshot.best_signal, dict)
        assert isinstance(snapshot.watchout_signal, dict)

    def test_snapshot_stores_trend_data(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert isinstance(snapshot.trend_data, dict)

    def test_snapshot_stores_breakdown_data(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert isinstance(snapshot.breakdown_data, dict)

    def test_snapshot_stores_recent_prs(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert isinstance(snapshot.recent_prs, list)
        assert len(snapshot.recent_prs) <= 10

    def test_snapshot_sets_last_computed_at(self):
        snapshot = build_repo_snapshot(self.repo_profile)
        assert snapshot.last_computed_at is not None

    def test_snapshot_is_idempotent(self):
        snapshot1 = build_repo_snapshot(self.repo_profile)
        snapshot2 = build_repo_snapshot(self.repo_profile)
        assert snapshot1.pk == snapshot2.pk


class BaseQuerysetRepoFilterTests(TestCase):
    """Test that _base_pr_queryset respects github_repo filter."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMemberFactory(team=cls.team)
        now = timezone.now()

        for i in range(3):
            PullRequest.objects.create(
                team=cls.team,
                github_repo="org/repo-a",
                github_pr_id=3000 + i,
                title=f"Repo A PR {i}",
                state="merged",
                pr_created_at=now - timedelta(days=i + 1),
                merged_at=now - timedelta(days=i),
                author=cls.member,
            )
        for i in range(2):
            PullRequest.objects.create(
                team=cls.team,
                github_repo="org/repo-b",
                github_pr_id=4000 + i,
                title=f"Repo B PR {i}",
                state="merged",
                pr_created_at=now - timedelta(days=i + 1),
                merged_at=now - timedelta(days=i),
                author=cls.member,
            )

    def test_base_queryset_without_repo_returns_all(self):
        from apps.public.aggregations import _base_pr_queryset

        qs = _base_pr_queryset(self.team.id, start_date=timezone.now() - timedelta(days=30), end_date=timezone.now())
        assert qs.count() == 5

    def test_base_queryset_with_repo_filters(self):
        from apps.public.aggregations import _base_pr_queryset

        qs = _base_pr_queryset(
            self.team.id,
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now(),
            github_repo="org/repo-a",
        )
        assert qs.count() == 3

    def test_compute_team_summary_with_repo_filter(self):
        from apps.public.aggregations import compute_team_summary

        summary = compute_team_summary(
            self.team.id,
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now(),
            github_repo="org/repo-b",
        )
        assert summary["total_prs"] == 2

    def test_compute_ai_tools_breakdown_with_repo_filter(self):
        """compute_ai_tools_breakdown must respect github_repo filter."""
        from apps.public.aggregations import compute_ai_tools_breakdown

        # Without repo filter — returns tools from all repos (may be empty if no tools)
        all_tools = compute_ai_tools_breakdown(
            self.team.id,
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now(),
        )
        # With repo filter — should not error and should scope correctly
        repo_tools = compute_ai_tools_breakdown(
            self.team.id,
            start_date=timezone.now() - timedelta(days=30),
            end_date=timezone.now(),
            github_repo="org/repo-a",
        )
        # Both should return lists (possibly empty if no AI tools data)
        assert isinstance(all_tools, list)
        assert isinstance(repo_tools, list)

    def test_compute_team_summary_returns_30d_and_90d_contributors(self):
        """compute_team_summary must return both 30d and 90d contributor counts."""
        from apps.public.aggregations import compute_team_summary

        summary = compute_team_summary(
            self.team.id,
            start_date=timezone.now() - timedelta(days=90),
            end_date=timezone.now(),
        )
        assert "active_contributors_30d" in summary
        assert "active_contributors_90d" in summary


class ContributorWindowTests(TestCase):
    """Test that 30d and 90d contributor counts are distinct."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        now = timezone.now()

        # Member active only in last 30 days
        cls.recent_member = TeamMemberFactory(team=cls.team)
        PullRequest.objects.create(
            team=cls.team,
            github_repo="org/repo",
            github_pr_id=5000,
            title="Recent PR",
            state="merged",
            pr_created_at=now - timedelta(days=5),
            merged_at=now - timedelta(days=4),
            author=cls.recent_member,
        )

        # Member active only 60 days ago (in 90d window, outside 30d window)
        cls.older_member = TeamMemberFactory(team=cls.team)
        PullRequest.objects.create(
            team=cls.team,
            github_repo="org/repo",
            github_pr_id=5001,
            title="Older PR",
            state="merged",
            pr_created_at=now - timedelta(days=60),
            merged_at=now - timedelta(days=59),
            author=cls.older_member,
        )

    def test_30d_count_is_subset_of_90d(self):
        from apps.public.aggregations import compute_team_summary

        now = timezone.now()
        summary = compute_team_summary(
            self.team.id,
            start_date=now - timedelta(days=90),
            end_date=now,
        )
        assert summary["active_contributors_30d"] == 1
        assert summary["active_contributors_90d"] == 2

    def test_snapshot_uses_30d_contributor_count(self):
        """build_repo_snapshot must map 30d contributors, not 90d."""
        org_profile = PublicOrgProfile.objects.create(
            team=self.team,
            public_slug="contributor-test-org",
            industry="analytics",
            display_name="Contributor Test Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        repo_profile = PublicRepoProfile.objects.create(
            org_profile=org_profile,
            team=self.team,
            github_repo="org/repo",
            repo_slug="repo",
            display_name="Repo",
            is_flagship=True,
        )
        snapshot = build_repo_snapshot(repo_profile)
        # Should be 1 (only recent_member in last 30 days), not 2
        assert snapshot.active_contributors_30d == 1
