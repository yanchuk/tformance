"""
Tests for Slack leaderboard service.

Leaderboard computes weekly stats and posts to Slack channel.
"""

from datetime import UTC, date, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import SlackIntegrationFactory
from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestComputeWeeklyLeaderboard(TestCase):
    """Tests for compute_weekly_leaderboard function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        # Week starting Monday
        self.week_start = date(2025, 1, 6)  # A Monday

    def test_returns_top_guessers_up_to_3(self):
        """Test that compute_weekly_leaderboard returns top 3 guessers."""
        from apps.integrations.services.slack_leaderboard import compute_weekly_leaderboard

        # Create 4 reviewer members
        reviewers = TeamMemberFactory.create_batch(4, team=self.team)

        # Create an author
        author = TeamMemberFactory(team=self.team)

        # Create multiple PRs and have each reviewer guess on them
        # Reviewer 0: 5/5 correct (100%)
        # Reviewer 1: 4/5 correct (80%)
        # Reviewer 2: 3/5 correct (60%)
        # Reviewer 3: 2/5 correct (40%)
        for pr_idx in range(5):
            pr = PullRequestFactory(
                team=self.team,
                author=author,
                state="merged",
                merged_at=timezone.datetime(2025, 1, 8, 10, 0, tzinfo=UTC),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr, author=author, author_ai_assisted=True)

            # Create reviews from each reviewer
            for reviewer_idx, reviewer in enumerate(reviewers):
                correct_count = 5 - reviewer_idx
                guess_correct = pr_idx < correct_count
                PRSurveyReviewFactory(
                    team=self.team,
                    survey=survey,
                    reviewer=reviewer,
                    ai_guess=bool(guess_correct),
                    guess_correct=guess_correct,
                    responded_at=timezone.datetime(2025, 1, 8, 12, 0, tzinfo=UTC),
                )

        result = compute_weekly_leaderboard(self.team, self.week_start)

        # Should have top_guessers key
        self.assertIn("top_guessers", result)
        top_guessers = result["top_guessers"]

        # Should return top 3 only
        self.assertEqual(len(top_guessers), 3)

        # Check ordering and data structure
        self.assertEqual(top_guessers[0]["name"], reviewers[0].display_name)
        self.assertEqual(top_guessers[0]["correct"], 5)
        self.assertEqual(top_guessers[0]["total"], 5)
        self.assertEqual(top_guessers[0]["percentage"], 100)

    def test_returns_team_stats(self):
        """Test that compute_weekly_leaderboard returns team stats."""
        from apps.integrations.services.slack_leaderboard import compute_weekly_leaderboard

        member = TeamMemberFactory(team=self.team)

        # Create merged PRs in the week
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.datetime(2025, 1, 7 + i % 3, 10, 0, tzinfo=UTC),
            )
            survey = PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=member,
                author_ai_assisted=(i % 2 == 0),  # 3 AI-assisted, 2 not
                author_responded_at=timezone.datetime(2025, 1, 7 + i % 3, 11, 0, tzinfo=UTC),
            )
            # Add quality rating
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                reviewer=member,
                quality_rating=3,
                responded_at=timezone.datetime(2025, 1, 7 + i % 3, 12, 0, tzinfo=UTC),
            )

        result = compute_weekly_leaderboard(self.team, self.week_start)

        # Check team_stats
        self.assertIn("team_stats", result)
        stats = result["team_stats"]

        self.assertEqual(stats["prs_merged"], 5)
        self.assertEqual(stats["ai_percentage"], 60)  # 3/5 = 60%
        self.assertIsNotNone(stats["detection_rate"])
        self.assertEqual(stats["avg_rating"], Decimal("3.00"))

    def test_returns_quality_champions(self):
        """Test that compute_weekly_leaderboard returns quality champions."""
        from apps.integrations.services.slack_leaderboard import compute_weekly_leaderboard

        member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        member2 = TeamMemberFactory(team=self.team, display_name="Bob")

        # Bob gives most "Super" ratings (as a reviewer)
        for _ in range(3):
            pr = PullRequestFactory(
                team=self.team,
                author=member1,
                state="merged",
                merged_at=timezone.datetime(2025, 1, 8, 10, 0, tzinfo=UTC),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr, author=member1)
            PRSurveyReviewFactory(team=self.team, survey=survey, reviewer=member2, quality_rating=3)

        # Alice has fastest review time on her PR (as author)
        pr = PullRequestFactory(
            team=self.team,
            author=member1,
            state="merged",
            merged_at=timezone.datetime(2025, 1, 8, 12, 0, tzinfo=UTC),
            pr_created_at=timezone.datetime(2025, 1, 8, 10, 0, tzinfo=UTC),
            review_time_hours=Decimal("0.5"),  # 30 minutes
        )

        result = compute_weekly_leaderboard(self.team, self.week_start)

        # Check quality_champions
        self.assertIn("quality_champions", result)
        champions = result["quality_champions"]

        self.assertIn("super_champion", champions)
        self.assertEqual(champions["super_champion"]["name"], "Bob")  # Bob is the reviewer who gave 3 Super ratings
        self.assertEqual(champions["super_champion"]["super_count"], 3)

        self.assertIn("fast_reviewer", champions)
        self.assertEqual(champions["fast_reviewer"]["name"], "Alice")  # Alice's PR had the fastest review time
        self.assertAlmostEqual(float(champions["fast_reviewer"]["fastest_review_hours"]), 0.5, places=1)

    def test_handles_fewer_than_3_participants(self):
        """Test that compute_weekly_leaderboard handles <3 participants."""
        from apps.integrations.services.slack_leaderboard import compute_weekly_leaderboard

        # Create only 2 members
        members = TeamMemberFactory.create_batch(2, team=self.team)

        for member in members:
            pr = PullRequestFactory(
                team=self.team,
                author=member,
                state="merged",
                merged_at=timezone.datetime(2025, 1, 8, 10, 0, tzinfo=UTC),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr, author=member, author_ai_assisted=True)
            PRSurveyReviewFactory(team=self.team, survey=survey, reviewer=member, ai_guess=True, guess_correct=True)

        result = compute_weekly_leaderboard(self.team, self.week_start)

        # Should return only 2 guessers
        self.assertEqual(len(result["top_guessers"]), 2)

    def test_handles_no_prs_merged(self):
        """Test that compute_weekly_leaderboard handles no PRs merged."""
        from apps.integrations.services.slack_leaderboard import compute_weekly_leaderboard

        # No PRs created
        result = compute_weekly_leaderboard(self.team, self.week_start)

        # Should return empty or zero values
        self.assertEqual(result["team_stats"]["prs_merged"], 0)
        self.assertEqual(len(result["top_guessers"]), 0)


class TestBuildLeaderboardBlocks(TestCase):
    """Tests for build_leaderboard_blocks function."""

    def test_returns_valid_block_kit_blocks(self):
        """Test that build_leaderboard_blocks returns valid Block Kit blocks."""
        from apps.integrations.services.slack_leaderboard import build_leaderboard_blocks

        leaderboard_data = {
            "top_guessers": [
                {"name": "Alice", "correct": 5, "total": 5, "percentage": 100},
                {"name": "Bob", "correct": 4, "total": 5, "percentage": 80},
            ],
            "team_stats": {
                "prs_merged": 10,
                "ai_percentage": 60,
                "detection_rate": 75,
                "avg_rating": Decimal("2.80"),
            },
            "quality_champions": {
                "super_champion": {"name": "Alice", "super_count": 3},
                "fast_reviewer": {"name": "Bob", "fastest_review_hours": Decimal("1.5")},
            },
        }
        date_range = "Jan 6 - Jan 12, 2025"

        blocks = build_leaderboard_blocks(leaderboard_data, date_range)

        # Should be a list
        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)

        # Should contain header with trophy emoji
        blocks_str = str(blocks)
        self.assertIn("🏆", blocks_str)
        self.assertIn("Leaderboard", blocks_str)
        self.assertIn("Jan 6 - Jan 12, 2025", blocks_str)

        # Should contain top guessers
        self.assertIn("Alice", blocks_str)
        self.assertIn("Bob", blocks_str)

        # Should contain team stats
        self.assertIn("10", blocks_str)  # prs_merged
        self.assertIn("60", blocks_str)  # ai_percentage


class TestShouldPostLeaderboard(TestCase):
    """Tests for should_post_leaderboard function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.integration = SlackIntegrationFactory(
            team=self.team,
            leaderboard_enabled=True,
            leaderboard_day=0,  # Monday
            leaderboard_time=time(9, 0),  # 9 AM
        )

    def test_returns_true_when_day_and_time_match(self):
        """Test that should_post_leaderboard returns True when day/time match."""
        from apps.integrations.services.slack_leaderboard import should_post_leaderboard

        # Mock current time to Monday 9 AM
        with patch("apps.integrations.services.slack_leaderboard.timezone") as mock_tz:
            mock_now = timezone.datetime(2025, 1, 6, 9, 0, tzinfo=UTC)  # Monday 9 AM
            mock_tz.now.return_value = mock_now

            result = should_post_leaderboard(self.integration)

            self.assertTrue(result)

    def test_returns_false_when_disabled(self):
        """Test that should_post_leaderboard returns False when disabled."""
        from apps.integrations.services.slack_leaderboard import should_post_leaderboard

        self.integration.leaderboard_enabled = False
        self.integration.save()

        with patch("apps.integrations.services.slack_leaderboard.timezone") as mock_tz:
            mock_now = timezone.datetime(2025, 1, 6, 9, 0, tzinfo=UTC)
            mock_tz.now.return_value = mock_now

            result = should_post_leaderboard(self.integration)

            self.assertFalse(result)

    def test_returns_false_when_day_does_not_match(self):
        """Test that should_post_leaderboard returns False when day doesn't match."""
        from apps.integrations.services.slack_leaderboard import should_post_leaderboard

        # Set to Monday, but current time is Tuesday
        with patch("apps.integrations.services.slack_leaderboard.timezone") as mock_tz:
            mock_now = timezone.datetime(2025, 1, 7, 9, 0, tzinfo=UTC)  # Tuesday 9 AM
            mock_tz.now.return_value = mock_now

            result = should_post_leaderboard(self.integration)

            self.assertFalse(result)


