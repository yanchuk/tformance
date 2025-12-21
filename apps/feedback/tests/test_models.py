"""
Tests for the AI Feedback models.
"""

from django.test import TestCase
from django.utils import timezone

from apps.feedback.factories import AIFeedbackFactory
from apps.feedback.models import CATEGORY_CHOICES, STATUS_CHOICES, AIFeedback
from apps.metrics.factories import PullRequestFactory, TeamFactory, TeamMemberFactory


class TestAIFeedbackModel(TestCase):
    """Tests for the AIFeedback model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.pr = PullRequestFactory(team=self.team, author=self.member)

    def test_create_feedback_with_required_fields(self):
        """Test creating feedback with only required fields."""
        feedback = AIFeedback.objects.create(
            team=self.team,
            category="wrong_code",
            reported_by=self.member,
        )
        self.assertIsNotNone(feedback.id)
        self.assertEqual(feedback.category, "wrong_code")
        self.assertEqual(feedback.reported_by, self.member)
        self.assertEqual(feedback.status, "open")

    def test_create_feedback_with_all_fields(self):
        """Test creating feedback with all fields populated."""
        feedback = AIFeedback.objects.create(
            team=self.team,
            category="missed_context",
            description="AI didn't understand our custom ORM patterns",
            pull_request=self.pr,
            file_path="apps/models/custom.py",
            language="python",
            reported_by=self.member,
        )
        self.assertEqual(feedback.description, "AI didn't understand our custom ORM patterns")
        self.assertEqual(feedback.pull_request, self.pr)
        self.assertEqual(feedback.file_path, "apps/models/custom.py")
        self.assertEqual(feedback.language, "python")

    def test_feedback_category_choices(self):
        """Test that all expected category choices exist."""
        expected_categories = [
            "wrong_code",
            "missed_context",
            "style_issue",
            "missing_tests",
            "security",
            "performance",
            "other",
        ]
        actual_categories = [choice[0] for choice in CATEGORY_CHOICES]
        for category in expected_categories:
            self.assertIn(category, actual_categories)

    def test_feedback_status_choices(self):
        """Test that all expected status choices exist."""
        expected_statuses = ["open", "acknowledged", "resolved"]
        actual_statuses = [choice[0] for choice in STATUS_CHOICES]
        for status in expected_statuses:
            self.assertIn(status, actual_statuses)

    def test_default_status_is_open(self):
        """Test that new feedback defaults to 'open' status."""
        feedback = AIFeedback.objects.create(
            team=self.team,
            category="other",
            reported_by=self.member,
        )
        self.assertEqual(feedback.status, "open")

    def test_resolve_feedback_sets_resolved_at(self):
        """Test that resolving feedback sets the resolved_at timestamp."""
        feedback = AIFeedback.objects.create(
            team=self.team,
            category="style_issue",
            reported_by=self.member,
        )
        self.assertIsNone(feedback.resolved_at)

        feedback.status = "resolved"
        feedback.resolved_at = timezone.now()
        feedback.save()

        feedback.refresh_from_db()
        self.assertEqual(feedback.status, "resolved")
        self.assertIsNotNone(feedback.resolved_at)

    def test_feedback_str_representation(self):
        """Test the string representation of feedback."""
        feedback = AIFeedback.objects.create(
            team=self.team,
            category="wrong_code",
            reported_by=self.member,
        )
        # Should include category display name
        self.assertIn("Generated wrong code", str(feedback))

    def test_feedback_ordering_is_newest_first(self):
        """Test that feedback is ordered by created_at descending."""
        feedback1 = AIFeedback.objects.create(
            team=self.team,
            category="other",
            reported_by=self.member,
        )
        feedback2 = AIFeedback.objects.create(
            team=self.team,
            category="wrong_code",
            reported_by=self.member,
        )
        feedback3 = AIFeedback.objects.create(
            team=self.team,
            category="style_issue",
            reported_by=self.member,
        )

        feedback_list = list(AIFeedback.objects.all())
        self.assertEqual(feedback_list[0], feedback3)
        self.assertEqual(feedback_list[1], feedback2)
        self.assertEqual(feedback_list[2], feedback1)


class TestAIFeedbackFactory(TestCase):
    """Tests for the AIFeedback factory."""

    def test_factory_creates_valid_feedback(self):
        """Test that the factory creates valid feedback."""
        feedback = AIFeedbackFactory()
        self.assertIsNotNone(feedback.id)
        self.assertIsNotNone(feedback.team)
        self.assertIsNotNone(feedback.category)
        self.assertIsNotNone(feedback.reported_by)

    def test_factory_with_custom_category(self):
        """Test factory with custom category."""
        feedback = AIFeedbackFactory(category="security")
        self.assertEqual(feedback.category, "security")

    def test_factory_with_pull_request(self):
        """Test factory with pull request."""
        pr = PullRequestFactory()
        feedback = AIFeedbackFactory(team=pr.team, pull_request=pr)
        self.assertEqual(feedback.pull_request, pr)


class TestAIFeedbackTeamIsolation(TestCase):
    """Tests for team isolation in AI Feedback."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = TeamFactory()
        self.team2 = TeamFactory()
        self.member1 = TeamMemberFactory(team=self.team1)
        self.member2 = TeamMemberFactory(team=self.team2)

    def test_for_team_manager_filters_by_team(self):
        """Test that for_team manager correctly filters by team."""
        from apps.teams.context import set_current_team

        feedback1 = AIFeedback.objects.create(
            team=self.team1,
            category="wrong_code",
            reported_by=self.member1,
        )
        feedback2 = AIFeedback.objects.create(
            team=self.team2,
            category="style_issue",
            reported_by=self.member2,
        )

        # Set team context and query
        set_current_team(self.team1)
        team1_feedback = list(AIFeedback.for_team.all())
        self.assertIn(feedback1, team1_feedback)
        self.assertNotIn(feedback2, team1_feedback)

        set_current_team(self.team2)
        team2_feedback = list(AIFeedback.for_team.all())
        self.assertNotIn(feedback1, team2_feedback)
        self.assertIn(feedback2, team2_feedback)
