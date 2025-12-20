"""Tests for the scenario data generator."""

from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.models import (
    AIUsageDaily,
    Commit,
    PRReview,
    PRSurvey,
    PullRequest,
    TeamMember,
    WeeklyMetrics,
)
from apps.metrics.seeding.data_generator import (
    GeneratorStats,
    MemberWithArchetype,
    ScenarioDataGenerator,
)
from apps.metrics.seeding.scenarios import get_scenario
from apps.teams.models import Team


class TestGeneratorStats(TestCase):
    """Tests for the GeneratorStats dataclass."""

    def test_default_values(self):
        """GeneratorStats should initialize with zeros."""
        stats = GeneratorStats()

        self.assertEqual(stats.team_members_created, 0)
        self.assertEqual(stats.prs_created, 0)
        self.assertEqual(stats.reviews_created, 0)
        self.assertEqual(stats.commits_created, 0)
        self.assertEqual(stats.surveys_created, 0)
        self.assertEqual(stats.github_prs_used, 0)
        self.assertEqual(stats.factory_prs_used, 0)


class TestScenarioDataGenerator(TestCase):
    """Tests for the ScenarioDataGenerator class."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.scenario = get_scenario("ai-success")

    def tearDown(self):
        """Clean up test data."""
        # Clean up in reverse dependency order
        WeeklyMetrics.objects.filter(team=self.team).delete()
        AIUsageDaily.objects.filter(team=self.team).delete()
        PRReview.objects.filter(team=self.team).delete()
        Commit.objects.filter(team=self.team).delete()
        PRSurvey.objects.filter(team=self.team).delete()
        PullRequest.objects.filter(team=self.team).delete()
        TeamMember.objects.filter(team=self.team).delete()
        self.team.delete()

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_creates_team_members(self, mock_fetcher_class):
        """Generator should create team members based on archetypes."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )

        stats = generator.generate(self.team)

        # ai-success has 5 members (2 early_adopter, 2 follower, 1 skeptic)
        self.assertEqual(stats.team_members_created, 5)
        self.assertEqual(TeamMember.objects.filter(team=self.team).count(), 5)

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_creates_prs(self, mock_fetcher_class):
        """Generator should create PRs for each week."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )

        stats = generator.generate(self.team)

        # Should have created PRs
        self.assertGreater(stats.prs_created, 0)
        self.assertEqual(
            PullRequest.objects.filter(team=self.team).count(),
            stats.prs_created,
        )

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_creates_reviews(self, mock_fetcher_class):
        """Generator should create reviews for non-open PRs."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )

        stats = generator.generate(self.team)

        self.assertGreater(stats.reviews_created, 0)
        self.assertEqual(
            PRReview.objects.filter(team=self.team).count(),
            stats.reviews_created,
        )

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_creates_commits(self, mock_fetcher_class):
        """Generator should create commits for PRs."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )

        stats = generator.generate(self.team)

        self.assertGreater(stats.commits_created, 0)
        self.assertEqual(
            Commit.objects.filter(team=self.team).count(),
            stats.commits_created,
        )

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_creates_weekly_metrics(self, mock_fetcher_class):
        """Generator should create WeeklyMetrics records."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )

        stats = generator.generate(self.team)

        self.assertGreater(stats.weekly_metrics_created, 0)
        self.assertEqual(
            WeeklyMetrics.objects.filter(team=self.team).count(),
            stats.weekly_metrics_created,
        )

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_same_seed_produces_same_counts(self, mock_fetcher_class):
        """Same seed should produce reproducible results."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        # First run
        generator1 = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )
        stats1 = generator1.generate(self.team)

        # Clean up
        self.tearDown()
        self.team = Team.objects.create(name="Test Team 2", slug="test-team-2")

        # Second run with same seed
        generator2 = ScenarioDataGenerator(
            scenario=get_scenario("ai-success"),
            seed=42,
            fetch_github=False,
        )
        stats2 = generator2.generate(self.team)

        # Counts should match
        self.assertEqual(stats1.prs_created, stats2.prs_created)
        self.assertEqual(stats1.reviews_created, stats2.reviews_created)
        self.assertEqual(stats1.commits_created, stats2.commits_created)

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_different_seed_produces_different_results(self, mock_fetcher_class):
        """Different seeds should produce different results."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        # First run
        generator1 = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )
        stats1 = generator1.generate(self.team)

        # Clean up
        self.tearDown()
        self.team = Team.objects.create(name="Test Team 2", slug="test-team-2")

        # Second run with different seed
        generator2 = ScenarioDataGenerator(
            scenario=get_scenario("ai-success"),
            seed=999,
            fetch_github=False,
        )
        stats2 = generator2.generate(self.team)

        # At least one count should differ (very likely with different seeds)
        # We check the reviews since they have more variance
        # Note: It's theoretically possible they match, but extremely unlikely
        different = (
            stats1.prs_created != stats2.prs_created
            or stats1.reviews_created != stats2.reviews_created
            or stats1.commits_created != stats2.commits_created
        )
        self.assertTrue(different, "Different seeds should produce different results")

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_uses_github_data_when_enabled(self, mock_fetcher_class):
        """Generator should use GitHub PR data when fetch_github=True."""
        from apps.metrics.seeding.github_fetcher import FetchedPR

        mock_pr = FetchedPR(
            title="GitHub PR Title",
            additions=500,
            deletions=100,
            files_changed=10,
            commits_count=5,
            labels=["enhancement"],
            is_draft=False,
            review_comments_count=3,
        )
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_prs.return_value = [mock_pr]
        mock_fetcher_class.return_value = mock_fetcher

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=True,
            github_percentage=1.0,  # Use GitHub for all PRs
        )

        stats = generator.generate(self.team)

        # Should have used GitHub PRs
        self.assertGreater(stats.github_prs_used, 0)

        # Check that some PRs have the GitHub title
        github_titled_prs = PullRequest.objects.filter(
            team=self.team,
            title="GitHub PR Title",
        )
        self.assertGreater(github_titled_prs.count(), 0)

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_generator_falls_back_to_factory_when_no_github(self, mock_fetcher_class):
        """Generator should use factory when GitHub data unavailable."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=True,
            github_percentage=0.25,
        )

        stats = generator.generate(self.team)

        # Should have used factory for all PRs
        self.assertEqual(stats.github_prs_used, 0)
        self.assertGreater(stats.factory_prs_used, 0)


class TestScenarioDataGeneratorWithBottleneck(TestCase):
    """Tests for data generator with review-bottleneck scenario."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Bottleneck Team", slug="bottleneck")
        self.scenario = get_scenario("review-bottleneck")

    def tearDown(self):
        """Clean up test data."""
        WeeklyMetrics.objects.filter(team=self.team).delete()
        AIUsageDaily.objects.filter(team=self.team).delete()
        PRReview.objects.filter(team=self.team).delete()
        Commit.objects.filter(team=self.team).delete()
        PRSurvey.objects.filter(team=self.team).delete()
        PullRequest.objects.filter(team=self.team).delete()
        TeamMember.objects.filter(team=self.team).delete()
        self.team.delete()

    @patch("apps.metrics.seeding.data_generator.GitHubPublicFetcher")
    def test_bottleneck_reviewer_gets_more_reviews(self, mock_fetcher_class):
        """Bottleneck reviewer should handle majority of reviews."""
        mock_fetcher_class.return_value.fetch_prs.return_value = []

        generator = ScenarioDataGenerator(
            scenario=self.scenario,
            seed=42,
            fetch_github=False,
        )

        generator.generate(self.team)

        # Find the bottleneck reviewer (should have most reviews)
        members = TeamMember.objects.filter(team=self.team)
        review_counts = {}
        for member in members:
            review_counts[member.id] = PRReview.objects.filter(
                team=self.team,
                reviewer=member,
            ).count()

        # The member with most reviews should have significantly more
        max_reviews = max(review_counts.values())
        total_reviews = sum(review_counts.values())

        if total_reviews > 0:
            bottleneck_ratio = max_reviews / total_reviews
            # Bottleneck should have noticeably more than average (1/5 = 20%)
            # With 60% weight, expect ~30%+ after accounting for randomness
            self.assertGreater(
                bottleneck_ratio,
                0.25,
                f"Bottleneck reviewer should have >25% of reviews, got {bottleneck_ratio:.0%}",
            )


class TestMemberWithArchetype(TestCase):
    """Tests for the MemberWithArchetype dataclass."""

    def test_member_archetype_pairing(self):
        """MemberWithArchetype should pair member with archetype."""
        from apps.metrics.seeding.scenarios.base import MemberArchetype

        team = Team.objects.create(name="Test", slug="test")
        member = TeamMember.objects.create(
            team=team,
            display_name="Test User",
            email="test@example.com",
        )
        archetype = MemberArchetype(
            name="test_archetype",
            count=1,
            ai_adoption_modifier=0.1,
        )

        pair = MemberWithArchetype(member=member, archetype=archetype)

        self.assertEqual(pair.member, member)
        self.assertEqual(pair.archetype, archetype)

        # Cleanup
        member.delete()
        team.delete()
