from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestPRSurveyModel(TestCase):
    """Tests for PRSurvey model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.author = TeamMember.objects.create(team=self.team1, display_name="Author", github_username="author")
        self.pull_request1 = PullRequest.objects.create(
            team=self.team1, github_pr_id=1, github_repo="org/repo", state="open"
        )
        self.pull_request2 = PullRequest.objects.create(
            team=self.team1, github_pr_id=2, github_repo="org/repo", state="open"
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_survey_creation_with_pull_request(self):
        """Test that PRSurvey can be created with OneToOne to PullRequest."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertEqual(survey.team, self.team1)
        self.assertEqual(survey.pull_request, self.pull_request1)
        self.assertEqual(survey.author, self.author)
        self.assertIsNotNone(survey.pk)

    def test_pr_survey_one_to_one_enforced(self):
        """Test that OneToOne constraint is enforced (only one survey per PR)."""
        PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        # Attempt to create another survey for the same PR
        with self.assertRaises(IntegrityError):
            PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)

    def test_pr_survey_cascade_delete_when_pull_request_deleted(self):
        """Test that PRSurvey is cascade deleted when PullRequest is deleted."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        survey_id = survey.pk

        # Delete the pull request
        self.pull_request1.delete()

        # Verify survey is also deleted
        with self.assertRaises(PRSurvey.DoesNotExist):
            PRSurvey.objects.get(pk=survey_id)

    def test_pr_survey_author_ai_assisted_can_be_null(self):
        """Test that PRSurvey.author_ai_assisted can be null (not responded)."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertIsNone(survey.author_ai_assisted)

    def test_pr_survey_author_ai_assisted_can_be_true(self):
        """Test that PRSurvey.author_ai_assisted can be True."""
        survey = PRSurvey.objects.create(
            team=self.team1, pull_request=self.pull_request1, author=self.author, author_ai_assisted=True
        )
        self.assertTrue(survey.author_ai_assisted)

    def test_pr_survey_author_ai_assisted_can_be_false(self):
        """Test that PRSurvey.author_ai_assisted can be False."""
        survey = PRSurvey.objects.create(
            team=self.team1, pull_request=self.pull_request1, author=self.author, author_ai_assisted=False
        )
        self.assertFalse(survey.author_ai_assisted)

    def test_pr_survey_author_responded_at_can_be_set(self):
        """Test that PRSurvey.author_responded_at can be set."""
        responded_time = django_timezone.now()
        survey = PRSurvey.objects.create(
            team=self.team1,
            pull_request=self.pull_request1,
            author=self.author,
            author_ai_assisted=True,
            author_responded_at=responded_time,
        )
        self.assertEqual(survey.author_responded_at, responded_time)

    def test_pr_survey_multiple_surveys_different_prs_allowed(self):
        """Test that multiple surveys can be created for different PRs."""
        survey1 = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        survey2 = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request2, author=self.author)
        self.assertNotEqual(survey1.pull_request, survey2.pull_request)
        self.assertEqual(survey1.author, survey2.author)

    def test_pr_survey_for_team_manager_filters_by_current_team(self):
        """Test that PRSurvey.for_team manager filters by current team context."""
        # Create another team with PR
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=3, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")

        # Create surveys for both teams
        survey1 = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        survey2 = PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_surveys = list(PRSurvey.for_team.all())
        self.assertEqual(len(team1_surveys), 1)
        self.assertEqual(team1_surveys[0].pk, survey1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_surveys = list(PRSurvey.for_team.all())
        self.assertEqual(len(team2_surveys), 1)
        self.assertEqual(team2_surveys[0].pk, survey2.pk)

    def test_pr_survey_for_team_manager_with_context_manager(self):
        """Test that PRSurvey.for_team works with context manager."""
        # Create another team with PR
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=4, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")

        # Create surveys for both teams
        PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)

        with current_team(self.team1):
            self.assertEqual(PRSurvey.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(PRSurvey.for_team.count(), 1)

    def test_pr_survey_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PRSurvey.for_team returns empty queryset when no team is set."""
        PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PRSurvey.for_team.count(), 0)

    def test_pr_survey_has_created_at_from_base_model(self):
        """Test that PRSurvey inherits created_at from BaseModel."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertIsNotNone(survey.created_at)

    def test_pr_survey_has_updated_at_from_base_model(self):
        """Test that PRSurvey inherits updated_at from BaseModel."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertIsNotNone(survey.updated_at)


class TestPRSurveyReviewModel(TestCase):
    """Tests for PRSurveyReview model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.author = TeamMember.objects.create(team=self.team1, display_name="Author", github_username="author")
        self.reviewer1 = TeamMember.objects.create(
            team=self.team1, display_name="Reviewer 1", github_username="reviewer1"
        )
        self.reviewer2 = TeamMember.objects.create(
            team=self.team1, display_name="Reviewer 2", github_username="reviewer2"
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team1, github_pr_id=1, github_repo="org/repo", state="open"
        )
        self.survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request, author=self.author)

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_survey_review_creation_linked_to_survey(self):
        """Test that PRSurveyReview can be created linked to PRSurvey."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=3
        )
        self.assertEqual(review.team, self.team1)
        self.assertEqual(review.survey, self.survey)
        self.assertEqual(review.reviewer, self.reviewer1)
        self.assertEqual(review.quality_rating, 3)
        self.assertIsNotNone(review.pk)

    def test_pr_survey_review_quality_choice_1_could_be_better(self):
        """Test that PRSurveyReview quality_rating 1 (Could be better) works correctly."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=1
        )
        self.assertEqual(review.quality_rating, 1)

    def test_pr_survey_review_quality_choice_2_ok(self):
        """Test that PRSurveyReview quality_rating 2 (OK) works correctly."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=2
        )
        self.assertEqual(review.quality_rating, 2)

    def test_pr_survey_review_quality_choice_3_super(self):
        """Test that PRSurveyReview quality_rating 3 (Super) works correctly."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=3
        )
        self.assertEqual(review.quality_rating, 3)

    def test_pr_survey_review_unique_constraint_survey_reviewer_enforced(self):
        """Test that unique constraint on (survey, reviewer) is enforced."""
        PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        # Attempt to create another review for same survey and reviewer
        with self.assertRaises(IntegrityError):
            PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)

    def test_pr_survey_review_cascade_delete_when_survey_deleted(self):
        """Test that PRSurveyReview is cascade deleted when PRSurvey is deleted."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        review_id = review.pk

        # Delete the survey
        self.survey.delete()

        # Verify review is also deleted
        with self.assertRaises(PRSurveyReview.DoesNotExist):
            PRSurveyReview.objects.get(pk=review_id)

    def test_pr_survey_review_ai_guess_can_be_null(self):
        """Test that PRSurveyReview.ai_guess can be null."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        self.assertIsNone(review.ai_guess)

    def test_pr_survey_review_ai_guess_can_be_true(self):
        """Test that PRSurveyReview.ai_guess can be True."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, ai_guess=True
        )
        self.assertTrue(review.ai_guess)

    def test_pr_survey_review_ai_guess_can_be_false(self):
        """Test that PRSurveyReview.ai_guess can be False."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, ai_guess=False
        )
        self.assertFalse(review.ai_guess)

    def test_pr_survey_review_guess_correct_scenario(self):
        """Test PRSurveyReview.guess_correct calculation scenario."""
        # Create survey with author_ai_assisted=True
        self.survey.author_ai_assisted = True
        self.survey.save()

        # Reviewer guesses True (correct)
        review_correct = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, ai_guess=True, guess_correct=True
        )
        self.assertTrue(review_correct.guess_correct)

        # Reviewer guesses False (incorrect)
        review_incorrect = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer2, ai_guess=False, guess_correct=False
        )
        self.assertFalse(review_incorrect.guess_correct)

    def test_pr_survey_review_multiple_reviews_per_survey_different_reviewers(self):
        """Test that multiple reviews per survey are allowed (different reviewers)."""
        review1 = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=3
        )
        review2 = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer2, quality_rating=2
        )
        # Both reviews should exist for the same survey
        self.assertEqual(review1.survey, review2.survey)
        self.assertNotEqual(review1.reviewer, review2.reviewer)
        self.assertEqual(self.survey.reviews.count(), 2)

    def test_pr_survey_review_responded_at_can_be_set(self):
        """Test that PRSurveyReview.responded_at can be set."""
        responded_time = django_timezone.now()
        review = PRSurveyReview.objects.create(
            team=self.team1,
            survey=self.survey,
            reviewer=self.reviewer1,
            quality_rating=3,
            responded_at=responded_time,
        )
        self.assertEqual(review.responded_at, responded_time)

    def test_pr_survey_review_for_team_manager_filters_by_current_team(self):
        """Test that PRSurveyReview.for_team manager filters by current team context."""
        # Create another team with survey
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=2, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")
        survey2 = PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)
        reviewer2_team2 = TeamMember.objects.create(
            team=self.team2, display_name="Reviewer 2", github_username="reviewer2_team2"
        )

        # Create reviews for both teams
        review1 = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        review2 = PRSurveyReview.objects.create(team=self.team2, survey=survey2, reviewer=reviewer2_team2)

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_reviews = list(PRSurveyReview.for_team.all())
        self.assertEqual(len(team1_reviews), 1)
        self.assertEqual(team1_reviews[0].pk, review1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_reviews = list(PRSurveyReview.for_team.all())
        self.assertEqual(len(team2_reviews), 1)
        self.assertEqual(team2_reviews[0].pk, review2.pk)

    def test_pr_survey_review_for_team_manager_with_context_manager(self):
        """Test that PRSurveyReview.for_team works with context manager."""
        # Create another team with survey
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=3, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")
        survey2 = PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)
        reviewer2_team2 = TeamMember.objects.create(
            team=self.team2, display_name="Reviewer 2", github_username="reviewer2_team2"
        )

        # Create reviews for both teams
        PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        PRSurveyReview.objects.create(team=self.team2, survey=survey2, reviewer=reviewer2_team2)

        with current_team(self.team1):
            self.assertEqual(PRSurveyReview.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(PRSurveyReview.for_team.count(), 1)

    def test_pr_survey_review_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PRSurveyReview.for_team returns empty queryset when no team is set."""
        PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PRSurveyReview.for_team.count(), 0)

    def test_pr_survey_review_has_created_at_from_base_model(self):
        """Test that PRSurveyReview inherits created_at from BaseModel."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        self.assertIsNotNone(review.created_at)

    def test_pr_survey_review_has_updated_at_from_base_model(self):
        """Test that PRSurveyReview inherits updated_at from BaseModel."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        self.assertIsNotNone(review.updated_at)


class TestSurveyResponseSourceFields(TestCase):
    """Tests for response source tracking fields (Phase 2 - Survey Improvements)."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(team=self.team, display_name="Author", github_username="author")
        self.reviewer = TeamMember.objects.create(team=self.team, display_name="Reviewer", github_username="reviewer")
        self.pull_request = PullRequest.objects.create(
            team=self.team, github_pr_id=100, github_repo="org/repo", state="merged"
        )
        self.survey = PRSurvey.objects.create(team=self.team, pull_request=self.pull_request, author=self.author)

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    # --- Response Source Constants Tests ---

    def test_response_source_choices_exists(self):
        """Test that RESPONSE_SOURCE_CHOICES constant exists."""
        from apps.metrics.models.surveys import RESPONSE_SOURCE_CHOICES

        self.assertIsInstance(RESPONSE_SOURCE_CHOICES, list)
        self.assertGreater(len(RESPONSE_SOURCE_CHOICES), 0)

    def test_response_source_choices_contains_github(self):
        """Test that RESPONSE_SOURCE_CHOICES contains 'github' option."""
        from apps.metrics.models.surveys import RESPONSE_SOURCE_CHOICES

        values = [choice[0] for choice in RESPONSE_SOURCE_CHOICES]
        self.assertIn("github", values)

    def test_response_source_choices_contains_slack(self):
        """Test that RESPONSE_SOURCE_CHOICES contains 'slack' option."""
        from apps.metrics.models.surveys import RESPONSE_SOURCE_CHOICES

        values = [choice[0] for choice in RESPONSE_SOURCE_CHOICES]
        self.assertIn("slack", values)

    def test_response_source_choices_contains_web(self):
        """Test that RESPONSE_SOURCE_CHOICES contains 'web' option."""
        from apps.metrics.models.surveys import RESPONSE_SOURCE_CHOICES

        values = [choice[0] for choice in RESPONSE_SOURCE_CHOICES]
        self.assertIn("web", values)

    def test_response_source_choices_contains_auto(self):
        """Test that RESPONSE_SOURCE_CHOICES contains 'auto' option for AI auto-detection."""
        from apps.metrics.models.surveys import RESPONSE_SOURCE_CHOICES

        values = [choice[0] for choice in RESPONSE_SOURCE_CHOICES]
        self.assertIn("auto", values)

    # --- Modification Effort Constants Tests ---

    def test_modification_effort_choices_exists(self):
        """Test that MODIFICATION_EFFORT_CHOICES constant exists."""
        from apps.metrics.models.surveys import MODIFICATION_EFFORT_CHOICES

        self.assertIsInstance(MODIFICATION_EFFORT_CHOICES, list)
        self.assertGreater(len(MODIFICATION_EFFORT_CHOICES), 0)

    def test_modification_effort_choices_contains_expected_values(self):
        """Test that MODIFICATION_EFFORT_CHOICES contains expected values."""
        from apps.metrics.models.surveys import MODIFICATION_EFFORT_CHOICES

        values = [choice[0] for choice in MODIFICATION_EFFORT_CHOICES]
        self.assertIn("none", values)
        self.assertIn("minor", values)
        self.assertIn("moderate", values)
        self.assertIn("major", values)
        self.assertIn("na", values)

    # --- PRSurvey.author_response_source Tests ---

    def test_pr_survey_author_response_source_can_be_null(self):
        """Test that PRSurvey.author_response_source can be null (default)."""
        self.assertIsNone(self.survey.author_response_source)

    def test_pr_survey_author_response_source_can_be_github(self):
        """Test that PRSurvey.author_response_source can be 'github'."""
        self.survey.author_response_source = "github"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.author_response_source, "github")

    def test_pr_survey_author_response_source_can_be_slack(self):
        """Test that PRSurvey.author_response_source can be 'slack'."""
        self.survey.author_response_source = "slack"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.author_response_source, "slack")

    def test_pr_survey_author_response_source_can_be_web(self):
        """Test that PRSurvey.author_response_source can be 'web'."""
        self.survey.author_response_source = "web"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.author_response_source, "web")

    def test_pr_survey_author_response_source_can_be_auto(self):
        """Test that PRSurvey.author_response_source can be 'auto' for AI auto-detection."""
        self.survey.author_response_source = "auto"
        self.survey.author_ai_assisted = True  # Set by auto-detection
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.author_response_source, "auto")
        self.assertTrue(self.survey.author_ai_assisted)

    # --- PRSurvey.ai_modification_effort Tests ---

    def test_pr_survey_ai_modification_effort_can_be_null(self):
        """Test that PRSurvey.ai_modification_effort can be null (default)."""
        self.assertIsNone(self.survey.ai_modification_effort)

    def test_pr_survey_ai_modification_effort_can_be_none_value(self):
        """Test that PRSurvey.ai_modification_effort can be 'none' (used as-is)."""
        self.survey.ai_modification_effort = "none"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.ai_modification_effort, "none")

    def test_pr_survey_ai_modification_effort_can_be_minor(self):
        """Test that PRSurvey.ai_modification_effort can be 'minor'."""
        self.survey.ai_modification_effort = "minor"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.ai_modification_effort, "minor")

    def test_pr_survey_ai_modification_effort_can_be_moderate(self):
        """Test that PRSurvey.ai_modification_effort can be 'moderate'."""
        self.survey.ai_modification_effort = "moderate"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.ai_modification_effort, "moderate")

    def test_pr_survey_ai_modification_effort_can_be_major(self):
        """Test that PRSurvey.ai_modification_effort can be 'major'."""
        self.survey.ai_modification_effort = "major"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.ai_modification_effort, "major")

    def test_pr_survey_ai_modification_effort_can_be_na(self):
        """Test that PRSurvey.ai_modification_effort can be 'na'."""
        self.survey.ai_modification_effort = "na"
        self.survey.save()
        self.survey.refresh_from_db()
        self.assertEqual(self.survey.ai_modification_effort, "na")

    # --- PRSurveyReview.response_source Tests ---

    def test_pr_survey_review_response_source_can_be_null(self):
        """Test that PRSurveyReview.response_source can be null (default)."""
        review = PRSurveyReview.objects.create(team=self.team, survey=self.survey, reviewer=self.reviewer)
        self.assertIsNone(review.response_source)

    def test_pr_survey_review_response_source_can_be_github(self):
        """Test that PRSurveyReview.response_source can be 'github'."""
        review = PRSurveyReview.objects.create(
            team=self.team, survey=self.survey, reviewer=self.reviewer, response_source="github"
        )
        self.assertEqual(review.response_source, "github")

    def test_pr_survey_review_response_source_can_be_slack(self):
        """Test that PRSurveyReview.response_source can be 'slack'."""
        review = PRSurveyReview.objects.create(
            team=self.team, survey=self.survey, reviewer=self.reviewer, response_source="slack"
        )
        self.assertEqual(review.response_source, "slack")

    def test_pr_survey_review_response_source_can_be_web(self):
        """Test that PRSurveyReview.response_source can be 'web'."""
        review = PRSurveyReview.objects.create(
            team=self.team, survey=self.survey, reviewer=self.reviewer, response_source="web"
        )
        self.assertEqual(review.response_source, "web")
