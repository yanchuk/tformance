"""
Tests for survey web views (public, token-based access).

These views handle PR survey access via unique tokens sent through Slack.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import PRSurveyFactory, TeamMemberFactory
from apps.users.models import CustomUser


class TestSurveyLandingView(TestCase):
    """Tests for survey landing page (determines role, redirects to appropriate form)."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        self.author = TeamMemberFactory()
        self.reviewer = TeamMemberFactory(team=self.author.team)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="valid-token-123",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

    def test_survey_landing_url_resolves(self):
        """Test that survey landing URL pattern is configured."""
        url = reverse("web:survey_landing", kwargs={"token": "valid-token-123"})
        self.assertEqual(url, "/survey/valid-token-123/")

    def test_survey_landing_requires_authentication(self):
        """Test that unauthenticated users are redirected to login."""
        url = reverse("web:survey_landing", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_survey_landing_with_valid_token_authenticated(self):
        """Test that valid token redirects authenticated user to appropriate form."""
        self.client.force_login(self.user)
        url = reverse("web:survey_landing", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should redirect to either author or reviewer form
        self.assertEqual(response.status_code, 302)
        self.assertIn("/survey/", response.url)

    def test_survey_landing_with_invalid_token_shows_error(self):
        """Test that invalid token shows error page."""
        self.client.force_login(self.user)
        url = reverse("web:survey_landing", kwargs={"token": "invalid-token"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_survey_landing_with_expired_token_shows_error(self):
        """Test that expired token shows error page."""
        self.client.force_login(self.user)
        expired_survey = PRSurveyFactory(
            token="expired-token",
            token_expires_at=timezone.now() - timedelta(days=1),
        )
        url = reverse("web:survey_landing", kwargs={"token": expired_survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 410)  # Gone


class TestSurveyAuthorView(TestCase):
    """Tests for author survey form view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from allauth.socialaccount.models import SocialAccount

        self.author = TeamMemberFactory(github_id="12345")
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="author-token-123",
            token_expires_at=timezone.now() + timedelta(days=7),
        )
        # Create user with matching GitHub ID
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="12345",  # Matches author's github_id
        )

    def test_author_survey_url_resolves(self):
        """Test that author survey URL pattern is configured."""
        url = reverse("web:survey_author", kwargs={"token": "author-token-123"})
        self.assertEqual(url, "/survey/author-token-123/author/")

    def test_author_survey_requires_authentication(self):
        """Test that unauthenticated users are redirected to login."""
        url = reverse("web:survey_author", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_author_survey_accessible_when_authenticated(self):
        """Test that authenticated users can access author survey form."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI")  # Should ask about AI assistance

    def test_author_survey_invalid_token_shows_error(self):
        """Test that invalid token shows error."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": "invalid"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_author_survey_expired_token_shows_error(self):
        """Test that expired token shows error."""
        self.client.force_login(self.user)
        expired_survey = PRSurveyFactory(
            token="expired-author-token",
            token_expires_at=timezone.now() - timedelta(days=1),
        )
        url = reverse("web:survey_author", kwargs={"token": expired_survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 410)


class TestSurveyReviewerView(TestCase):
    """Tests for reviewer survey form view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from allauth.socialaccount.models import SocialAccount

        from apps.metrics.factories import PRReviewFactory, PullRequestFactory

        self.author = TeamMemberFactory(github_id="10000")
        self.reviewer = TeamMemberFactory(team=self.author.team, github_id="20001")

        # Create PR and survey
        self.pr = PullRequestFactory(team=self.author.team, author=self.author)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            pull_request=self.pr,
            author=self.author,
            token="reviewer-token-123",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

        # Create PR review for the reviewer
        PRReviewFactory(team=self.author.team, pull_request=self.pr, reviewer=self.reviewer)

        # Create user with matching GitHub ID for the reviewer
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="20001",  # Matches reviewer's github_id
        )

    def test_reviewer_survey_url_resolves(self):
        """Test that reviewer survey URL pattern is configured."""
        url = reverse("web:survey_reviewer", kwargs={"token": "reviewer-token-123"})
        self.assertEqual(url, "/survey/reviewer-token-123/reviewer/")

    def test_reviewer_survey_requires_authentication(self):
        """Test that unauthenticated users are redirected to login."""
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_reviewer_survey_accessible_when_authenticated(self):
        """Test that authenticated users can access reviewer survey form."""
        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quality")  # Should ask about quality rating
        self.assertContains(response, "AI")  # Should ask for AI guess

    def test_reviewer_survey_invalid_token_shows_error(self):
        """Test that invalid token shows error."""
        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": "invalid"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_reviewer_survey_expired_token_shows_error(self):
        """Test that expired token shows error."""
        self.client.force_login(self.user)
        expired_survey = PRSurveyFactory(
            token="expired-reviewer-token",
            token_expires_at=timezone.now() - timedelta(days=1),
        )
        url = reverse("web:survey_reviewer", kwargs={"token": expired_survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 410)


class TestSurveySubmitView(TestCase):
    """Tests for survey form submission view."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        self.author = TeamMemberFactory()
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="submit-token-123",
            token_expires_at=timezone.now() + timedelta(days=7),
            author_ai_assisted=None,  # Not yet responded
        )

    def test_survey_submit_url_resolves(self):
        """Test that survey submit URL pattern is configured."""
        url = reverse("web:survey_submit", kwargs={"token": "submit-token-123"})
        self.assertEqual(url, "/survey/submit-token-123/submit/")

    def test_survey_submit_requires_authentication(self):
        """Test that unauthenticated users cannot submit."""
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(url, {"ai_assisted": "true"})

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_survey_submit_accepts_post_only(self):
        """Test that GET requests to submit URL are not allowed."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_survey_submit_with_valid_data_redirects_to_complete(self):
        """Test that valid submission redirects to thank you page."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(url, {"ai_assisted": "true"})

        # Should redirect to complete page
        self.assertEqual(response.status_code, 302)
        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertEqual(response.url, expected_url)

    def test_survey_submit_invalid_token_shows_error(self):
        """Test that invalid token shows error."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": "invalid"})
        response = self.client.post(url, {"ai_assisted": "true"})

        self.assertEqual(response.status_code, 404)

    def test_survey_submit_expired_token_shows_error(self):
        """Test that expired token shows error."""
        self.client.force_login(self.user)
        expired_survey = PRSurveyFactory(
            token="expired-submit-token",
            token_expires_at=timezone.now() - timedelta(days=1),
        )
        url = reverse("web:survey_submit", kwargs={"token": expired_survey.token})
        response = self.client.post(url, {"ai_assisted": "true"})

        self.assertEqual(response.status_code, 410)


class TestSurveyCompleteView(TestCase):
    """Tests for survey thank you page."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        self.author = TeamMemberFactory()
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="complete-token-123",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

    def test_survey_complete_url_resolves(self):
        """Test that survey complete URL pattern is configured."""
        url = reverse("web:survey_complete", kwargs={"token": "complete-token-123"})
        self.assertEqual(url, "/survey/complete-token-123/complete/")

    def test_survey_complete_requires_authentication(self):
        """Test that unauthenticated users are redirected to login."""
        url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_survey_complete_shows_thank_you_message(self):
        """Test that complete page shows thank you message."""
        self.client.force_login(self.user)
        url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Thank")  # Should have a thank you message

    def test_survey_complete_invalid_token_shows_error(self):
        """Test that invalid token shows error."""
        self.client.force_login(self.user)
        url = reverse("web:survey_complete", kwargs={"token": "invalid"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 404)

    def test_survey_complete_with_expired_token_still_accessible(self):
        """Test that complete page is accessible even with expired token (they already completed it)."""
        self.client.force_login(self.user)
        expired_survey = PRSurveyFactory(
            token="expired-complete-token",
            token_expires_at=timezone.now() - timedelta(days=1),
            author_ai_assisted=True,  # Already responded
            author_responded_at=timezone.now() - timedelta(days=2),
        )
        url = reverse("web:survey_complete", kwargs={"token": expired_survey.token})
        response = self.client.get(url)

        # Complete page should be accessible even after expiration if survey was already completed
        self.assertEqual(response.status_code, 200)


class TestAuthorSurveySubmission(TestCase):
    """Tests for author survey submission that records responses."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        self.author = TeamMemberFactory()
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="author-submit-token",
            token_expires_at=timezone.now() + timedelta(days=7),
            author_ai_assisted=None,  # Not yet responded
            author_responded_at=None,
        )

    def test_author_submits_yes_records_ai_assisted_true(self):
        """Test that submitting 'yes' sets author_ai_assisted to True."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(url, {"ai_assisted": "true"})

        # Reload survey from database
        self.survey.refresh_from_db()

        # Should record the response
        self.assertTrue(self.survey.author_ai_assisted)
        self.assertEqual(response.status_code, 302)

    def test_author_submits_no_records_ai_assisted_false(self):
        """Test that submitting 'no' sets author_ai_assisted to False."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(url, {"ai_assisted": "false"})

        # Reload survey from database
        self.survey.refresh_from_db()

        # Should record the response
        self.assertFalse(self.survey.author_ai_assisted)
        self.assertEqual(response.status_code, 302)

    def test_author_submission_sets_responded_at_timestamp(self):
        """Test that author submission sets author_responded_at timestamp."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})

        # Record time before submission
        before_submit = timezone.now()

        response = self.client.post(url, {"ai_assisted": "true"})

        # Reload survey from database
        self.survey.refresh_from_db()

        # Should have set responded_at timestamp
        self.assertIsNotNone(self.survey.author_responded_at)
        self.assertGreaterEqual(self.survey.author_responded_at, before_submit)
        self.assertLessEqual(self.survey.author_responded_at, timezone.now())
        self.assertEqual(response.status_code, 302)

    def test_duplicate_author_submission_is_ignored(self):
        """Test that submitting again when already responded is ignored."""
        # Author has already responded
        original_time = timezone.now() - timedelta(hours=2)
        self.survey.author_ai_assisted = True
        self.survey.author_responded_at = original_time
        self.survey.save()

        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(url, {"ai_assisted": "false"})

        # Reload survey from database
        self.survey.refresh_from_db()

        # Should NOT have changed the original response
        self.assertTrue(self.survey.author_ai_assisted)  # Still True
        self.assertEqual(self.survey.author_responded_at, original_time)  # Same timestamp
        self.assertEqual(response.status_code, 302)

    def test_author_submission_redirects_to_complete_page(self):
        """Test that successful submission redirects to complete page."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(url, {"ai_assisted": "true"})

        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)


