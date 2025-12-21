"""Tests for Dashboard Service - data aggregation for dashboard views.

Business logic for aggregating metrics data from PRs, surveys, and reviews
into dashboard-friendly formats.
"""

from decimal import Decimal

from django.test import TestCase

from apps.metrics.factories import (
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services import dashboard_service


class TestGetReviewerCorrelations(TestCase):
    """Tests for get_reviewer_correlations function."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.metrics.factories import ReviewerCorrelationFactory

        self.team = TeamFactory()
        self.reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob")
        self.ReviewerCorrelationFactory = ReviewerCorrelationFactory

    def test_get_reviewer_correlations_returns_list_of_dicts(self):
        """Test that get_reviewer_correlations returns a list of dicts."""
        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertIsInstance(result, list)

    def test_get_reviewer_correlations_includes_required_keys(self):
        """Test that each correlation has required keys."""
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertEqual(len(result), 1)
        corr = result[0]
        self.assertIn("reviewer_1_name", corr)
        self.assertIn("reviewer_2_name", corr)
        self.assertIn("prs_reviewed_together", corr)
        self.assertIn("agreement_rate", corr)
        self.assertIn("is_redundant", corr)

    def test_get_reviewer_correlations_returns_correct_data(self):
        """Test that get_reviewer_correlations returns correct data."""
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        corr = result[0]
        self.assertEqual(corr["reviewer_1_name"], "Alice")
        self.assertEqual(corr["reviewer_2_name"], "Bob")
        self.assertEqual(corr["prs_reviewed_together"], 10)
        self.assertEqual(corr["agreement_rate"], Decimal("80.00"))
        self.assertFalse(corr["is_redundant"])  # 80% < 95% threshold

    def test_get_reviewer_correlations_detects_redundant_pair(self):
        """Test that get_reviewer_correlations detects redundant reviewer pairs."""
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=15,  # >= 10 sample size
            agreements=15,  # 100% agreement > 95% threshold
            disagreements=0,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        corr = result[0]
        self.assertTrue(corr["is_redundant"])

    def test_get_reviewer_correlations_filters_by_team(self):
        """Test that get_reviewer_correlations only includes data from the specified team."""
        other_team = TeamFactory()
        other_r1 = TeamMemberFactory(team=other_team)
        other_r2 = TeamMemberFactory(team=other_team)

        # Create correlation for target team
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
        )

        # Create correlation for other team
        self.ReviewerCorrelationFactory(
            team=other_team,
            reviewer_1=other_r1,
            reviewer_2=other_r2,
            prs_reviewed_together=20,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["prs_reviewed_together"], 10)

    def test_get_reviewer_correlations_orders_by_prs_reviewed_desc(self):
        """Test that get_reviewer_correlations orders by PRs reviewed descending."""
        reviewer3 = TeamMemberFactory(team=self.team, display_name="Charlie")

        # Create correlations with different PR counts
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=5,
        )
        self.ReviewerCorrelationFactory(
            team=self.team,
            reviewer_1=self.reviewer2,
            reviewer_2=reviewer3,
            prs_reviewed_together=15,
        )

        result = dashboard_service.get_reviewer_correlations(self.team)

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["prs_reviewed_together"], 15)  # Higher count first
        self.assertEqual(result[1]["prs_reviewed_together"], 5)
