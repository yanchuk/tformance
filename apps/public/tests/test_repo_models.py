from django.db import IntegrityError
from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoInsight,
    PublicRepoProfile,
    PublicRepoStats,
)


class PublicRepoProfileTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="testorg",
            industry="analytics",
            display_name="Test Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=600,
        )

    def test_repo_profile_creation(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="testorg/testrepo",
            repo_slug="testrepo",
            display_name="Test Repo",
        )
        assert repo.pk is not None
        assert repo.org_profile == self.org_profile
        assert repo.github_repo == "testorg/testrepo"
        assert repo.is_flagship is False
        assert repo.is_public is True

    def test_repo_slug_must_be_unique_within_org(self):
        PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="testorg/repo-a",
            repo_slug="same-slug",
            display_name="Repo A",
        )
        with self.assertRaises(IntegrityError):
            PublicRepoProfile.objects.create(
                org_profile=self.org_profile,
                team=self.team,
                github_repo="testorg/repo-b",
                repo_slug="same-slug",
                display_name="Repo B",
            )

    def test_repo_profile_related_name(self):
        PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="testorg/myrepo",
            repo_slug="myrepo",
            display_name="My Repo",
        )
        assert self.org_profile.repos.count() == 1

    def test_repo_str(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="testorg/str-test",
            repo_slug="str-test",
            display_name="Str Test",
        )
        assert str(repo) == "Str Test"


class PublicRepoStatsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="statsorg",
            industry="analytics",
            display_name="Stats Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(org_profile=cls.org_profile, total_prs=600)
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="statsorg/repo",
            repo_slug="repo",
            display_name="Repo",
        )

    def test_repo_stats_creation(self):
        stats = PublicRepoStats.objects.create(
            repo_profile=self.repo_profile,
            total_prs=100,
            total_prs_in_window=40,
        )
        assert stats.summary_window_days == 30
        assert stats.trend_window_days == 90

    def test_repo_stats_onetoone(self):
        PublicRepoStats.objects.create(
            repo_profile=self.repo_profile,
            total_prs=50,
        )
        with self.assertRaises(IntegrityError):
            PublicRepoStats.objects.create(
                repo_profile=self.repo_profile,
                total_prs=60,
            )

    def test_repo_stats_related_name(self):
        PublicRepoStats.objects.create(
            repo_profile=self.repo_profile,
            total_prs=50,
        )
        assert self.repo_profile.stats.total_prs == 50


class PublicRepoInsightTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="insightorg",
            industry="analytics",
            display_name="Insight Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(org_profile=cls.org_profile, total_prs=600)
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="insightorg/repo",
            repo_slug="repo",
            display_name="Repo",
        )

    def test_insight_creation(self):
        insight = PublicRepoInsight.objects.create(
            repo_profile=self.repo_profile,
            content="This repo shows strong AI adoption.",
            insight_type="weekly",
            is_current=True,
            batch_id="batch-001",
        )
        assert insight.pk is not None
        assert insight.is_current is True

    def test_multiple_insights_per_repo(self):
        PublicRepoInsight.objects.create(
            repo_profile=self.repo_profile,
            content="Old insight",
            insight_type="weekly",
            is_current=False,
            batch_id="batch-001",
        )
        PublicRepoInsight.objects.create(
            repo_profile=self.repo_profile,
            content="New insight",
            insight_type="weekly",
            is_current=True,
            batch_id="batch-002",
        )
        assert self.repo_profile.insights.filter(is_current=True).count() == 1
        assert self.repo_profile.insights.count() == 2
