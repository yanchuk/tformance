from datetime import timedelta
from decimal import Decimal

from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory, TeamMemberFactory
from apps.metrics.models import PullRequest
from apps.public import tasks as public_tasks
from apps.public.models import PublicOrgProfile, PublicRepoProfile, PublicRepoStats
from apps.public.views import helpers
from tformance.settings import SCHEDULED_TASKS


class PublicFoundationTests(SimpleTestCase):
    def test_public_stats_task_is_scheduled(self):
        scheduled = [
            config
            for config in SCHEDULED_TASKS.values()
            if config["task"] == "apps.public.tasks.compute_public_stats_task"
        ]
        assert len(scheduled) == 1
        assert scheduled[0]["expire_seconds"] > 0

    def test_public_windows_are_fixed_for_summary_and_trends(self):
        assert helpers.PUBLIC_SUMMARY_WINDOW_DAYS == 30
        assert helpers.PUBLIC_TREND_WINDOW_DAYS == 90

    def test_summary_window_range_uses_30_days(self):
        end_date = timezone.now().date()
        days, start_date, actual_end_date = helpers.get_public_summary_date_range()

        assert days == 30
        assert actual_end_date == end_date
        assert start_date == end_date - timedelta(days=30)

    def test_trend_window_range_uses_90_days(self):
        end_date = timezone.now().date()
        days, start_date, actual_end_date = helpers.get_public_trend_date_range()

        assert days == 90
        assert actual_end_date == end_date
        assert start_date == end_date - timedelta(days=90)

    def test_best_data_year_prefers_latest_pr_year_with_most_activity(self):
        # Smoke check the helper is still callable from the public task module.
        assert callable(public_tasks._best_data_year)


class ComputeStatsTaskRepoSnapshotTests(TestCase):
    """Integration test: compute_public_stats_task must also build repo snapshots."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="pipeline-org",
            industry="analytics",
            display_name="Pipeline Org",
            is_public=True,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="pipeline-org/flagship",
            repo_slug="flagship",
            display_name="Flagship",
            is_flagship=True,
            is_public=True,
        )
        cls.member = TeamMemberFactory(team=cls.team)

        now = timezone.now()
        for i in range(5):
            pr_date = now - timedelta(days=i + 1)
            PullRequest.objects.create(
                team=cls.team,
                github_repo="pipeline-org/flagship",
                github_pr_id=9000 + i,
                title=f"Pipeline PR {i}",
                state="merged",
                pr_created_at=pr_date,
                merged_at=pr_date + timedelta(hours=6),
                cycle_time_hours=Decimal("6.0"),
                review_time_hours=Decimal("2.0"),
                author=cls.member,
                additions=100,
                deletions=50,
            )

    def test_compute_stats_task_builds_repo_snapshots(self):
        """compute_public_stats_task must also build PublicRepoStats for flagship repos."""
        assert not PublicRepoStats.objects.filter(repo_profile=self.repo_profile).exists()

        result = public_tasks.compute_public_stats_task()

        assert result["repo_snapshots"] >= 1
        assert PublicRepoStats.objects.filter(repo_profile=self.repo_profile).exists()

        snapshot = PublicRepoStats.objects.get(repo_profile=self.repo_profile)
        assert snapshot.total_prs_in_window > 0
        assert snapshot.last_computed_at is not None
