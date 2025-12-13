"""Tests for PRSurvey token-related fields."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import PRSurveyFactory, PullRequestFactory, TeamFactory, TeamMemberFactory
from apps.metrics.models import PRSurvey
from apps.metrics.services import survey_tokens


class TestPRSurveyTokenFields(TestCase):
    """Tests for PRSurvey token, token_expires_at, and github_comment_id fields."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.pull_request = PullRequestFactory(team=self.team, author=self.member)

    def test_token_field_exists(self):
        """Test that PRSurvey has a token field."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # Should be able to set and retrieve token
        survey.token = "abc123xyz789"
        survey.save()
        survey.refresh_from_db()

        self.assertEqual(survey.token, "abc123xyz789")

    def test_token_field_max_length(self):
        """Test that token field has max_length of 64."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # 64 characters should work
        valid_token = "a" * 64
        survey.token = valid_token
        survey.save()
        survey.refresh_from_db()
        self.assertEqual(survey.token, valid_token)

        # 65 characters should fail validation
        invalid_token = "a" * 65
        survey.token = invalid_token
        with self.assertRaises(ValidationError):
            survey.full_clean()

    def test_token_field_is_unique(self):
        """Test that token field is unique across all surveys."""
        survey1 = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)
        survey1.token = "unique_token_123"
        survey1.save()

        # Create a second survey
        pr2 = PullRequestFactory(team=self.team, author=self.member)
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author=self.member)

        # Attempting to use the same token should fail
        survey2.token = "unique_token_123"
        with self.assertRaises(IntegrityError):
            survey2.save()

    def test_token_field_is_indexed(self):
        """Test that token field has a database index for efficient lookups."""
        # Check that the field has db_index=True
        token_field = PRSurvey._meta.get_field("token")
        self.assertTrue(token_field.db_index, "Token field should have db_index=True for efficient lookups")

    def test_token_expires_at_field_exists(self):
        """Test that PRSurvey has a token_expires_at field."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # Should be able to set and retrieve token_expires_at
        expiry_time = timezone.now() + timedelta(days=7)
        survey.token_expires_at = expiry_time
        survey.save()
        survey.refresh_from_db()

        # Compare timestamps (allowing for microsecond differences)
        self.assertAlmostEqual(
            survey.token_expires_at.timestamp(), expiry_time.timestamp(), delta=1, msg="Token expiry should be set"
        )

    def test_token_expires_at_defaults_to_7_days(self):
        """Test that token_expires_at defaults to 7 days from creation."""
        before_creation = timezone.now()
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)
        after_creation = timezone.now()

        # The default should be approximately 7 days from creation time
        expected_min = before_creation + timedelta(days=7)
        expected_max = after_creation + timedelta(days=7)

        self.assertIsNotNone(survey.token_expires_at, "token_expires_at should have a default value")
        self.assertGreaterEqual(
            survey.token_expires_at, expected_min, "token_expires_at should be at least 7 days from creation"
        )
        self.assertLessEqual(
            survey.token_expires_at, expected_max, "token_expires_at should be at most 7 days from creation"
        )

    def test_token_can_be_checked_for_expiry(self):
        """Test that we can check if a token is expired."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # Set token to expire in the past
        survey.token_expires_at = timezone.now() - timedelta(days=1)
        survey.save()
        survey.refresh_from_db()

        self.assertTrue(survey.is_token_expired(), "Token should be expired")

        # Set token to expire in the future
        survey.token_expires_at = timezone.now() + timedelta(days=1)
        survey.save()
        survey.refresh_from_db()

        self.assertFalse(survey.is_token_expired(), "Token should not be expired")

    def test_is_token_expired_when_no_expiry_set(self):
        """Test that tokens with no expiry date are considered expired."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)
        survey.token_expires_at = None
        survey.save()

        self.assertTrue(survey.is_token_expired(), "Token with no expiry should be considered expired")

    def test_github_comment_id_field_exists(self):
        """Test that PRSurvey has a github_comment_id field."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # Should be able to set and retrieve github_comment_id
        survey.github_comment_id = 123456789
        survey.save()
        survey.refresh_from_db()

        self.assertEqual(survey.github_comment_id, 123456789)

    def test_github_comment_id_can_be_null(self):
        """Test that github_comment_id can be null (for surveys not posted to GitHub)."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # Should be able to create without github_comment_id
        survey.github_comment_id = None
        survey.save()
        survey.refresh_from_db()

        self.assertIsNone(survey.github_comment_id, "github_comment_id should allow null values")

    def test_github_comment_id_can_store_large_integers(self):
        """Test that github_comment_id can store large GitHub comment IDs (BigIntegerField)."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)

        # GitHub comment IDs can be large - use value within PostgreSQL bigint range
        # Max bigint: 9,223,372,036,854,775,807
        large_comment_id = 1234567890123456789
        survey.github_comment_id = large_comment_id
        survey.save()
        survey.refresh_from_db()

        self.assertEqual(survey.github_comment_id, large_comment_id)

    def test_token_lookup_by_token(self):
        """Test that we can efficiently look up surveys by token."""
        survey = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)
        survey.token = "lookup_test_token"
        survey.save()

        # Should be able to find survey by token
        found_survey = PRSurvey.objects.get(token="lookup_test_token")
        self.assertEqual(found_survey.pk, survey.pk)
        self.assertEqual(found_survey.token, "lookup_test_token")

    def test_multiple_surveys_can_have_null_github_comment_id(self):
        """Test that multiple surveys can have null github_comment_id (not unique)."""
        survey1 = PRSurveyFactory(team=self.team, pull_request=self.pull_request, author=self.member)
        survey1.github_comment_id = None
        survey1.save()

        pr2 = PullRequestFactory(team=self.team, author=self.member)
        survey2 = PRSurveyFactory(team=self.team, pull_request=pr2, author=self.member)
        survey2.github_comment_id = None
        survey2.save()

        # Both should save successfully
        self.assertIsNone(survey1.github_comment_id)
        self.assertIsNone(survey2.github_comment_id)