class TestPostWeeklyLeaderboardsTask(TestCase):
    """Tests for post_weekly_leaderboards_task Celery task."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()

    @patch("apps.integrations.tasks.send_channel_message")
    @patch("apps.integrations.tasks.get_slack_client")
    @patch("apps.integrations.tasks.should_post_leaderboard")
    @patch("apps.integrations.tasks.compute_weekly_leaderboard")
    def test_posts_leaderboards_and_returns_counts(
        self, mock_compute, mock_should_post, mock_get_client, mock_send_message
    ):
        """Test that post_weekly_leaderboards_task posts and returns counts."""
        from apps.integrations.tasks import post_weekly_leaderboards_task

        # Create integration
        SlackIntegrationFactory(
            team=self.team,
            leaderboard_enabled=True,
            leaderboard_channel_id="C12345",
        )

        # Mock should_post_leaderboard to return True
        mock_should_post.return_value = True

        # Mock compute_weekly_leaderboard
        mock_compute.return_value = {
            "top_guessers": [],
            "team_stats": {"prs_merged": 5, "ai_percentage": 50, "detection_rate": 70, "avg_rating": Decimal("2.5")},
            "quality_champions": {},
        }

        # Mock Slack client
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_send_message.return_value = {"ok": True}

        # Run task
        result = post_weekly_leaderboards_task()

        # Check result
        self.assertIn("teams_checked", result)
        self.assertIn("leaderboards_posted", result)
        self.assertIn("errors", result)

        self.assertEqual(result["teams_checked"], 1)
        self.assertEqual(result["leaderboards_posted"], 1)
        self.assertEqual(len(result["errors"]), 0)

        # Verify send_channel_message was called
        mock_send_message.assert_called_once()
