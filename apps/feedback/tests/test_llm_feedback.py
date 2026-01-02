"""
Tests for the LLMFeedback model.

TDD RED Phase: These tests define the expected behavior of the LLMFeedback model
which does not exist yet. All tests should fail until the model is implemented.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.integrations.factories import UserFactory
from apps.metrics.factories import (
    DailyInsightFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestLLMFeedbackModel(TestCase):
    """Tests for the LLMFeedback model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.pr = PullRequestFactory(team=self.team, author=self.member)

    def test_llm_feedback_requires_rating(self):
        """Test that LLMFeedback requires a rating field (True=thumbs up, False=thumbs down)."""
        from apps.feedback.models import LLMFeedback

        # Should raise an error when rating is not provided
        with self.assertRaises((IntegrityError, ValidationError)):
            feedback = LLMFeedback(
                team=self.team,
                user=self.user,
                content_type="pr_summary",
                content_snapshot={"summary": "Test summary"},
            )
            feedback.full_clean()
            feedback.save()

    def test_llm_feedback_requires_content_type(self):
        """Test that LLMFeedback requires a content_type field."""
        from apps.feedback.models import LLMFeedback

        # Should raise an error when content_type is not provided
        with self.assertRaises((IntegrityError, ValidationError)):
            feedback = LLMFeedback(
                team=self.team,
                user=self.user,
                rating=True,
                content_snapshot={"summary": "Test summary"},
            )
            feedback.full_clean()
            feedback.save()

    def test_llm_feedback_requires_user(self):
        """Test that LLMFeedback requires a user field."""
        from apps.feedback.models import LLMFeedback

        # Should raise an error when user is not provided (CASCADE requires it)
        with self.assertRaises((IntegrityError, ValidationError)):
            feedback = LLMFeedback(
                team=self.team,
                content_type="pr_summary",
                rating=True,
                content_snapshot={"summary": "Test summary"},
            )
            feedback.full_clean()
            feedback.save()

    def test_llm_feedback_content_type_choices_valid(self):
        """Test that content_type only accepts valid choices."""
        from apps.feedback.models import CONTENT_TYPE_CHOICES, LLMFeedback

        # Verify expected choices exist
        expected_choices = ["engineering_insight", "pr_summary", "qa_answer", "ai_detection"]
        actual_choices = [choice[0] for choice in CONTENT_TYPE_CHOICES]

        for choice in expected_choices:
            self.assertIn(choice, actual_choices)

        # Creating with valid choice should work
        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test summary"},
        )
        self.assertEqual(feedback.content_type, "pr_summary")

        # Creating with invalid choice should fail
        with self.assertRaises(ValidationError):
            invalid_feedback = LLMFeedback(
                team=self.team,
                user=self.user,
                content_type="invalid_type",
                rating=True,
                content_snapshot={"summary": "Test summary"},
            )
            invalid_feedback.full_clean()

    def test_llm_feedback_can_link_to_pull_request(self):
        """Test that LLMFeedback can optionally link to a PullRequest."""
        from apps.feedback.models import LLMFeedback

        # Create feedback linked to a PR
        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test summary"},
            pull_request=self.pr,
        )

        self.assertEqual(feedback.pull_request, self.pr)
        self.assertEqual(feedback.pull_request.id, self.pr.id)

        # Create feedback without PR link (should also work)
        feedback_no_pr = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="ai_detection",
            rating=False,
            content_snapshot={"detected": True},
        )

        self.assertIsNone(feedback_no_pr.pull_request)

    def test_llm_feedback_can_link_to_daily_insight(self):
        """Test that LLMFeedback can optionally link to a DailyInsight."""
        from apps.feedback.models import LLMFeedback

        daily_insight = DailyInsightFactory(team=self.team)

        # Create feedback linked to a DailyInsight
        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="engineering_insight",
            rating=True,
            content_snapshot={"insight": "Team velocity improved"},
            daily_insight=daily_insight,
        )

        self.assertEqual(feedback.daily_insight, daily_insight)
        self.assertEqual(feedback.daily_insight.id, daily_insight.id)

        # Create feedback without insight link (should also work)
        feedback_no_insight = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="qa_answer",
            rating=False,
            content_snapshot={"answer": "Test answer"},
        )

        self.assertIsNone(feedback_no_insight.daily_insight)

    def test_llm_feedback_belongs_to_team(self):
        """Test that LLMFeedback is team-scoped via BaseTeamModel."""
        from apps.feedback.models import LLMFeedback
        from apps.teams.context import set_current_team

        team2 = TeamFactory()
        user2 = UserFactory()

        # Create feedback for different teams
        feedback1 = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Team 1 summary"},
        )
        feedback2 = LLMFeedback.objects.create(
            team=team2,
            user=user2,
            content_type="pr_summary",
            rating=False,
            content_snapshot={"summary": "Team 2 summary"},
        )

        # Verify team FK is set correctly
        self.assertEqual(feedback1.team, self.team)
        self.assertEqual(feedback2.team, team2)

        # Test for_team manager filters by team context
        set_current_team(self.team)
        team1_feedback = list(LLMFeedback.for_team.all())
        self.assertIn(feedback1, team1_feedback)
        self.assertNotIn(feedback2, team1_feedback)

        set_current_team(team2)
        team2_feedback = list(LLMFeedback.for_team.all())
        self.assertNotIn(feedback1, team2_feedback)
        self.assertIn(feedback2, team2_feedback)

    def test_llm_feedback_stores_json_snapshot(self):
        """Test that content_snapshot stores JSON data correctly."""
        from apps.feedback.models import LLMFeedback

        snapshot_data = {
            "summary": "This PR adds a new feature for user authentication",
            "key_changes": ["Added login endpoint", "Added JWT support"],
            "complexity_score": 7,
            "metadata": {
                "model": "claude-3-opus",
                "tokens_used": 1500,
            },
        }

        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot=snapshot_data,
        )

        # Reload from database to ensure proper serialization
        feedback.refresh_from_db()

        self.assertEqual(feedback.content_snapshot, snapshot_data)
        self.assertEqual(feedback.content_snapshot["summary"], snapshot_data["summary"])
        self.assertEqual(feedback.content_snapshot["key_changes"], snapshot_data["key_changes"])
        self.assertEqual(feedback.content_snapshot["metadata"]["model"], "claude-3-opus")

    def test_llm_feedback_stores_input_context(self):
        """Test that input_context stores JSON data correctly (nullable)."""
        from apps.feedback.models import LLMFeedback

        input_context_data = {
            "pr_title": "Add user authentication",
            "pr_body": "This PR implements OAuth2 login",
            "files_changed": ["auth/views.py", "auth/models.py"],
            "diff_stats": {"additions": 250, "deletions": 50},
        }

        # Create with input_context
        feedback_with_context = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test"},
            input_context=input_context_data,
        )

        feedback_with_context.refresh_from_db()
        self.assertEqual(feedback_with_context.input_context, input_context_data)
        self.assertEqual(feedback_with_context.input_context["pr_title"], "Add user authentication")

        # Create without input_context (nullable)
        feedback_no_context = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="ai_detection",
            rating=False,
            content_snapshot={"detected": True},
        )

        feedback_no_context.refresh_from_db()
        self.assertIsNone(feedback_no_context.input_context)

    def test_llm_feedback_stores_prompt_version(self):
        """Test that prompt_version field stores version string correctly."""
        from apps.feedback.models import LLMFeedback

        # Create with prompt_version
        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test"},
            prompt_version="1.2.3",
        )

        feedback.refresh_from_db()
        self.assertEqual(feedback.prompt_version, "1.2.3")

        # Create without prompt_version (should default to empty string)
        feedback_no_version = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="ai_detection",
            rating=True,
            content_snapshot={"detected": False},
        )

        feedback_no_version.refresh_from_db()
        self.assertEqual(feedback_no_version.prompt_version, "")