class TestTokenGenerationService(TestCase):
    """Tests for token generation service."""

    def test_generate_survey_token_returns_url_safe_string(self):
        """Test that generate_survey_token returns a URL-safe string."""
        token = survey_tokens.generate_survey_token()

        # Token should be a string
        self.assertIsInstance(token, str)

        # Token should only contain URL-safe characters (a-z, A-Z, 0-9, -, _)
        # base64url uses: A-Z, a-z, 0-9, -, _
        import re

        self.assertIsNotNone(re.match(r"^[A-Za-z0-9_-]+$", token), "Token should only contain URL-safe characters")

    def test_generate_survey_token_returns_correct_length(self):
        """Test that generate_survey_token returns a token of correct length."""
        token = survey_tokens.generate_survey_token()

        # 32 bytes encoded as base64url = 43 characters (no padding with base64.urlsafe_b64encode)
        # Formula: ceil(bytes * 8 / 6) = ceil(32 * 8 / 6) = ceil(42.67) = 43
        self.assertEqual(len(token), 43, "Token should be 43 characters (32 bytes base64url encoded)")

    def test_generate_survey_token_generates_unique_tokens(self):
        """Test that generate_survey_token generates unique tokens on each call."""
        tokens = set()

        # Generate 100 tokens and verify they are all unique
        for _ in range(100):
            token = survey_tokens.generate_survey_token()
            self.assertNotIn(token, tokens, "Each token should be unique")
            tokens.add(token)

        # All 100 should be unique
        self.assertEqual(len(tokens), 100)

    def test_set_survey_token_sets_token_on_survey(self):
        """Test that set_survey_token sets a token on the survey."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)
        survey = PRSurveyFactory(team=team, pull_request=pr, author=member, token=None)

        survey_tokens.set_survey_token(survey)

        survey.refresh_from_db()
        self.assertIsNotNone(survey.token, "Token should be set on survey")
        self.assertEqual(len(survey.token), 43, "Token should be 43 characters")

    def test_set_survey_token_sets_default_expiry(self):
        """Test that set_survey_token sets default expiry to 7 days from now."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)
        survey = PRSurveyFactory(team=team, pull_request=pr, author=member, token_expires_at=None)

        before = timezone.now()
        survey_tokens.set_survey_token(survey)
        after = timezone.now()

        survey.refresh_from_db()
        self.assertIsNotNone(survey.token_expires_at, "Token expiry should be set")

        # Should be approximately 7 days from now
        expected_min = before + timedelta(days=7)
        expected_max = after + timedelta(days=7)

        self.assertGreaterEqual(
            survey.token_expires_at, expected_min, "Token expiry should be at least 7 days from now"
        )
        self.assertLessEqual(survey.token_expires_at, expected_max, "Token expiry should be at most 7 days from now")

    def test_set_survey_token_accepts_custom_expiry_days(self):
        """Test that set_survey_token accepts custom expiry days."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)
        survey = PRSurveyFactory(team=team, pull_request=pr, author=member, token_expires_at=None)

        before = timezone.now()
        survey_tokens.set_survey_token(survey, expiry_days=14)
        after = timezone.now()

        survey.refresh_from_db()

        # Should be approximately 14 days from now
        expected_min = before + timedelta(days=14)
        expected_max = after + timedelta(days=14)

        self.assertGreaterEqual(
            survey.token_expires_at, expected_min, "Token expiry should be at least 14 days from now"
        )
        self.assertLessEqual(survey.token_expires_at, expected_max, "Token expiry should be at most 14 days from now")

    def test_set_survey_token_saves_survey(self):
        """Test that set_survey_token saves the survey to the database."""
        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)
        survey = PRSurveyFactory(team=team, pull_request=pr, author=member, token=None, token_expires_at=None)

        original_updated_at = survey.updated_at

        # Call set_survey_token
        survey_tokens.set_survey_token(survey)

        # Refresh from DB to verify it was saved
        survey.refresh_from_db()

        # updated_at should have changed
        self.assertNotEqual(survey.updated_at, original_updated_at, "Survey should have been saved")


class TestCreatePRSurveyIntegration(TestCase):
    """Tests for create_pr_survey integration with token generation."""

    def test_create_pr_survey_sets_token(self):
        """Test that create_pr_survey automatically sets a token."""
        from apps.metrics.services import survey_service

        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)

        survey = survey_service.create_pr_survey(pr)

        self.assertIsNotNone(survey.token, "create_pr_survey should set a token")
        self.assertEqual(len(survey.token), 43, "Token should be 43 characters")

    def test_create_pr_survey_sets_token_expires_at(self):
        """Test that create_pr_survey automatically sets token_expires_at."""
        from apps.metrics.services import survey_service

        team = TeamFactory()
        member = TeamMemberFactory(team=team)
        pr = PullRequestFactory(team=team, author=member)

        before = timezone.now()
        survey = survey_service.create_pr_survey(pr)
        after = timezone.now()

        self.assertIsNotNone(survey.token_expires_at, "create_pr_survey should set token_expires_at")

        # Should be approximately 7 days from creation
        expected_min = before + timedelta(days=7)
        expected_max = after + timedelta(days=7)

        self.assertGreaterEqual(survey.token_expires_at, expected_min)
        self.assertLessEqual(survey.token_expires_at, expected_max)

    def test_create_pr_survey_generates_unique_tokens(self):
        """Test that create_pr_survey generates unique tokens for different surveys."""
        from apps.metrics.services import survey_service

        team = TeamFactory()
        member = TeamMemberFactory(team=team)

        tokens = set()
        for i in range(10):
            pr = PullRequestFactory(team=team, author=member, github_pr_id=i + 1000)
            survey = survey_service.create_pr_survey(pr)
            self.assertNotIn(survey.token, tokens, "Each survey should have a unique token")
            tokens.add(survey.token)

        # All 10 should be unique
        self.assertEqual(len(tokens), 10)


class TestTokenValidationService(TestCase):
    """Tests for token validation service."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)
        self.pr = PullRequestFactory(team=self.team, author=self.member)

    def test_validate_survey_token_returns_survey_for_valid_token(self):
        """Test that validate_survey_token returns the PRSurvey for a valid token."""
        survey = PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.member,
            token="valid_token_123",
            token_expires_at=timezone.now() + timedelta(days=1),
        )

        result = survey_tokens.validate_survey_token("valid_token_123")

        self.assertEqual(result, survey, "Should return the survey for valid token")

    def test_validate_survey_token_raises_invalid_token_error_for_nonexistent_token(self):
        """Test that validate_survey_token raises InvalidTokenError for nonexistent token."""
        with self.assertRaises(survey_tokens.InvalidTokenError):
            survey_tokens.validate_survey_token("nonexistent_token")

    def test_validate_survey_token_raises_invalid_token_error_for_none(self):
        """Test that validate_survey_token raises InvalidTokenError for None token."""
        with self.assertRaises(survey_tokens.InvalidTokenError):
            survey_tokens.validate_survey_token(None)

    def test_validate_survey_token_raises_invalid_token_error_for_empty_string(self):
        """Test that validate_survey_token raises InvalidTokenError for empty string."""
        with self.assertRaises(survey_tokens.InvalidTokenError):
            survey_tokens.validate_survey_token("")

    def test_validate_survey_token_raises_expired_token_error_for_expired_token(self):
        """Test that validate_survey_token raises ExpiredTokenError for expired token."""
        PRSurveyFactory(
            team=self.team,
            pull_request=self.pr,
            author=self.member,
            token="expired_token_123",
            token_expires_at=timezone.now() - timedelta(days=1),
        )

        with self.assertRaises(survey_tokens.ExpiredTokenError):
            survey_tokens.validate_survey_token("expired_token_123")

    def test_invalid_token_error_is_exception(self):
        """Test that InvalidTokenError is a proper exception class."""
        self.assertTrue(issubclass(survey_tokens.InvalidTokenError, Exception))

    def test_expired_token_error_is_exception(self):
        """Test that ExpiredTokenError is a proper exception class."""
        self.assertTrue(issubclass(survey_tokens.ExpiredTokenError, Exception))

    def test_invalid_token_error_can_be_raised(self):
        """Test that InvalidTokenError can be raised with a message."""
        with self.assertRaises(survey_tokens.InvalidTokenError) as context:
            raise survey_tokens.InvalidTokenError("Token not found")

        self.assertEqual(str(context.exception), "Token not found")

    def test_expired_token_error_can_be_raised(self):
        """Test that ExpiredTokenError can be raised with a message."""
        with self.assertRaises(survey_tokens.ExpiredTokenError) as context:
            raise survey_tokens.ExpiredTokenError("Token has expired")

        self.assertEqual(str(context.exception), "Token has expired")
