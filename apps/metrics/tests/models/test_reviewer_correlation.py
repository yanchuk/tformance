from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase


class TestReviewerCorrelationModel(TestCase):
    """Tests for ReviewerCorrelation model."""

    def setUp(self):
        """Set up test fixtures."""
        from apps.metrics.factories import TeamFactory, TeamMemberFactory

        self.team = TeamFactory()
        self.reviewer1 = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer2 = TeamMemberFactory(team=self.team, display_name="Bob")

    def test_reviewer_correlation_creation(self):
        """Test that ReviewerCorrelation can be created with required fields."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        self.assertEqual(correlation.reviewer_1, self.reviewer1)
        self.assertEqual(correlation.reviewer_2, self.reviewer2)
        self.assertEqual(correlation.prs_reviewed_together, 10)
        self.assertEqual(correlation.agreements, 8)
        self.assertEqual(correlation.disagreements, 2)

    def test_reviewer_correlation_team_relationship(self):
        """Test that ReviewerCorrelation has proper team relationship."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=5,
            agreements=4,
            disagreements=1,
        )

        self.assertEqual(correlation.team, self.team)
        self.assertIn(correlation, self.team.reviewercorrelation_set.all())

    def test_reviewer_correlation_unique_constraint(self):
        """Test that reviewer pairs are unique per team."""
        from apps.metrics.models import ReviewerCorrelation

        ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=5,
            agreements=4,
            disagreements=1,
        )

        # Creating duplicate should raise IntegrityError
        with self.assertRaises(IntegrityError):
            ReviewerCorrelation.objects.create(
                team=self.team,
                reviewer_1=self.reviewer1,
                reviewer_2=self.reviewer2,
                prs_reviewed_together=10,
                agreements=8,
                disagreements=2,
            )

    def test_reviewer_correlation_agreement_rate_property(self):
        """Test that agreement_rate is calculated correctly."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        # 8 agreements out of 10 = 80%
        self.assertEqual(correlation.agreement_rate, Decimal("80.00"))

    def test_reviewer_correlation_agreement_rate_zero_reviews(self):
        """Test that agreement_rate handles zero reviews gracefully."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=0,
            agreements=0,
            disagreements=0,
        )

        self.assertEqual(correlation.agreement_rate, Decimal("0.00"))

    def test_reviewer_correlation_str_representation(self):
        """Test the string representation of ReviewerCorrelation."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=10,
            agreements=8,
            disagreements=2,
        )

        expected = f"{self.reviewer1.display_name} ↔ {self.reviewer2.display_name}: 80.00% agreement"
        self.assertEqual(str(correlation), expected)

    def test_reviewer_correlation_is_redundant_high_agreement(self):
        """Test that is_redundant returns True for high agreement rate."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=20,  # Sufficient sample size
            agreements=19,
            disagreements=1,
        )

        # 95% agreement with 20+ reviews = redundant
        self.assertTrue(correlation.is_redundant)

    def test_reviewer_correlation_is_redundant_low_sample_size(self):
        """Test that is_redundant returns False for low sample size even with high agreement."""
        from apps.metrics.models import ReviewerCorrelation

        correlation = ReviewerCorrelation.objects.create(
            team=self.team,
            reviewer_1=self.reviewer1,
            reviewer_2=self.reviewer2,
            prs_reviewed_together=5,  # Low sample size
            agreements=5,
            disagreements=0,
        )

        # 100% agreement but only 5 reviews = not enough data
        self.assertFalse(correlation.is_redundant)