class TestLLMFeedbackSubmittedBy(TestCase):
    """Tests for the submitted_by relationship in LLMFeedback."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_llm_feedback_can_link_to_team_member(self):
        """Test that LLMFeedback can optionally link to a TeamMember via submitted_by."""
        from apps.feedback.models import LLMFeedback

        # Create feedback with submitted_by
        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test"},
            submitted_by=self.member,
        )

        self.assertEqual(feedback.submitted_by, self.member)
        self.assertEqual(feedback.submitted_by.id, self.member.id)

        # Create feedback without submitted_by (nullable)
        feedback_no_member = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="ai_detection",
            rating=False,
            content_snapshot={"detected": True},
        )

        self.assertIsNone(feedback_no_member.submitted_by)


class TestLLMFeedbackComment(TestCase):
    """Tests for the comment field in LLMFeedback."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()

    def test_llm_feedback_stores_comment(self):
        """Test that comment field stores text correctly (blank allowed)."""
        from apps.feedback.models import LLMFeedback

        # Create with comment
        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=False,
            content_snapshot={"summary": "Test"},
            comment="The summary missed important security implications of the changes.",
        )

        feedback.refresh_from_db()
        self.assertEqual(
            feedback.comment,
            "The summary missed important security implications of the changes.",
        )

        # Create without comment (blank=True)
        feedback_no_comment = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="ai_detection",
            rating=True,
            content_snapshot={"detected": True},
        )

        feedback_no_comment.refresh_from_db()
        self.assertEqual(feedback_no_comment.comment, "")


