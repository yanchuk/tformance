"""
Tests for survey_submit IDOR protection.

Verifies that survey_submit checks user identity before processing
author or reviewer submissions — preventing any logged-in user with
a valid token from submitting on behalf of someone else.
"""

from datetime import timedelta

from allauth.socialaccount.models import SocialAccount
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.metrics.factories import PRReviewFactory, PRSurveyFactory, PullRequestFactory, TeamMemberFactory
from apps.users.models import CustomUser


class TestSurveySubmitAuthorAuth(TestCase):
    """Tests that only the PR author can submit an author survey response."""

    def setUp(self):
        self.author = TeamMemberFactory(github_id="11111")
        self.pr = PullRequestFactory(team=self.author.team, author=self.author)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            pull_request=self.pr,
            author=self.author,
            token="author-auth-token",
            token_expires_at=timezone.now() + timedelta(days=7),
            author_ai_assisted=None,
        )
        self.url = reverse("web:survey_submit", kwargs={"token": self.survey.token})

    def test_unauthorized_user_cannot_submit_author_survey(self):
        """A logged-in user who is NOT the PR author gets 403."""
        stranger = CustomUser.objects.create_user(username="stranger", password="testpass123")
        SocialAccount.objects.create(user=stranger, provider="github", uid="99999")

        self.client.force_login(stranger)
        response = self.client.post(self.url, {"ai_assisted": "true"})

        self.assertEqual(response.status_code, 403)

    def test_authorized_author_can_submit_survey(self):
        """The actual PR author can submit and gets redirected to complete page."""
        author_user = CustomUser.objects.create_user(username="author", password="testpass123")
        SocialAccount.objects.create(user=author_user, provider="github", uid="11111")

        self.client.force_login(author_user)
        response = self.client.post(self.url, {"ai_assisted": "true"})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertEqual(response.url, expected_url)


class TestSurveySubmitReviewerAuth(TestCase):
    """Tests that only a PR reviewer can submit a reviewer survey response."""

    def setUp(self):
        self.author = TeamMemberFactory(github_id="22222")
        self.reviewer = TeamMemberFactory(team=self.author.team, github_id="33333")
        self.pr = PullRequestFactory(team=self.author.team, author=self.author)
        PRReviewFactory(team=self.author.team, pull_request=self.pr, reviewer=self.reviewer)
        self.survey = PRSurveyFactory(
            team=self.author.team,
            pull_request=self.pr,
            author=self.author,
            token="reviewer-auth-token",
            token_expires_at=timezone.now() + timedelta(days=7),
            author_ai_assisted=None,
        )
        self.url = reverse("web:survey_submit", kwargs={"token": self.survey.token})

    def test_unauthorized_user_cannot_submit_reviewer_survey(self):
        """A logged-in user who is NOT a PR reviewer gets 403."""
        stranger = CustomUser.objects.create_user(username="stranger", password="testpass123")
        SocialAccount.objects.create(user=stranger, provider="github", uid="99999")

        self.client.force_login(stranger)
        response = self.client.post(self.url, {"quality_rating": "3", "ai_guess": "true"})

        self.assertEqual(response.status_code, 403)

    def test_authorized_reviewer_can_submit_survey(self):
        """The actual PR reviewer can submit and gets redirected to complete page."""
        reviewer_user = CustomUser.objects.create_user(username="reviewer", password="testpass123")
        SocialAccount.objects.create(user=reviewer_user, provider="github", uid="33333")

        self.client.force_login(reviewer_user)
        response = self.client.post(self.url, {"quality_rating": "3", "ai_guess": "true"})

        self.assertEqual(response.status_code, 302)
        expected_url = reverse("web:survey_complete", kwargs={"token": self.survey.token})
        self.assertEqual(response.url, expected_url)