class TestAuthorSurveyAuthorization(TestCase):
    """Tests for author survey authorization - verifies user is the PR author."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from allauth.socialaccount.models import SocialAccount

        # Create team and PR author
        self.author = TeamMemberFactory(github_id="12345")
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="author-auth-token",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

        # Create user who is the author (has matching GitHub ID)
        self.author_user = CustomUser.objects.create_user(username="author_user", password="testpass123")
        SocialAccount.objects.create(
            user=self.author_user,
            provider="github",
            uid="12345",  # Matches author's github_id
        )

        # Create user who is NOT the author (different GitHub ID)
        self.non_author_user = CustomUser.objects.create_user(username="non_author", password="testpass123")
        SocialAccount.objects.create(
            user=self.non_author_user,
            provider="github",
            uid="99999",  # Different GitHub ID
        )

        # Create user with no GitHub account
        self.user_no_github = CustomUser.objects.create_user(username="no_github", password="testpass123")

    def test_author_can_access_author_survey(self):
        """Test that user whose GitHub ID matches PR author can access author survey."""
        self.client.force_login(self.author_user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should allow access (200 OK)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI")

    def test_non_author_gets_403_on_author_survey(self):
        """Test that user who is not the PR author gets 403 Forbidden."""
        self.client.force_login(self.non_author_user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should deny access (403 Forbidden)
        self.assertEqual(response.status_code, 403)

    def test_user_with_no_github_id_gets_403_on_author_survey(self):
        """Test that user with no GitHub account gets 403 Forbidden."""
        self.client.force_login(self.user_no_github)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should deny access (403 Forbidden)
        self.assertEqual(response.status_code, 403)


class TestReviewerSurveyAuthorization(TestCase):
    """Tests for reviewer survey authorization - verifies user is a PR reviewer."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from allauth.socialaccount.models import SocialAccount

        from apps.metrics.factories import PRReviewFactory

        # Create team, author, and reviewers
        self.author = TeamMemberFactory(github_id="10000")
        self.reviewer1 = TeamMemberFactory(team=self.author.team, github_id="20001")
        self.reviewer2 = TeamMemberFactory(team=self.author.team, github_id="20002")
        self.non_reviewer = TeamMemberFactory(team=self.author.team, github_id="30000")

        # Create PR and survey
        from apps.metrics.factories import PullRequestFactory

        self.pr = PullRequestFactory(team=self.author.team, author=self.author)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            pull_request=self.pr,
            author=self.author,
            token="reviewer-auth-token",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

        # Create PR reviews for reviewer1 and reviewer2
        PRReviewFactory(team=self.author.team, pull_request=self.pr, reviewer=self.reviewer1)
        PRReviewFactory(team=self.author.team, pull_request=self.pr, reviewer=self.reviewer2)

        # Create users with matching GitHub IDs
        self.reviewer1_user = CustomUser.objects.create_user(username="reviewer1", password="testpass123")
        SocialAccount.objects.create(
            user=self.reviewer1_user,
            provider="github",
            uid="20001",  # Matches reviewer1's github_id
        )

        self.reviewer2_user = CustomUser.objects.create_user(username="reviewer2", password="testpass123")
        SocialAccount.objects.create(
            user=self.reviewer2_user,
            provider="github",
            uid="20002",  # Matches reviewer2's github_id
        )

        # Create user who is NOT a reviewer
        self.non_reviewer_user = CustomUser.objects.create_user(username="non_reviewer", password="testpass123")
        SocialAccount.objects.create(
            user=self.non_reviewer_user,
            provider="github",
            uid="30000",  # Matches non_reviewer's github_id (not in PR reviews)
        )

        # Create user with no GitHub account
        self.user_no_github = CustomUser.objects.create_user(username="no_github", password="testpass123")

    def test_reviewer_can_access_reviewer_survey(self):
        """Test that user whose GitHub ID matches a PR reviewer can access reviewer survey."""
        self.client.force_login(self.reviewer1_user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should allow access (200 OK)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quality")

    def test_second_reviewer_can_also_access_reviewer_survey(self):
        """Test that another reviewer of the same PR can also access reviewer survey."""
        self.client.force_login(self.reviewer2_user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should allow access (200 OK)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quality")

    def test_non_reviewer_gets_403_on_reviewer_survey(self):
        """Test that user who is not a PR reviewer gets 403 Forbidden."""
        self.client.force_login(self.non_reviewer_user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should deny access (403 Forbidden)
        self.assertEqual(response.status_code, 403)

    def test_user_with_no_github_id_gets_403_on_reviewer_survey(self):
        """Test that user with no GitHub account gets 403 Forbidden."""
        self.client.force_login(self.user_no_github)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        # Should deny access (403 Forbidden)
        self.assertEqual(response.status_code, 403)


class TestReviewerSurveySubmission(TestCase):
    """Tests for reviewer survey submission that records responses."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        self.author = TeamMemberFactory()
        self.reviewer = TeamMemberFactory(team=self.author.team)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="reviewer-submit-token",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

    def test_reviewer_submission_creates_survey_review(self):
        """Test that reviewer submission creates a PRSurveyReview record."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(
            url, {"quality_rating": "2", "ai_guess": "true", "reviewer_id": str(self.reviewer.id)}
        )

        # Should have created a PRSurveyReview
        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNotNone(review)
        self.assertEqual(response.status_code, 302)

    def test_reviewer_submission_records_quality_rating(self):
        """Test that reviewer submission records quality_rating correctly."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(
            url, {"quality_rating": "3", "ai_guess": "false", "reviewer_id": str(self.reviewer.id)}
        )

        # Should record quality rating
        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertEqual(review.quality_rating, 3)
        self.assertEqual(response.status_code, 302)

    def test_reviewer_submission_records_ai_guess(self):
        """Test that reviewer submission records ai_guess correctly."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(
            url, {"quality_rating": "2", "ai_guess": "true", "reviewer_id": str(self.reviewer.id)}
        )

        # Should record AI guess
        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertTrue(review.ai_guess)
        self.assertEqual(response.status_code, 302)

    def test_reviewer_submission_sets_responded_at_timestamp(self):
        """Test that reviewer submission sets responded_at timestamp."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})

        # Record time before submission
        before_submit = timezone.now()

        response = self.client.post(
            url, {"quality_rating": "1", "ai_guess": "false", "reviewer_id": str(self.reviewer.id)}
        )

        # Should have set responded_at timestamp
        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNotNone(review.responded_at)
        self.assertGreaterEqual(review.responded_at, before_submit)
        self.assertLessEqual(review.responded_at, timezone.now())
        self.assertEqual(response.status_code, 302)

    def test_reviewer_submission_redirects_to_complete_page(self):
        """Test that successful reviewer submission redirects to complete page."""
        self.client.force_login(self.user)
        url = reverse("web:survey_submit", kwargs={"token": self.survey.token})
        response = self.client.post(
            url, {"quality_rating": "2", "ai_guess": "true", "reviewer_id": str(self.reviewer.id)}
        )

        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)


class TestOneClickAuthorVoting(TestCase):
    """Tests for one-click author voting via ?vote= query parameter.

    One-click voting allows authors to vote directly from PR description links
    by appending ?vote=yes or ?vote=no to the survey URL.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from allauth.socialaccount.models import SocialAccount

        self.author = TeamMemberFactory(github_id="12345")
        self.survey = PRSurveyFactory(
            team=self.author.team,
            author=self.author,
            token="oneclick-author-token",
            token_expires_at=timezone.now() + timedelta(days=7),
            author_ai_assisted=None,
            author_responded_at=None,
            author_response_source=None,
        )
        # Create user with matching GitHub ID
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="12345",
        )

    def test_author_oneclick_vote_yes_records_ai_assisted_true(self):
        """Test that ?vote=yes records author_ai_assisted=True."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=yes"
        self.client.get(url)

        self.survey.refresh_from_db()
        self.assertTrue(self.survey.author_ai_assisted)

    def test_author_oneclick_vote_no_records_ai_assisted_false(self):
        """Test that ?vote=no records author_ai_assisted=False."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=no"
        self.client.get(url)

        self.survey.refresh_from_db()
        self.assertFalse(self.survey.author_ai_assisted)

    def test_author_oneclick_vote_sets_response_source_github(self):
        """Test that one-click vote sets response_source to 'github'."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=yes"
        self.client.get(url)

        self.survey.refresh_from_db()
        self.assertEqual(self.survey.author_response_source, "github")

    def test_author_oneclick_vote_sets_responded_at(self):
        """Test that one-click vote sets author_responded_at timestamp."""
        self.client.force_login(self.user)
        before = timezone.now()
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=yes"
        self.client.get(url)
        after = timezone.now()

        self.survey.refresh_from_db()
        self.assertIsNotNone(self.survey.author_responded_at)
        self.assertGreaterEqual(self.survey.author_responded_at, before)
        self.assertLessEqual(self.survey.author_responded_at, after)

    def test_author_oneclick_vote_redirects_to_complete_page(self):
        """Test that one-click vote redirects to complete page."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=yes"
        response = self.client.get(url)

        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_author_oneclick_without_vote_param_shows_form(self):
        """Test that without ?vote= param, the normal form is displayed."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI")

    def test_author_oneclick_invalid_vote_value_shows_form(self):
        """Test that invalid vote value shows the normal form."""
        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=invalid"
        response = self.client.get(url)

        # Should show form, not record vote
        self.assertEqual(response.status_code, 200)
        self.survey.refresh_from_db()
        self.assertIsNone(self.survey.author_ai_assisted)

    def test_author_oneclick_already_responded_ignores_vote(self):
        """Test that one-click vote is ignored if author already responded."""
        original_time = timezone.now() - timedelta(hours=2)
        self.survey.author_ai_assisted = True
        self.survey.author_responded_at = original_time
        self.survey.author_response_source = "slack"
        self.survey.save()

        self.client.force_login(self.user)
        url = reverse("web:survey_author", kwargs={"token": self.survey.token}) + "?vote=no"
        self.client.get(url)

        self.survey.refresh_from_db()
        # Should NOT have changed
        self.assertTrue(self.survey.author_ai_assisted)
        self.assertEqual(self.survey.author_response_source, "slack")


class TestOneClickReviewerVoting(TestCase):
    """Tests for one-click reviewer voting via ?vote= query parameter.

    One-click voting allows reviewers to vote quality directly from PR description
    links by appending ?vote=1, ?vote=2, or ?vote=3 to the survey URL.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from allauth.socialaccount.models import SocialAccount

        from apps.metrics.factories import PRReviewFactory, PullRequestFactory

        self.author = TeamMemberFactory(github_id="10000")
        self.reviewer = TeamMemberFactory(team=self.author.team, github_id="20001")

        # Create PR and survey
        self.pr = PullRequestFactory(team=self.author.team, author=self.author)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            pull_request=self.pr,
            author=self.author,
            token="oneclick-reviewer-token",
            token_expires_at=timezone.now() + timedelta(days=7),
        )

        # Create PR review for the reviewer
        PRReviewFactory(team=self.author.team, pull_request=self.pr, reviewer=self.reviewer)

        # Create user with matching GitHub ID
        self.user = CustomUser.objects.create_user(username="testuser", password="testpass123")
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="20001",
        )

    def test_reviewer_oneclick_vote_1_records_quality_rating(self):
        """Test that ?vote=1 records quality_rating=1."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=1"
        self.client.get(url)

        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.quality_rating, 1)

    def test_reviewer_oneclick_vote_2_records_quality_rating(self):
        """Test that ?vote=2 records quality_rating=2."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=2"
        self.client.get(url)

        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.quality_rating, 2)

    def test_reviewer_oneclick_vote_3_records_quality_rating(self):
        """Test that ?vote=3 records quality_rating=3."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=3"
        self.client.get(url)

        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNotNone(review)
        self.assertEqual(review.quality_rating, 3)

    def test_reviewer_oneclick_vote_sets_response_source_github(self):
        """Test that one-click vote sets response_source to 'github'."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=2"
        self.client.get(url)

        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertEqual(review.response_source, "github")

    def test_reviewer_oneclick_vote_sets_responded_at(self):
        """Test that one-click vote sets responded_at timestamp."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        before = timezone.now()
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=3"
        self.client.get(url)
        after = timezone.now()

        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNotNone(review.responded_at)
        self.assertGreaterEqual(review.responded_at, before)
        self.assertLessEqual(review.responded_at, after)

    def test_reviewer_oneclick_vote_does_not_set_ai_guess(self):
        """Test that one-click vote does NOT set ai_guess (quality only)."""
        from apps.metrics.models import PRSurveyReview

        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=2"
        self.client.get(url)

        review = PRSurveyReview.objects.filter(survey=self.survey, reviewer=self.reviewer).first()
        self.assertIsNone(review.ai_guess)

    def test_reviewer_oneclick_vote_redirects_to_complete_page(self):
        """Test that one-click vote redirects to complete page."""
        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=2"
        response = self.client.get(url)

        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertRedirects(response, expected_url, fetch_redirect_response=False)

    def test_reviewer_oneclick_without_vote_param_shows_form(self):
        """Test that without ?vote= param, the normal form is displayed."""
        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "quality")

    def test_reviewer_oneclick_invalid_vote_value_shows_form(self):
        """Test that invalid vote value shows the normal form."""
        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=invalid"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_reviewer_oneclick_vote_0_is_invalid_shows_form(self):
        """Test that ?vote=0 is invalid and shows form."""
        self.client.force_login(self.user)
        url = reverse("web:survey_reviewer", kwargs={"token": self.survey.token}) + "?vote=0"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