class TestLLMFeedbackOnDelete(TestCase):
    """Tests for on_delete behavior of LLMFeedback foreign keys."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = UserFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.pr = PullRequestFactory(team=self.team, author=self.member)

    def test_user_delete_cascades_to_feedback(self):
        """Test that deleting a user cascades to delete their feedback."""
        from apps.feedback.models import LLMFeedback

        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test"},
        )
        feedback_id = feedback.id

        # Delete user
        self.user.delete()

        # Feedback should be deleted (CASCADE)
        self.assertFalse(LLMFeedback.objects.filter(id=feedback_id).exists())

    def test_pull_request_delete_sets_null(self):
        """Test that deleting a PR sets pull_request to null."""
        from apps.feedback.models import LLMFeedback

        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test"},
            pull_request=self.pr,
        )

        # Delete PR
        self.pr.delete()

        # Feedback should still exist with null PR (SET_NULL)
        feedback.refresh_from_db()
        self.assertIsNone(feedback.pull_request)

    def test_team_member_delete_sets_null(self):
        """Test that deleting a TeamMember sets submitted_by to null."""
        from apps.feedback.models import LLMFeedback

        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="pr_summary",
            rating=True,
            content_snapshot={"summary": "Test"},
            submitted_by=self.member,
        )

        # Delete team member
        self.member.delete()

        # Feedback should still exist with null submitted_by (SET_NULL)
        feedback.refresh_from_db()
        self.assertIsNone(feedback.submitted_by)

    def test_daily_insight_delete_sets_null(self):
        """Test that deleting a DailyInsight sets daily_insight to null."""
        from apps.feedback.models import LLMFeedback

        daily_insight = DailyInsightFactory(team=self.team)

        feedback = LLMFeedback.objects.create(
            team=self.team,
            user=self.user,
            content_type="engineering_insight",
            rating=True,
            content_snapshot={"insight": "Test"},
            daily_insight=daily_insight,
        )

        # Delete daily insight
        daily_insight.delete()

        # Feedback should still exist with null daily_insight (SET_NULL)
        feedback.refresh_from_db()
        self.assertIsNone(feedback.daily_insight)


class TestLLMFeedbackFactory(TestCase):
    """Tests for LLMFeedbackFactory."""

    def test_factory_creates_valid_instance(self):
        """Test that LLMFeedbackFactory creates valid LLMFeedback instances."""
        from apps.feedback.factories import LLMFeedbackFactory

        feedback = LLMFeedbackFactory()

        self.assertIsNotNone(feedback.id)
        self.assertIsNotNone(feedback.team)
        self.assertIsNotNone(feedback.user)
        self.assertIn(
            feedback.content_type,
            ["engineering_insight", "pr_summary", "qa_answer", "ai_detection"],
        )
        self.assertIn(feedback.rating, [True, False])
        self.assertIsInstance(feedback.content_snapshot, dict)

    def test_factory_batch_creates_multiple_instances(self):
        """Test that factory can create multiple instances."""
        from apps.feedback.factories import LLMFeedbackFactory

        feedback_list = LLMFeedbackFactory.create_batch(3)

        self.assertEqual(len(feedback_list), 3)
        for feedback in feedback_list:
            self.assertIsNotNone(feedback.id)


class TestLLMFeedbackIndexes(TestCase):
    """Tests for LLMFeedback database indexes."""

    def test_model_has_content_type_index(self):
        """Test that model has index on content_type for filtering by type."""
        from apps.feedback.models import LLMFeedback

        indexes = LLMFeedback._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]
        self.assertIn(("content_type",), index_fields)

    def test_model_has_rating_index(self):
        """Test that model has index on rating for quality analysis."""
        from apps.feedback.models import LLMFeedback

        indexes = LLMFeedback._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]
        self.assertIn(("rating",), index_fields)

    def test_model_has_team_created_at_index(self):
        """Test that model has composite index on (team, created_at) for dashboard queries."""
        from apps.feedback.models import LLMFeedback

        indexes = LLMFeedback._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]
        self.assertIn(("team", "created_at"), index_fields)

    def test_model_has_team_type_rating_index(self):
        """Test that model has composite index on (team, content_type, rating) for analysis."""
        from apps.feedback.models import LLMFeedback

        indexes = LLMFeedback._meta.indexes
        index_fields = [tuple(idx.fields) for idx in indexes]
        self.assertIn(("team", "content_type", "rating"), index_fields)
