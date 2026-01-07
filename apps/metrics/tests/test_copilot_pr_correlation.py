"""
Tests for PR correlation with Copilot usage.

This module tests the correlation between daily Copilot usage (AIUsageDaily)
and PullRequests created on those days, marking PRs as AI-assisted when
the author had Copilot activity on the PR creation date.
"""

from datetime import date, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.integrations.services.copilot_pr_correlation import correlate_prs_with_copilot_usage
from apps.metrics.factories import (
    AIUsageDailyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestCopilotPRCorrelation(TestCase):
    """Tests for correlating PRs with Copilot usage."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(slug="test-team")
        self.member = TeamMemberFactory(team=self.team)
        self.today = date.today()

    def test_prs_on_usage_days_marked_ai_assisted(self):
        """Test that PRs created on days with Copilot usage are marked as AI-assisted."""
        # Arrange - Create Copilot usage for today
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create PR on same day
        pr_datetime = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,  # Not yet determined
            ai_tools_detected=[],
        )

        # Act
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert
        pr.refresh_from_db()
        self.assertTrue(pr.is_ai_assisted)

    def test_prs_on_non_usage_days_not_marked(self):
        """Test that PRs created on days without Copilot usage are not marked."""
        # Arrange - Create Copilot usage for yesterday (not today)
        yesterday = self.today - timedelta(days=1)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=yesterday,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        # Create PR today (no usage on this day)
        pr_datetime = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
            ai_tools_detected=[],
        )

        # Act
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert - PR should not be marked as AI assisted
        pr.refresh_from_db()
        self.assertIsNone(pr.is_ai_assisted)

    def test_ai_tools_detected_includes_copilot(self):
        """Test that ai_tools_detected includes 'copilot' when correlated."""
        # Arrange
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        pr_datetime = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
            ai_tools_detected=[],
        )

        # Act
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert
        pr.refresh_from_db()
        self.assertIn("copilot", pr.ai_tools_detected)

    def test_existing_ai_tools_preserved(self):
        """Test that existing ai_tools_detected entries are preserved when adding copilot."""
        # Arrange
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        pr_datetime = timezone.now().replace(hour=14, minute=0, second=0, microsecond=0)
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=True,
            ai_tools_detected=["cursor"],  # Already has cursor
        )

        # Act
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert - Both tools should be present
        pr.refresh_from_db()
        self.assertIn("cursor", pr.ai_tools_detected)
        self.assertIn("copilot", pr.ai_tools_detected)

    def test_correlation_respects_team_isolation(self):
        """Test that correlation only affects PRs in the specified team."""
        # Arrange - Create another team
        other_team = TeamFactory(slug="other-team")
        other_member = TeamMemberFactory(team=other_team)

        # Create Copilot usage for both teams
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
        )
        AIUsageDailyFactory(
            team=other_team,
            member=other_member,
            date=self.today,
            source="copilot",
        )

        # Create PRs for both teams
        pr_datetime = timezone.now()
        pr_team1 = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
        )
        pr_team2 = PullRequestFactory(
            team=other_team,
            author=other_member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
        )

        # Act - Only correlate for self.team
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert
        pr_team1.refresh_from_db()
        pr_team2.refresh_from_db()
        self.assertTrue(pr_team1.is_ai_assisted)  # Should be marked
        self.assertIsNone(pr_team2.is_ai_assisted)  # Should NOT be marked

    def test_correlation_only_for_copilot_source(self):
        """Test that only Copilot usage (not Cursor) triggers correlation."""
        # Arrange - Create Cursor usage (not Copilot)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="cursor",  # Not copilot
            suggestions_shown=100,
            suggestions_accepted=40,
        )

        pr_datetime = timezone.now()
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
            ai_tools_detected=[],
        )

        # Act
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert - Should NOT be marked (no Copilot usage)
        pr.refresh_from_db()
        self.assertIsNone(pr.is_ai_assisted)
        self.assertNotIn("copilot", pr.ai_tools_detected)

    def test_correlation_requires_minimum_suggestions(self):
        """Test that correlation requires minimum suggestions to count as active usage."""
        # Arrange - Create usage with 0 suggestions (inactive day)
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=0,  # No activity
            suggestions_accepted=0,
        )

        pr_datetime = timezone.now()
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
        )

        # Act
        correlate_prs_with_copilot_usage(team=self.team)

        # Assert - Should NOT be marked (no actual activity)
        pr.refresh_from_db()
        self.assertIsNone(pr.is_ai_assisted)

    def test_correlation_returns_count(self):
        """Test that correlation function returns count of updated PRs."""
        # Arrange
        AIUsageDailyFactory(
            team=self.team,
            member=self.member,
            date=self.today,
            source="copilot",
            suggestions_shown=100,
        )

        pr_datetime = timezone.now()
        PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
        )
        PullRequestFactory(
            team=self.team,
            author=self.member,
            pr_created_at=pr_datetime,
            is_ai_assisted=None,
        )

        # Act
        updated_count = correlate_prs_with_copilot_usage(team=self.team)

        # Assert
        self.assertEqual(updated_count, 2)
