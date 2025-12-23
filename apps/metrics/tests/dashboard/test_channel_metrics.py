"""Tests for Response Channel Distribution metrics in Dashboard Service.

Tests for the get_response_channel_distribution function that aggregates
survey response data by channel (github, slack, web, auto) to show which
channels users are responding from.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import (
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
)
from apps.metrics.services import dashboard_service


class TestGetResponseChannelDistribution(TestCase):
    """Tests for get_response_channel_distribution function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_response_channel_distribution_returns_dict_with_required_keys(self):
        """Test that get_response_channel_distribution returns dict with required keys."""
        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("author_responses", result)
        self.assertIn("reviewer_responses", result)
        self.assertIn("percentages", result)

    def test_get_response_channel_distribution_author_responses_has_all_channels(self):
        """Test that author_responses includes github, slack, web, auto, and total keys."""
        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        author_responses = result["author_responses"]
        self.assertIn("github", author_responses)
        self.assertIn("slack", author_responses)
        self.assertIn("web", author_responses)
        self.assertIn("auto", author_responses)
        self.assertIn("total", author_responses)

    def test_get_response_channel_distribution_reviewer_responses_has_all_channels(self):
        """Test that reviewer_responses includes github, slack, web, and total keys (no auto for reviewers)."""
        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        reviewer_responses = result["reviewer_responses"]
        self.assertIn("github", reviewer_responses)
        self.assertIn("slack", reviewer_responses)
        self.assertIn("web", reviewer_responses)
        self.assertIn("total", reviewer_responses)
        # Auto-detection is only for authors, not reviewers
        self.assertNotIn("auto", reviewer_responses)

    def test_get_response_channel_distribution_counts_author_github_responses(self):
        """Test that get_response_channel_distribution counts author responses from GitHub."""
        # Create 3 PRs with author responses from GitHub
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["author_responses"]["github"], 3)
        self.assertEqual(result["author_responses"]["total"], 3)

    def test_get_response_channel_distribution_counts_author_slack_responses(self):
        """Test that get_response_channel_distribution counts author responses from Slack."""
        # Create 2 PRs with author responses from Slack
        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=False,
                author_response_source="slack",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["author_responses"]["slack"], 2)
        self.assertEqual(result["author_responses"]["total"], 2)

    def test_get_response_channel_distribution_counts_author_web_responses(self):
        """Test that get_response_channel_distribution counts author responses from web."""
        # Create 4 PRs with author responses from web
        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="web",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["author_responses"]["web"], 4)
        self.assertEqual(result["author_responses"]["total"], 4)

    def test_get_response_channel_distribution_counts_author_auto_responses(self):
        """Test that get_response_channel_distribution counts auto-detected author responses."""
        # Create 2 PRs with auto-detected author responses
        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["author_responses"]["auto"], 2)
        self.assertEqual(result["author_responses"]["total"], 2)

    def test_get_response_channel_distribution_counts_mixed_author_responses(self):
        """Test that get_response_channel_distribution correctly counts responses from multiple channels."""
        # Create PRs with different response sources
        channels = ["github", "github", "slack", "slack", "slack", "web", "web", "auto"]

        for i, channel in enumerate(channels):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source=channel,
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["author_responses"]["github"], 2)
        self.assertEqual(result["author_responses"]["slack"], 3)
        self.assertEqual(result["author_responses"]["web"], 2)
        self.assertEqual(result["author_responses"]["auto"], 1)
        self.assertEqual(result["author_responses"]["total"], 8)

    def test_get_response_channel_distribution_counts_reviewer_github_responses(self):
        """Test that get_response_channel_distribution counts reviewer responses from GitHub."""
        # Create PR with survey and reviewer responses from GitHub
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr)

        for i in range(3):
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source="github",
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12 + i, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["reviewer_responses"]["github"], 3)
        self.assertEqual(result["reviewer_responses"]["total"], 3)

    def test_get_response_channel_distribution_counts_reviewer_slack_responses(self):
        """Test that get_response_channel_distribution counts reviewer responses from Slack."""
        # Create PR with survey and reviewer responses from Slack
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr)

        for i in range(2):
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source="slack",
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12 + i, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["reviewer_responses"]["slack"], 2)
        self.assertEqual(result["reviewer_responses"]["total"], 2)

    def test_get_response_channel_distribution_counts_reviewer_web_responses(self):
        """Test that get_response_channel_distribution counts reviewer responses from web."""
        # Create PR with survey and reviewer responses from web
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr)

        for i in range(4):
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source="web",
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12 + i, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["reviewer_responses"]["web"], 4)
        self.assertEqual(result["reviewer_responses"]["total"], 4)

    def test_get_response_channel_distribution_counts_mixed_reviewer_responses(self):
        """Test that get_response_channel_distribution correctly counts reviewer responses from multiple channels."""
        # Create multiple PRs with surveys and different reviewer response sources
        channels_per_pr = [
            ["github", "github"],
            ["slack", "slack", "slack"],
            ["web", "web"],
        ]

        for pr_channels in channels_per_pr:
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr)

            for i, channel in enumerate(pr_channels):
                PRSurveyReviewFactory(
                    team=self.team,
                    survey=survey,
                    response_source=channel,
                    responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12 + i, 0)),
                )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        self.assertEqual(result["reviewer_responses"]["github"], 2)
        self.assertEqual(result["reviewer_responses"]["slack"], 3)
        self.assertEqual(result["reviewer_responses"]["web"], 2)
        self.assertEqual(result["reviewer_responses"]["total"], 7)

    def test_get_response_channel_distribution_calculates_author_percentages(self):
        """Test that get_response_channel_distribution calculates percentages correctly for authors."""
        # Create 10 author responses: 5 github, 3 slack, 2 web
        channels = ["github"] * 5 + ["slack"] * 3 + ["web"] * 2

        for i, channel in enumerate(channels):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source=channel,
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11 + i, 12, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        percentages = result["percentages"]["author"]
        self.assertEqual(percentages["github"], Decimal("50.00"))  # 5/10 = 50%
        self.assertEqual(percentages["slack"], Decimal("30.00"))  # 3/10 = 30%
        self.assertEqual(percentages["web"], Decimal("20.00"))  # 2/10 = 20%
        self.assertEqual(percentages["auto"], Decimal("0.00"))  # 0/10 = 0%

    def test_get_response_channel_distribution_calculates_reviewer_percentages(self):
        """Test that get_response_channel_distribution calculates percentages correctly for reviewers."""
        # Create PR with survey and 10 reviewer responses: 4 github, 4 slack, 2 web
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr)

        channels = ["github"] * 4 + ["slack"] * 4 + ["web"] * 2

        for i, channel in enumerate(channels):
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source=channel,
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12 + i, 0)),
            )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        percentages = result["percentages"]["reviewer"]
        self.assertEqual(percentages["github"], Decimal("40.00"))  # 4/10 = 40%
        self.assertEqual(percentages["slack"], Decimal("40.00"))  # 4/10 = 40%
        self.assertEqual(percentages["web"], Decimal("20.00"))  # 2/10 = 20%

    def test_get_response_channel_distribution_handles_no_responses(self):
        """Test that get_response_channel_distribution handles case with no survey responses."""
        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        # All counts should be 0
        self.assertEqual(result["author_responses"]["github"], 0)
        self.assertEqual(result["author_responses"]["slack"], 0)
        self.assertEqual(result["author_responses"]["web"], 0)
        self.assertEqual(result["author_responses"]["auto"], 0)
        self.assertEqual(result["author_responses"]["total"], 0)

        self.assertEqual(result["reviewer_responses"]["github"], 0)
        self.assertEqual(result["reviewer_responses"]["slack"], 0)
        self.assertEqual(result["reviewer_responses"]["web"], 0)
        self.assertEqual(result["reviewer_responses"]["total"], 0)

        # All percentages should be 0.00
        self.assertEqual(result["percentages"]["author"]["github"], Decimal("0.00"))
        self.assertEqual(result["percentages"]["author"]["slack"], Decimal("0.00"))
        self.assertEqual(result["percentages"]["author"]["web"], Decimal("0.00"))
        self.assertEqual(result["percentages"]["author"]["auto"], Decimal("0.00"))

        self.assertEqual(result["percentages"]["reviewer"]["github"], Decimal("0.00"))
        self.assertEqual(result["percentages"]["reviewer"]["slack"], Decimal("0.00"))
        self.assertEqual(result["percentages"]["reviewer"]["web"], Decimal("0.00"))

    def test_get_response_channel_distribution_ignores_surveys_without_author_response(self):
        """Test that get_response_channel_distribution only counts surveys where author has responded."""
        # Create survey with author_response_source=None (not responded)
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author_ai_assisted=None,  # Not responded
            author_response_source=None,
            author_responded_at=None,
        )

        # Create survey with author response
        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 12, 0)),
        )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        # Should only count the 1 response
        self.assertEqual(result["author_responses"]["total"], 1)
        self.assertEqual(result["author_responses"]["github"], 1)

    def test_get_response_channel_distribution_filters_by_date_range(self):
        """Test that get_response_channel_distribution only includes responses within date range."""
        # In-range PR with author response
        pr_in = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr_in,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        # Before start date (should be excluded)
        pr_before = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr_before,
            author_ai_assisted=True,
            author_response_source="slack",
            author_responded_at=timezone.make_aware(timezone.datetime(2023, 12, 16, 12, 0)),
        )

        # After end date (should be excluded)
        pr_after = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr_after,
            author_ai_assisted=True,
            author_response_source="web",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 2, 16, 12, 0)),
        )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        # Should only count the 1 in-range response
        self.assertEqual(result["author_responses"]["total"], 1)
        self.assertEqual(result["author_responses"]["github"], 1)
        self.assertEqual(result["author_responses"]["slack"], 0)
        self.assertEqual(result["author_responses"]["web"], 0)

    def test_get_response_channel_distribution_filters_reviewer_responses_by_date_range(self):
        """Test that get_response_channel_distribution filters reviewer responses by date range."""
        # In-range PR with reviewer responses
        pr_in = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey_in = PRSurveyFactory(team=self.team, pull_request=pr_in)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey_in,
            response_source="github",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        # Out-of-range PR (should be excluded)
        pr_out = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        survey_out = PRSurveyFactory(team=self.team, pull_request=pr_out)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey_out,
            response_source="slack",
            responded_at=timezone.make_aware(timezone.datetime(2024, 2, 16, 12, 0)),
        )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        # Should only count the 1 in-range review
        self.assertEqual(result["reviewer_responses"]["total"], 1)
        self.assertEqual(result["reviewer_responses"]["github"], 1)
        self.assertEqual(result["reviewer_responses"]["slack"], 0)

    def test_get_response_channel_distribution_filters_by_team(self):
        """Test that get_response_channel_distribution only includes data from the specified team."""
        other_team = TeamFactory()

        # Target team data
        pr_target = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr_target,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        # Other team data (should be excluded)
        pr_other = PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=other_team,
            pull_request=pr_other,
            author_ai_assisted=True,
            author_response_source="slack",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        # Should only count target team data
        self.assertEqual(result["author_responses"]["total"], 1)
        self.assertEqual(result["author_responses"]["github"], 1)
        self.assertEqual(result["author_responses"]["slack"], 0)

    def test_get_response_channel_distribution_combined_author_and_reviewer_responses(self):
        """Test that get_response_channel_distribution handles both author and reviewer responses together."""
        # Create PR with both author and reviewer responses
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author_ai_assisted=True,
            author_response_source="slack",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16, 12, 0)),
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            response_source="github",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 12, 0)),
        )
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            response_source="web",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 17, 14, 0)),
        )

        result = dashboard_service.get_response_channel_distribution(self.team, self.start_date, self.end_date)

        # Check author responses
        self.assertEqual(result["author_responses"]["slack"], 1)
        self.assertEqual(result["author_responses"]["total"], 1)

        # Check reviewer responses
        self.assertEqual(result["reviewer_responses"]["github"], 1)
        self.assertEqual(result["reviewer_responses"]["web"], 1)
        self.assertEqual(result["reviewer_responses"]["total"], 2)


