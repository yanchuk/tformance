"""Tests for quick stats service."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.quick_stats import get_team_quick_stats


class TestGetTeamQuickStats(TestCase):
    """Tests for get_team_quick_stats service function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.member2 = TeamMemberFactory(team=self.team, display_name="Bob")

    def test_returns_correct_structure_with_no_data(self):
        """Test that function returns correct structure when there's no data."""
        stats = get_team_quick_stats(self.team, days=7)

        self.assertIsInstance(stats, dict)
        self.assertIn("prs_merged", stats)
        self.assertIn("prs_merged_change", stats)
        self.assertIn("avg_cycle_time_hours", stats)
        self.assertIn("cycle_time_change", stats)
        self.assertIn("ai_assisted_percent", stats)
        self.assertIn("ai_percent_change", stats)
        self.assertIn("avg_quality_rating", stats)
        self.assertIn("quality_change", stats)
        self.assertIn("recent_activity", stats)

        # With no data, should return zero/None values
        self.assertEqual(stats["prs_merged"], 0)
        self.assertEqual(stats["prs_merged_change"], 0.0)
        self.assertIsNone(stats["avg_cycle_time_hours"])
        self.assertIsNone(stats["cycle_time_change"])
        self.assertEqual(stats["ai_assisted_percent"], 0.0)
        self.assertEqual(stats["ai_percent_change"], 0.0)
        self.assertIsNone(stats["avg_quality_rating"])
        self.assertIsNone(stats["quality_change"])
        self.assertIsInstance(stats["recent_activity"], list)
        self.assertEqual(len(stats["recent_activity"]), 0)

    def test_prs_merged_count_is_correct_for_period(self):
        """Test that prs_merged counts only merged PRs in the current period."""
        now = timezone.now()

        # Create 3 PRs merged in last 7 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=5),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(hours=12),
        )

        # Create 1 PR merged outside the 7-day window
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=10),
        )

        # Create 1 open PR (should not be counted)
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="open",
            merged_at=None,
        )

        stats = get_team_quick_stats(self.team, days=7)
        self.assertEqual(stats["prs_merged"], 3)

    def test_prs_merged_change_calculates_percentage_correctly(self):
        """Test that prs_merged_change calculates % change vs previous period."""
        now = timezone.now()

        # Current period (last 7 days): 4 PRs
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=i),
            )

        # Previous period (8-14 days ago): 2 PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=8 + i),
            )

        stats = get_team_quick_stats(self.team, days=7)

        # 4 current vs 2 previous = +100% change
        self.assertEqual(stats["prs_merged"], 4)
        self.assertEqual(stats["prs_merged_change"], 100.0)

    def test_prs_merged_change_handles_zero_previous_period(self):
        """Test that prs_merged_change handles zero PRs in previous period."""
        now = timezone.now()

        # Current period: 3 PRs, Previous period: 0 PRs
        for i in range(3):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=i),
            )

        stats = get_team_quick_stats(self.team, days=7)

        # When previous is 0 and current > 0, change should be 100%
        self.assertEqual(stats["prs_merged"], 3)
        self.assertEqual(stats["prs_merged_change"], 100.0)

    def test_prs_merged_change_handles_negative_change(self):
        """Test that prs_merged_change handles negative change correctly."""
        now = timezone.now()

        # Current period: 2 PRs
        for i in range(2):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=i),
            )

        # Previous period: 4 PRs
        for i in range(4):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=8 + i),
            )

        stats = get_team_quick_stats(self.team, days=7)

        # 2 current vs 4 previous = -50% change
        self.assertEqual(stats["prs_merged"], 2)
        self.assertEqual(stats["prs_merged_change"], -50.0)

    def test_avg_cycle_time_hours_is_calculated_correctly(self):
        """Test that avg_cycle_time_hours is calculated from merged PRs."""
        now = timezone.now()

        # Create 3 merged PRs with different cycle times
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
            cycle_time_hours=Decimal("10.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
            cycle_time_hours=Decimal("20.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=3),
            cycle_time_hours=Decimal("30.00"),
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Average = (10 + 20 + 30) / 3 = 20.00
        self.assertEqual(stats["avg_cycle_time_hours"], 20.0)

    def test_avg_cycle_time_hours_ignores_null_values(self):
        """Test that avg_cycle_time_hours ignores PRs with null cycle times."""
        now = timezone.now()

        # Create 2 PRs with cycle times
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
            cycle_time_hours=Decimal("10.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
            cycle_time_hours=Decimal("20.00"),
        )

        # Create 1 PR without cycle time (should be ignored)
        PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=3),
            cycle_time_hours=None,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Average = (10 + 20) / 2 = 15.00
        self.assertEqual(stats["avg_cycle_time_hours"], 15.0)

    def test_avg_cycle_time_hours_returns_none_when_no_data(self):
        """Test that avg_cycle_time_hours returns None when no PRs with cycle times exist."""
        now = timezone.now()

        # Create a PR without cycle time
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
            cycle_time_hours=None,
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertIsNone(stats["avg_cycle_time_hours"])

    def test_cycle_time_change_compares_to_previous_period(self):
        """Test that cycle_time_change calculates % change vs previous period."""
        now = timezone.now()

        # Current period: avg 20 hours
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
            cycle_time_hours=Decimal("20.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
            cycle_time_hours=Decimal("20.00"),
        )

        # Previous period: avg 10 hours
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=8),
            cycle_time_hours=Decimal("10.00"),
        )
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=9),
            cycle_time_hours=Decimal("10.00"),
        )

        stats = get_team_quick_stats(self.team, days=7)

        # 20 current vs 10 previous = +100% change
        self.assertEqual(stats["avg_cycle_time_hours"], 20.0)
        self.assertEqual(stats["cycle_time_change"], 100.0)

    def test_cycle_time_change_returns_none_when_no_previous_data(self):
        """Test that cycle_time_change returns None when no previous period data exists."""
        now = timezone.now()

        # Only current period data
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
            cycle_time_hours=Decimal("20.00"),
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertEqual(stats["avg_cycle_time_hours"], 20.0)
        self.assertIsNone(stats["cycle_time_change"])

    def test_ai_assisted_percent_is_calculated_from_pr_survey_data(self):
        """Test that ai_assisted_percent is calculated from PRSurvey data."""
        now = timezone.now()

        # Create 4 PRs with surveys in current period
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author=self.member1,
            author_ai_assisted=True,
        )

        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author=self.member1,
            author_ai_assisted=True,
        )

        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=3),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr3,
            author=self.member2,
            author_ai_assisted=False,
        )

        pr4 = PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=4),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr4,
            author=self.member2,
            author_ai_assisted=False,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # 2 out of 4 = 50%
        self.assertEqual(stats["ai_assisted_percent"], 50.0)

    def test_ai_assisted_percent_ignores_null_survey_responses(self):
        """Test that ai_assisted_percent ignores surveys where author_ai_assisted is None."""
        now = timezone.now()

        # Create 2 PRs with answered surveys
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author=self.member1,
            author_ai_assisted=True,
        )

        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author=self.member1,
            author_ai_assisted=False,
        )

        # Create 1 PR with unanswered survey (should be ignored)
        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=3),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr3,
            author=self.member2,
            author_ai_assisted=None,  # Not yet answered
        )

        stats = get_team_quick_stats(self.team, days=7)

        # 1 out of 2 answered = 50%
        self.assertEqual(stats["ai_assisted_percent"], 50.0)

    def test_ai_assisted_percent_returns_zero_when_no_surveys(self):
        """Test that ai_assisted_percent returns 0 when no survey data exists."""
        now = timezone.now()

        # Create PRs without surveys
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertEqual(stats["ai_assisted_percent"], 0.0)

    def test_ai_percent_change_calculates_percentage_point_change(self):
        """Test that ai_percent_change calculates percentage point change."""
        now = timezone.now()

        # Current period: 75% AI-assisted (3 out of 4)
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=i),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member1,
                author_ai_assisted=True,
            )

        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=3),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member1,
            author_ai_assisted=False,
        )

        # Previous period: 25% AI-assisted (1 out of 4)
        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=8),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member1,
            author_ai_assisted=True,
        )

        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(days=9 + i),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author=self.member1,
                author_ai_assisted=False,
            )

        stats = get_team_quick_stats(self.team, days=7)

        # 75% current - 25% previous = +50 percentage points
        self.assertEqual(stats["ai_assisted_percent"], 75.0)
        self.assertEqual(stats["ai_percent_change"], 50.0)

    def test_avg_quality_rating_is_calculated_from_pr_survey_review_data(self):
        """Test that avg_quality_rating is calculated from PRSurveyReview data."""
        now = timezone.now()

        # Create 3 PRs with survey reviews in current period
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        survey1 = PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author=self.member1,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey1,
            reviewer=self.member2,
            quality_rating=3,
        )

        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
        )
        survey2 = PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author=self.member1,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey2,
            reviewer=self.member2,
            quality_rating=2,
        )

        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=3),
        )
        survey3 = PRSurveyFactory(
            team=self.team,
            pull_request=pr3,
            author=self.member2,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey3,
            reviewer=self.member1,
            quality_rating=1,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Average = (3 + 2 + 1) / 3 = 2.0
        self.assertEqual(stats["avg_quality_rating"], 2.0)

    def test_avg_quality_rating_handles_multiple_reviews_per_pr(self):
        """Test that avg_quality_rating handles multiple reviews per PR correctly."""
        now = timezone.now()

        # Create 1 PR with 2 reviews
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        survey1 = PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author=self.member1,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey1,
            reviewer=self.member2,
            quality_rating=3,
        )
        reviewer3 = TeamMemberFactory(team=self.team, display_name="Charlie")
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey1,
            reviewer=reviewer3,
            quality_rating=1,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Average = (3 + 1) / 2 = 2.0
        self.assertEqual(stats["avg_quality_rating"], 2.0)

    def test_avg_quality_rating_ignores_null_ratings(self):
        """Test that avg_quality_rating ignores reviews with null quality_rating."""
        now = timezone.now()

        # Create 2 reviews with ratings
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        survey1 = PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author=self.member1,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey1,
            reviewer=self.member2,
            quality_rating=3,
        )

        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
        )
        survey2 = PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author=self.member1,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey2,
            reviewer=self.member2,
            quality_rating=1,
        )

        # Create 1 review without rating
        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=3),
        )
        survey3 = PRSurveyFactory(
            team=self.team,
            pull_request=pr3,
            author=self.member2,
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey3,
            reviewer=self.member1,
            quality_rating=None,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Average = (3 + 1) / 2 = 2.0
        self.assertEqual(stats["avg_quality_rating"], 2.0)

    def test_avg_quality_rating_returns_none_when_no_reviews(self):
        """Test that avg_quality_rating returns None when no review data exists."""
        now = timezone.now()

        # Create PR with survey but no reviews
        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member1,
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertIsNone(stats["avg_quality_rating"])

    def test_quality_change_compares_to_previous_period(self):
        """Test that quality_change calculates change vs previous period."""
        now = timezone.now()

        # Current period: avg 3.0
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        survey1 = PRSurveyFactory(team=self.team, pull_request=pr1, author=self.member1)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey1,
            reviewer=self.member2,
            quality_rating=3,
        )

        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
        )
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author=self.member1)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey2,
            reviewer=self.member2,
            quality_rating=3,
        )

        # Previous period: avg 2.0
        pr3 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=8),
        )
        survey3 = PRSurveyFactory(team=self.team, pull_request=pr3, author=self.member1)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey3,
            reviewer=self.member2,
            quality_rating=2,
        )

        pr4 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=9),
        )
        survey4 = PRSurveyFactory(team=self.team, pull_request=pr4, author=self.member1)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey4,
            reviewer=self.member2,
            quality_rating=2,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # 3.0 current - 2.0 previous = +1.0 change
        self.assertEqual(stats["avg_quality_rating"], 3.0)
        self.assertEqual(stats["quality_change"], 1.0)

    def test_quality_change_returns_none_when_no_previous_data(self):
        """Test that quality_change returns None when no previous period data exists."""
        now = timezone.now()

        # Only current period data
        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr, author=self.member1)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            reviewer=self.member2,
            quality_rating=3,
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertEqual(stats["avg_quality_rating"], 3.0)
        self.assertIsNone(stats["quality_change"])

    def test_recent_activity_returns_last_5_items(self):
        """Test that recent_activity returns last 5 activity items."""
        now = timezone.now()

        # Create 7 merged PRs
        for i in range(7):
            PullRequestFactory(
                team=self.team,
                author=self.member1,
                state="merged",
                merged_at=now - timedelta(hours=i),
                title=f"PR {i}",
            )

        stats = get_team_quick_stats(self.team, days=7)

        # Should only return 5 most recent
        self.assertEqual(len(stats["recent_activity"]), 5)

    def test_recent_activity_includes_pr_merged_type(self):
        """Test that recent_activity includes pr_merged type items."""
        now = timezone.now()

        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(hours=1),
            title="Test PR",
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertEqual(len(stats["recent_activity"]), 1)
        activity = stats["recent_activity"][0]

        self.assertEqual(activity["type"], "pr_merged")
        self.assertEqual(activity["title"], "Test PR")
        self.assertEqual(activity["author"], self.member1.display_name)
        self.assertIsNone(activity["ai_assisted"])  # No survey
        self.assertEqual(activity["timestamp"], pr.merged_at)

    def test_recent_activity_includes_pr_ai_assisted_from_survey(self):
        """Test that recent_activity includes ai_assisted from survey data."""
        now = timezone.now()

        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(hours=1),
            title="Test PR",
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member1,
            author_ai_assisted=True,
        )

        stats = get_team_quick_stats(self.team, days=7)

        activity = stats["recent_activity"][0]
        self.assertEqual(activity["type"], "pr_merged")
        self.assertTrue(activity["ai_assisted"])

    def test_recent_activity_includes_survey_completed_type(self):
        """Test that recent_activity includes survey_completed type items."""
        now = timezone.now()

        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=2),
            title="Test PR",
        )
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member1,
            author_ai_assisted=True,
            author_responded_at=now - timedelta(hours=1),
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Should have 2 items: pr_merged and survey_completed
        self.assertEqual(len(stats["recent_activity"]), 2)

        # Find the survey_completed item
        survey_activity = next(
            (item for item in stats["recent_activity"] if item["type"] == "survey_completed"),
            None,
        )
        self.assertIsNotNone(survey_activity)
        self.assertEqual(survey_activity["title"], f"Survey for PR: {pr.title}")
        self.assertEqual(survey_activity["author"], self.member1.display_name)
        self.assertTrue(survey_activity["ai_assisted"])
        self.assertEqual(survey_activity["timestamp"], survey.author_responded_at)

    def test_recent_activity_mixed_types_sorted_by_timestamp(self):
        """Test that recent_activity includes both types and sorts by timestamp."""
        now = timezone.now()

        # Create PR merged 3 hours ago
        pr1 = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(hours=3),
            title="Older PR",
        )

        # Create survey completed 1 hour ago (more recent)
        pr2 = PullRequestFactory(
            team=self.team,
            author=self.member2,
            state="merged",
            merged_at=now - timedelta(days=2),
            title="Newer PR with Survey",
        )
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author=self.member2,
            author_ai_assisted=False,
            author_responded_at=now - timedelta(hours=1),
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Should have 3 items total
        self.assertEqual(len(stats["recent_activity"]), 3)

        # First item should be the most recent (survey completed)
        self.assertEqual(stats["recent_activity"][0]["type"], "survey_completed")
        self.assertEqual(stats["recent_activity"][0]["timestamp"], survey.author_responded_at)

        # Second item should be the PR merged 3 hours ago
        self.assertEqual(stats["recent_activity"][1]["type"], "pr_merged")
        self.assertEqual(stats["recent_activity"][1]["title"], "Older PR")

    def test_recent_activity_ignores_unanswered_surveys(self):
        """Test that recent_activity ignores surveys where author_ai_assisted is None."""
        now = timezone.now()

        pr = PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(hours=1),
            title="Test PR",
        )
        # Survey with no response
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member1,
            author_ai_assisted=None,
            author_responded_at=None,
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Should only have pr_merged, not survey_completed
        self.assertEqual(len(stats["recent_activity"]), 1)
        self.assertEqual(stats["recent_activity"][0]["type"], "pr_merged")

    def test_different_days_parameter_7_days(self):
        """Test that days=7 parameter filters correctly."""
        now = timezone.now()

        # Create PR within 7 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=5),
        )

        # Create PR outside 7 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=10),
        )

        stats = get_team_quick_stats(self.team, days=7)

        self.assertEqual(stats["prs_merged"], 1)

    def test_different_days_parameter_30_days(self):
        """Test that days=30 parameter filters correctly."""
        now = timezone.now()

        # Create PR within 30 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=25),
        )

        # Create PR outside 30 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=35),
        )

        stats = get_team_quick_stats(self.team, days=30)

        self.assertEqual(stats["prs_merged"], 1)

    def test_different_days_parameter_90_days(self):
        """Test that days=90 parameter filters correctly."""
        now = timezone.now()

        # Create PR within 90 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=85),
        )

        # Create PR outside 90 days
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=95),
        )

        stats = get_team_quick_stats(self.team, days=90)

        self.assertEqual(stats["prs_merged"], 1)

    def test_isolates_data_by_team(self):
        """Test that stats are properly isolated by team."""
        now = timezone.now()

        # Create data for our team
        PullRequestFactory(
            team=self.team,
            author=self.member1,
            state="merged",
            merged_at=now - timedelta(days=1),
        )

        # Create data for another team
        other_team = TeamFactory()
        other_member = TeamMemberFactory(team=other_team)
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=now - timedelta(days=1),
        )
        PullRequestFactory(
            team=other_team,
            author=other_member,
            state="merged",
            merged_at=now - timedelta(days=2),
        )

        stats = get_team_quick_stats(self.team, days=7)

        # Should only count our team's PR
        self.assertEqual(stats["prs_merged"], 1)