class TestGetAIDetectionMetrics(TestCase):
    """Tests for get_ai_detection_metrics function - AI auto-detection analytics."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_ai_detection_metrics_returns_dict_with_required_keys(self):
        """Test that get_ai_detection_metrics returns dict with all required keys."""
        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("auto_detected_count", result)
        self.assertIn("self_reported_count", result)
        self.assertIn("not_ai_count", result)
        self.assertIn("no_response_count", result)
        self.assertIn("total_surveys", result)
        self.assertIn("auto_detection_rate", result)
        self.assertIn("ai_usage_rate", result)

    def test_get_ai_detection_metrics_counts_auto_detected_prs(self):
        """Test that get_ai_detection_metrics counts PRs with auto-detected AI usage."""
        # Create 3 PRs with auto-detected AI usage
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["auto_detected_count"], 3)

    def test_get_ai_detection_metrics_counts_self_reported_github(self):
        """Test that get_ai_detection_metrics counts PRs where author self-reported AI via GitHub."""
        # Create 2 PRs with self-reported AI usage via GitHub
        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["self_reported_count"], 2)

    def test_get_ai_detection_metrics_counts_self_reported_slack(self):
        """Test that get_ai_detection_metrics counts PRs where author self-reported AI via Slack."""
        # Create 3 PRs with self-reported AI usage via Slack
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="slack",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["self_reported_count"], 3)

    def test_get_ai_detection_metrics_counts_self_reported_web(self):
        """Test that get_ai_detection_metrics counts PRs where author self-reported AI via web."""
        # Create 1 PR with self-reported AI usage via web
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author_ai_assisted=True,
            author_response_source="web",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 13, 0)),
        )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["self_reported_count"], 1)

    def test_get_ai_detection_metrics_counts_not_ai_responses(self):
        """Test that get_ai_detection_metrics counts PRs where author said no AI was used."""
        # Create 4 PRs where author responded no AI
        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=False,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["not_ai_count"], 4)

    def test_get_ai_detection_metrics_counts_no_response(self):
        """Test that get_ai_detection_metrics counts surveys without author response."""
        # Create 5 PRs with surveys but no author response
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=None,
                author_response_source=None,
                author_responded_at=None,
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["no_response_count"], 5)

    def test_get_ai_detection_metrics_counts_total_surveys(self):
        """Test that get_ai_detection_metrics counts total surveys in range."""
        # Create mixed surveys: 2 auto, 3 self-reported, 1 no-AI, 2 no-response
        channels = ["auto", "auto", "github", "slack", "web", "github", "github"]
        ai_values = [True, True, True, True, True, False, None]

        for i, (channel, ai_value) in enumerate(zip(channels, ai_values, strict=False)):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=ai_value,
                author_response_source=channel if ai_value is not None else None,
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0))
                if ai_value is not None
                else None,
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_surveys"], 7)

    def test_get_ai_detection_metrics_calculates_auto_detection_rate(self):
        """Test that get_ai_detection_metrics calculates auto-detection rate correctly."""
        # Create 3 auto-detected and 7 self-reported (total 10 AI PRs)
        # Auto-detection rate should be 30%
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        for i in range(7):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        # 3 auto-detected out of 10 total AI PRs = 30%
        self.assertEqual(result["auto_detection_rate"], Decimal("30.00"))

    def test_get_ai_detection_metrics_calculates_ai_usage_rate(self):
        """Test that get_ai_detection_metrics calculates AI usage rate correctly."""
        # Create 6 AI PRs (2 auto, 4 self-reported) and 4 non-AI PRs
        # AI usage rate should be 60%
        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 12 + i, 13, 0)),
            )

        for i in range(4):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 16 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=False,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 16 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        # 6 AI PRs out of 10 total surveys = 60%
        self.assertEqual(result["ai_usage_rate"], Decimal("60.00"))

    def test_get_ai_detection_metrics_filters_by_date_range(self):
        """Test that get_ai_detection_metrics filters surveys by date range based on survey creation."""
        # In-range survey
        pr_in = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey_in = PRSurveyFactory(
            team=self.team,
            pull_request=pr_in,
            author_ai_assisted=True,
            author_response_source="auto",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 13, 0)),
        )
        # Manually set created_at to be in range
        survey_in.created_at = timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0))
        survey_in.save()

        # Before start date (should be excluded)
        pr_before = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 12, 0)),
        )
        survey_before = PRSurveyFactory(
            team=self.team,
            pull_request=pr_before,
            author_ai_assisted=True,
            author_response_source="auto",
            author_responded_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 13, 0)),
        )
        survey_before.created_at = timezone.make_aware(timezone.datetime(2023, 12, 15, 12, 0))
        survey_before.save()

        # After end date (should be excluded)
        pr_after = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        survey_after = PRSurveyFactory(
            team=self.team,
            pull_request=pr_after,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 13, 0)),
        )
        survey_after.created_at = timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0))
        survey_after.save()

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        # Should only count the 1 in-range survey
        self.assertEqual(result["total_surveys"], 1)
        self.assertEqual(result["auto_detected_count"], 1)

    def test_get_ai_detection_metrics_filters_by_team(self):
        """Test that get_ai_detection_metrics only includes data from specified team."""
        other_team = TeamFactory()

        # Target team data
        pr_target = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr_target,
            author_ai_assisted=True,
            author_response_source="auto",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 13, 0)),
        )

        # Other team data (should be excluded)
        pr_other = PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=other_team,
            pull_request=pr_other,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 13, 0)),
        )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        # Should only count target team data
        self.assertEqual(result["total_surveys"], 1)
        self.assertEqual(result["auto_detected_count"], 1)
        self.assertEqual(result["self_reported_count"], 0)

    def test_get_ai_detection_metrics_handles_no_surveys(self):
        """Test that get_ai_detection_metrics handles case with no surveys."""
        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["auto_detected_count"], 0)
        self.assertEqual(result["self_reported_count"], 0)
        self.assertEqual(result["not_ai_count"], 0)
        self.assertEqual(result["no_response_count"], 0)
        self.assertEqual(result["total_surveys"], 0)
        self.assertEqual(result["auto_detection_rate"], Decimal("0.00"))
        self.assertEqual(result["ai_usage_rate"], Decimal("0.00"))

    def test_get_ai_detection_metrics_handles_all_auto_detected(self):
        """Test that get_ai_detection_metrics handles case where all AI PRs are auto-detected."""
        # Create 5 auto-detected PRs only
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["auto_detected_count"], 5)
        self.assertEqual(result["self_reported_count"], 0)
        self.assertEqual(result["auto_detection_rate"], Decimal("100.00"))
        self.assertEqual(result["ai_usage_rate"], Decimal("100.00"))

    def test_get_ai_detection_metrics_handles_all_self_reported(self):
        """Test that get_ai_detection_metrics handles case where all AI PRs are self-reported."""
        # Create 4 self-reported PRs only
        channels = ["github", "slack", "web", "github"]
        for i, channel in enumerate(channels):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source=channel,
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["auto_detected_count"], 0)
        self.assertEqual(result["self_reported_count"], 4)
        self.assertEqual(result["auto_detection_rate"], Decimal("0.00"))
        self.assertEqual(result["ai_usage_rate"], Decimal("100.00"))

    def test_get_ai_detection_metrics_handles_no_ai_usage(self):
        """Test that get_ai_detection_metrics handles case where no AI was used."""
        # Create 3 PRs where author responded no AI
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=False,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["auto_detected_count"], 0)
        self.assertEqual(result["self_reported_count"], 0)
        self.assertEqual(result["not_ai_count"], 3)
        self.assertEqual(result["auto_detection_rate"], Decimal("0.00"))
        self.assertEqual(result["ai_usage_rate"], Decimal("0.00"))

    def test_get_ai_detection_metrics_comprehensive_mixed_data(self):
        """Test get_ai_detection_metrics with comprehensive mixed data scenario."""
        # Create a realistic mix:
        # - 5 auto-detected
        # - 8 self-reported (3 github, 3 slack, 2 web)
        # - 7 not-AI
        # - 3 no-response
        # Total: 23 surveys
        # AI PRs: 13 (5 auto + 8 self-reported)
        # Auto-detection rate: 5/13 = 38.46%
        # AI usage rate: 13/23 = 56.52%

        # Auto-detected
        for i in range(5):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 5 + i, 13, 0)),
            )

        # Self-reported
        channels = ["github", "github", "github", "slack", "slack", "slack", "web", "web"]
        for i, channel in enumerate(channels):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source=channel,
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 13, 0)),
            )

        # Not AI
        for i in range(7):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 18 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=False,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 18 + i, 13, 0)),
            )

        # No response
        for i in range(3):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 25 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=None,
                author_response_source=None,
                author_responded_at=None,
            )

        result = dashboard_service.get_ai_detection_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["auto_detected_count"], 5)
        self.assertEqual(result["self_reported_count"], 8)
        self.assertEqual(result["not_ai_count"], 7)
        self.assertEqual(result["no_response_count"], 3)
        self.assertEqual(result["total_surveys"], 23)
        self.assertEqual(result["auto_detection_rate"], Decimal("38.46"))
        self.assertEqual(result["ai_usage_rate"], Decimal("56.52"))


class TestGetResponseTimeMetrics(TestCase):
    """Tests for get_response_time_metrics function - survey response time analytics."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.start_date = date(2024, 1, 1)
        self.end_date = date(2024, 1, 31)

    def test_get_response_time_metrics_returns_dict_with_required_keys(self):
        """Test that get_response_time_metrics returns dict with all required keys."""
        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertIsInstance(result, dict)
        self.assertIn("author_avg_response_time", result)
        self.assertIn("reviewer_avg_response_time", result)
        self.assertIn("by_channel", result)
        self.assertIn("total_author_responses", result)
        self.assertIn("total_reviewer_responses", result)

    def test_get_response_time_metrics_by_channel_has_author_and_reviewer_keys(self):
        """Test that by_channel dict has author and reviewer channel breakdowns."""
        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertIn("author", result["by_channel"])
        self.assertIn("reviewer", result["by_channel"])

    def test_get_response_time_metrics_by_channel_author_has_all_channels(self):
        """Test that author channel breakdown includes github, slack, and web."""
        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        author_channels = result["by_channel"]["author"]
        self.assertIn("github", author_channels)
        self.assertIn("slack", author_channels)
        self.assertIn("web", author_channels)

    def test_get_response_time_metrics_by_channel_reviewer_has_all_channels(self):
        """Test that reviewer channel breakdown includes github, slack, and web."""
        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        reviewer_channels = result["by_channel"]["reviewer"]
        self.assertIn("github", reviewer_channels)
        self.assertIn("slack", reviewer_channels)
        self.assertIn("web", reviewer_channels)

    def test_get_response_time_metrics_calculates_author_avg_response_time(self):
        """Test that get_response_time_metrics calculates average author response time correctly."""
        # Create 3 PRs with author responses at different times
        # PR 1: merged at 12:00, author responded at 14:00 (2 hours)
        pr1 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr1,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 14, 0)),
        )

        # PR 2: merged at 10:00, author responded at 16:00 (6 hours)
        pr2 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 10, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr2,
            author_ai_assisted=False,
            author_response_source="slack",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 16, 0)),
        )

        # PR 3: merged at 14:00, author responded at 18:00 (4 hours)
        pr3 = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 14, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr3,
            author_ai_assisted=True,
            author_response_source="web",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 18, 0)),
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Average: (2 + 6 + 4) / 3 = 4.0 hours
        self.assertEqual(result["author_avg_response_time"], Decimal("4.00"))
        self.assertEqual(result["total_author_responses"], 3)

    def test_get_response_time_metrics_calculates_reviewer_avg_response_time(self):
        """Test that get_response_time_metrics calculates average reviewer response time correctly."""
        # Create PR with survey and 3 reviewer responses at different times
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr)

        # Reviewer 1: responded 1 hour after merge
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            response_source="github",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 13, 0)),
        )

        # Reviewer 2: responded 5 hours after merge
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            response_source="slack",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 17, 0)),
        )

        # Reviewer 3: responded 3 hours after merge
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            response_source="web",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 15, 0)),
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Average: (1 + 5 + 3) / 3 = 3.0 hours
        self.assertEqual(result["reviewer_avg_response_time"], Decimal("3.00"))
        self.assertEqual(result["total_reviewer_responses"], 3)

    def test_get_response_time_metrics_calculates_author_response_time_by_channel(self):
        """Test that get_response_time_metrics calculates average response time per author channel."""
        # GitHub: 2 hours and 4 hours (avg: 3.0)
        for hours in [2, 4]:
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="github",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12 + hours, 0)),
            )

        # Slack: 6 hours and 8 hours (avg: 7.0)
        for hours in [6, 8]:
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 10, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=False,
                author_response_source="slack",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 11, 10 + hours, 0)),
            )

        # Web: 3 hours and 5 hours (avg: 4.0)
        for hours in [3, 5]:
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 14, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="web",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 12, 14 + hours, 0)),
            )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["by_channel"]["author"]["github"], Decimal("3.00"))
        self.assertEqual(result["by_channel"]["author"]["slack"], Decimal("7.00"))
        self.assertEqual(result["by_channel"]["author"]["web"], Decimal("4.00"))

    def test_get_response_time_metrics_calculates_reviewer_response_time_by_channel(self):
        """Test that get_response_time_metrics calculates average response time per reviewer channel."""
        # Create 3 PRs with reviewer responses on different channels
        # GitHub channel: 1 hour and 3 hours (avg: 2.0)
        for i, hours in enumerate([1, 3]):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr)
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source="github",
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12 + hours, 0)),
            )

        # Slack channel: 4 hours and 6 hours (avg: 5.0)
        for i, hours in enumerate([4, 6]):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 10, 0)),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr)
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source="slack",
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15 + i, 10 + hours, 0)),
            )

        # Web channel: 2 hours and 4 hours (avg: 3.0)
        for i, hours in enumerate([2, 4]):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 20 + i, 14, 0)),
            )
            survey = PRSurveyFactory(team=self.team, pull_request=pr)
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source="web",
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 20 + i, 14 + hours, 0)),
            )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["by_channel"]["reviewer"]["github"], Decimal("2.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["slack"], Decimal("5.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["web"], Decimal("3.00"))

    def test_get_response_time_metrics_excludes_auto_detected_author_responses(self):
        """Test that get_response_time_metrics excludes auto-detected responses (no real response time)."""
        # Create 2 auto-detected responses (should be excluded)
        for i in range(2):
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source="auto",
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10 + i, 14, 0)),
            )

        # Create 1 real response (should be counted)
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 16, 0)),  # 4 hours
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Should only count the 1 real response
        self.assertEqual(result["total_author_responses"], 1)
        self.assertEqual(result["author_avg_response_time"], Decimal("4.00"))

    def test_get_response_time_metrics_filters_by_date_range(self):
        """Test that get_response_time_metrics filters surveys by date range based on survey creation."""
        # In-range survey (created Jan 15)
        pr_in = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey_in = PRSurveyFactory(
            team=self.team,
            pull_request=pr_in,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 0)),  # 2 hours
        )
        survey_in.created_at = timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0))
        survey_in.save()

        # Before start date (should be excluded)
        pr_before = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 12, 0)),
        )
        survey_before = PRSurveyFactory(
            team=self.team,
            pull_request=pr_before,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2023, 12, 15, 18, 0)),
        )
        survey_before.created_at = timezone.make_aware(timezone.datetime(2023, 12, 15, 12, 0))
        survey_before.save()

        # After end date (should be excluded)
        pr_after = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        survey_after = PRSurveyFactory(
            team=self.team,
            pull_request=pr_after,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 18, 0)),
        )
        survey_after.created_at = timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0))
        survey_after.save()

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Should only count the 1 in-range survey
        self.assertEqual(result["total_author_responses"], 1)
        self.assertEqual(result["author_avg_response_time"], Decimal("2.00"))

    def test_get_response_time_metrics_filters_reviewer_responses_by_date_range(self):
        """Test that get_response_time_metrics filters reviewer responses by date range."""
        # In-range reviewer response
        pr_in = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        survey_in = PRSurveyFactory(team=self.team, pull_request=pr_in)
        survey_in.created_at = timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0))
        survey_in.save()
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey_in,
            response_source="github",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 15, 0)),  # 3 hours
        )

        # Out-of-range reviewer response (should be excluded)
        pr_out = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0)),
        )
        survey_out = PRSurveyFactory(team=self.team, pull_request=pr_out)
        survey_out.created_at = timezone.make_aware(timezone.datetime(2024, 2, 15, 12, 0))
        survey_out.save()
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey_out,
            response_source="slack",
            responded_at=timezone.make_aware(timezone.datetime(2024, 2, 15, 18, 0)),
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Should only count the 1 in-range review
        self.assertEqual(result["total_reviewer_responses"], 1)
        self.assertEqual(result["reviewer_avg_response_time"], Decimal("3.00"))

    def test_get_response_time_metrics_filters_by_team(self):
        """Test that get_response_time_metrics only includes data from specified team."""
        other_team = TeamFactory()

        # Target team data
        pr_target = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr_target,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 14, 0)),  # 2 hours
        )

        # Other team data (should be excluded)
        pr_other = PullRequestFactory(
            team=other_team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 12, 0)),
        )
        PRSurveyFactory(
            team=other_team,
            pull_request=pr_other,
            author_ai_assisted=True,
            author_response_source="github",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 20, 0)),
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Should only count target team data
        self.assertEqual(result["total_author_responses"], 1)
        self.assertEqual(result["author_avg_response_time"], Decimal("2.00"))

    def test_get_response_time_metrics_handles_no_responses(self):
        """Test that get_response_time_metrics handles case with no survey responses."""
        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # All counts should be 0
        self.assertEqual(result["total_author_responses"], 0)
        self.assertEqual(result["total_reviewer_responses"], 0)

        # Average times should be 0.00 when no responses
        self.assertEqual(result["author_avg_response_time"], Decimal("0.00"))
        self.assertEqual(result["reviewer_avg_response_time"], Decimal("0.00"))

        # Channel breakdowns should be 0.00
        self.assertEqual(result["by_channel"]["author"]["github"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["author"]["slack"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["author"]["web"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["github"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["slack"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["web"], Decimal("0.00"))

    def test_get_response_time_metrics_handles_single_author_response(self):
        """Test that get_response_time_metrics handles single author response correctly."""
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author_ai_assisted=True,
            author_response_source="slack",
            author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 17, 30)),  # 5.5 hours
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_author_responses"], 1)
        self.assertEqual(result["author_avg_response_time"], Decimal("5.50"))
        self.assertEqual(result["by_channel"]["author"]["slack"], Decimal("5.50"))
        self.assertEqual(result["by_channel"]["author"]["github"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["author"]["web"], Decimal("0.00"))

    def test_get_response_time_metrics_handles_single_reviewer_response(self):
        """Test that get_response_time_metrics handles single reviewer response correctly."""
        pr = PullRequestFactory(
            team=self.team,
            state="merged",
            merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
        )
        survey = PRSurveyFactory(team=self.team, pull_request=pr)
        PRSurveyReviewFactory(
            team=self.team,
            survey=survey,
            response_source="web",
            responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 18, 45)),  # 6.75 hours
        )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        self.assertEqual(result["total_reviewer_responses"], 1)
        self.assertEqual(result["reviewer_avg_response_time"], Decimal("6.75"))
        self.assertEqual(result["by_channel"]["reviewer"]["web"], Decimal("6.75"))
        self.assertEqual(result["by_channel"]["reviewer"]["github"], Decimal("0.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["slack"], Decimal("0.00"))

    def test_get_response_time_metrics_handles_mixed_channel_data(self):
        """Test that get_response_time_metrics correctly handles responses from multiple channels."""
        # Author responses: 2 github, 1 slack, 3 web
        author_data = [
            ("github", 2),
            ("github", 4),
            ("slack", 6),
            ("web", 3),
            ("web", 5),
            ("web", 7),
        ]

        for channel, hours in author_data:
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12, 0)),
            )
            PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_ai_assisted=True,
                author_response_source=channel,
                author_responded_at=timezone.make_aware(timezone.datetime(2024, 1, 10, 12 + hours, 0)),
            )

        # Reviewer responses: 3 github, 2 slack, 1 web
        reviewer_data = [
            ("github", 1),
            ("github", 2),
            ("github", 3),
            ("slack", 4),
            ("slack", 6),
            ("web", 5),
        ]

        for channel, hours in reviewer_data:
            pr = PullRequestFactory(
                team=self.team,
                state="merged",
                merged_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10, 0)),
            )
            survey = PRSurveyFactory(
                team=self.team,
                pull_request=pr,
                author_responded_at=None,
                author_response_source=None,
            )
            PRSurveyReviewFactory(
                team=self.team,
                survey=survey,
                response_source=channel,
                responded_at=timezone.make_aware(timezone.datetime(2024, 1, 15, 10 + hours, 0)),
            )

        result = dashboard_service.get_response_time_metrics(self.team, self.start_date, self.end_date)

        # Author: overall avg = (2+4+6+3+5+7)/6 = 27/6 = 4.50
        self.assertEqual(result["author_avg_response_time"], Decimal("4.50"))
        self.assertEqual(result["total_author_responses"], 6)
        # Author by channel: github=(2+4)/2=3.0, slack=6.0, web=(3+5+7)/3=5.0
        self.assertEqual(result["by_channel"]["author"]["github"], Decimal("3.00"))
        self.assertEqual(result["by_channel"]["author"]["slack"], Decimal("6.00"))
        self.assertEqual(result["by_channel"]["author"]["web"], Decimal("5.00"))

        # Reviewer: overall avg = (1+2+3+4+6+5)/6 = 21/6 = 3.50
        self.assertEqual(result["reviewer_avg_response_time"], Decimal("3.50"))
        self.assertEqual(result["total_reviewer_responses"], 6)
        # Reviewer by channel: github=(1+2+3)/3=2.0, slack=(4+6)/2=5.0, web=5.0
        self.assertEqual(result["by_channel"]["reviewer"]["github"], Decimal("2.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["slack"], Decimal("5.00"))
        self.assertEqual(result["by_channel"]["reviewer"]["web"], Decimal("5.00"))
