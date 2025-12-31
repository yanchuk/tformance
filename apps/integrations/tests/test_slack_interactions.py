"""Tests for Slack interactions webhook.

Handles button clicks from Slack surveys (author and reviewer responses).
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch
from urllib.parse import urlencode

from django.test import Client, TestCase, override_settings

from apps.integrations.services.slack_surveys import (
    ACTION_AI_GUESS_NO,
    ACTION_AI_GUESS_YES,
    ACTION_AUTHOR_AI_NO,
    ACTION_AUTHOR_AI_YES,
    ACTION_QUALITY_1,
    ACTION_QUALITY_2,
    ACTION_QUALITY_3,
)
from apps.metrics.factories import PRSurveyFactory, PRSurveyReviewFactory, TeamFactory


class TestSlackInteractionsWebhook(TestCase):
    """Tests for Slack interactions webhook endpoint."""

    def setUp(self):
        """Set up test client and test data."""
        self.client = Client()
        self.team = TeamFactory()
        self.webhook_url = "/integrations/webhooks/slack/interactions/"
        self.signing_secret = "test_signing_secret_12345"

    def _create_slack_signature(self, timestamp: str, body: str) -> str:
        """Create valid Slack signature for testing.

        Args:
            timestamp: Unix timestamp as string
            body: Request body

        Returns:
            Slack signature in format "v0=<hex>"
        """
        sig_basestring = f"v0:{timestamp}:{body}"
        signature = (
            "v0="
            + hmac.new(
                self.signing_secret.encode(),
                sig_basestring.encode(),
                hashlib.sha256,
            ).hexdigest()
        )
        return signature

    def _make_request_with_signature(self, payload: dict) -> tuple:
        """Make POST request with valid Slack signature.

        Args:
            payload: Payload dict to send

        Returns:
            Tuple of (response, timestamp, signature)
        """
        timestamp = str(int(time.time()))
        body = urlencode({"payload": json.dumps(payload)})
        signature = self._create_slack_signature(timestamp, body)

        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
            HTTP_X_SLACK_SIGNATURE=signature,
        )

        return response, timestamp, signature

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_endpoint_accepts_post(self):
        """Test that endpoint accepts POST requests."""
        payload = {"type": "block_actions", "actions": []}
        response, _, _ = self._make_request_with_signature(payload)

        # Should return 200 (even for empty actions)
        self.assertEqual(response.status_code, 200)

    def test_endpoint_rejects_get_with_405(self):
        """Test that endpoint rejects GET requests with 405."""
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, 405)

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_signature_verification_passes_for_valid_signature(self):
        """Test that signature verification passes for valid signature."""
        payload = {"type": "block_actions", "actions": []}
        response, _, _ = self._make_request_with_signature(payload)

        # Should not return 403 (forbidden)
        self.assertNotEqual(response.status_code, 403)

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_signature_verification_fails_for_invalid_signature(self):
        """Test that signature verification fails for invalid signature (403)."""
        timestamp = str(int(time.time()))
        body = urlencode({"payload": json.dumps({"type": "block_actions", "actions": []})})
        invalid_signature = "v0=invalid_signature_hash_12345"

        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
            HTTP_X_SLACK_SIGNATURE=invalid_signature,
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_payload_parsing_works_correctly(self):
        """Test that payload is parsed correctly from form data."""
        survey = PRSurveyFactory(team=self.team, author_ai_assisted=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_AUTHOR_AI_YES,
                    "value": str(survey.id),
                }
            ],
        }

        with patch("apps.integrations.webhooks.slack_interactions.record_author_response") as mock_record:
            response, _, _ = self._make_request_with_signature(payload)

            # Should call handler with correct survey_id
            mock_record.assert_called_once()
            args = mock_record.call_args[0]
            self.assertEqual(args[0].id, survey.id)
            self.assertTrue(args[1])  # ai_assisted=True

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_author_response")
    def test_action_author_ai_yes_handled_correctly(self, mock_record):
        """Test that ACTION_AUTHOR_AI_YES is handled correctly."""
        survey = PRSurveyFactory(team=self.team, author_ai_assisted=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_AUTHOR_AI_YES,
                    "value": str(survey.id),
                }
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertEqual(args[0].id, survey.id)
        self.assertTrue(args[1])  # ai_assisted=True

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_author_response")
    def test_action_author_ai_no_handled_correctly(self, mock_record):
        """Test that ACTION_AUTHOR_AI_NO is handled correctly."""
        survey = PRSurveyFactory(team=self.team, author_ai_assisted=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_AUTHOR_AI_NO,
                    "value": str(survey.id),
                }
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertEqual(args[0].id, survey.id)
        self.assertFalse(args[1])  # ai_assisted=False

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_reviewer_response")
    def test_action_quality_1_handled_correctly(self, mock_record):
        """Test that ACTION_QUALITY_1 is handled correctly."""
        survey_review = PRSurveyReviewFactory(team=self.team, quality_rating=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_1,
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_YES,
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertEqual(args[0].id, survey_review.id)
        self.assertEqual(args[1], 1)  # quality=1
        self.assertTrue(args[2])  # ai_guess=True

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_reviewer_response")
    def test_action_quality_2_handled_correctly(self, mock_record):
        """Test that ACTION_QUALITY_2 is handled correctly."""
        survey_review = PRSurveyReviewFactory(team=self.team, quality_rating=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_2,
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_NO,
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertEqual(args[0].id, survey_review.id)
        self.assertEqual(args[1], 2)  # quality=2
        self.assertFalse(args[2])  # ai_guess=False

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_reviewer_response")
    def test_action_quality_3_handled_correctly(self, mock_record):
        """Test that ACTION_QUALITY_3 is handled correctly."""
        survey_review = PRSurveyReviewFactory(team=self.team, quality_rating=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_3,
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_YES,
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertEqual(args[0].id, survey_review.id)
        self.assertEqual(args[1], 3)  # quality=3
        self.assertTrue(args[2])  # ai_guess=True

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_reviewer_response")
    def test_action_ai_guess_yes_handled_correctly(self, mock_record):
        """Test that ACTION_AI_GUESS_YES is handled correctly."""
        survey_review = PRSurveyReviewFactory(team=self.team, quality_rating=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_2,
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_YES,
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertTrue(args[2])  # ai_guess=True

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_reviewer_response")
    def test_action_ai_guess_no_handled_correctly(self, mock_record):
        """Test that ACTION_AI_GUESS_NO is handled correctly."""
        survey_review = PRSurveyReviewFactory(team=self.team, quality_rating=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_1,
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_NO,
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        args = mock_record.call_args[0]
        self.assertFalse(args[2])  # ai_guess=False

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_author_response")
    def test_unknown_action_id_ignored_no_error(self, mock_record):
        """Test that unknown action_id is ignored (no error)."""
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": "unknown_action_xyz",
                    "value": "12345",
                }
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        # Should return 200 and not call any handlers
        self.assertEqual(response.status_code, 200)
        mock_record.assert_not_called()

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_duplicate_author_response_ignored(self):
        """Test that duplicate author response is ignored."""
        # Create survey with author already responded
        survey = PRSurveyFactory(team=self.team, author_ai_assisted=True)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_AUTHOR_AI_NO,  # Try to change answer
                    "value": str(survey.id),
                }
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        # Should return 200 but not change the answer
        self.assertEqual(response.status_code, 200)
        survey.refresh_from_db()
        self.assertTrue(survey.author_ai_assisted)  # Still True (unchanged)

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_duplicate_reviewer_response_ignored(self):
        """Test that duplicate reviewer response is ignored."""
        # Create survey review with reviewer already responded
        survey_review = PRSurveyReviewFactory(
            team=self.team,
            quality_rating=3,
            ai_guess=True,
        )
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_1,  # Try to change answer
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_NO,  # Try to change answer
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        # Should return 200 but not change the answer
        self.assertEqual(response.status_code, 200)
        survey_review.refresh_from_db()
        self.assertEqual(survey_review.quality_rating, 3)  # Still 3 (unchanged)
        self.assertTrue(survey_review.ai_guess)  # Still True (unchanged)

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_returns_200_with_empty_body(self):
        """Test that endpoint returns 200 with empty body."""
        payload = {"type": "block_actions", "actions": []}
        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_author_response")
    def test_author_response_sets_response_source_slack(self, mock_record):
        """Test that author response sets response_source='slack'."""
        survey = PRSurveyFactory(team=self.team, author_ai_assisted=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_AUTHOR_AI_YES,
                    "value": str(survey.id),
                }
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        # Verify response_source='slack' is passed
        kwargs = mock_record.call_args[1]
        self.assertEqual(kwargs.get("response_source"), "slack")

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    @patch("apps.integrations.webhooks.slack_interactions.record_reviewer_response")
    def test_reviewer_response_sets_response_source_slack(self, mock_record):
        """Test that reviewer response sets response_source='slack'."""
        survey_review = PRSurveyReviewFactory(team=self.team, quality_rating=None)
        payload = {
            "type": "block_actions",
            "actions": [
                {
                    "action_id": ACTION_QUALITY_2,
                    "value": str(survey_review.id),
                },
                {
                    "action_id": ACTION_AI_GUESS_YES,
                    "value": str(survey_review.id),
                },
            ],
        }

        response, _, _ = self._make_request_with_signature(payload)

        self.assertEqual(response.status_code, 200)
        mock_record.assert_called_once()
        # Verify response_source='slack' is passed
        kwargs = mock_record.call_args[1]
        self.assertEqual(kwargs.get("response_source"), "slack")

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_handles_malformed_json_payload_gracefully(self):
        """Test that endpoint handles malformed JSON payload without crashing."""
        # Arrange - Create a request with valid signature but invalid JSON payload
        timestamp = str(int(time.time()))
        body = urlencode({"payload": "not valid json {{{"})
        signature = self._create_slack_signature(timestamp, body)

        # Act
        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_SLACK_SIGNATURE=signature,
            HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
        )

        # Assert - Should return 400 Bad Request, not 500 Server Error
        self.assertEqual(response.status_code, 400)

    @override_settings(SLACK_SIGNING_SECRET="test_signing_secret_12345")
    def test_handles_empty_json_payload_gracefully(self):
        """Test that endpoint handles empty/missing payload parameter gracefully.

        When payload parameter is empty or missing, it defaults to '{}' which is valid JSON.
        This is intentional - an empty payload with no actions just returns 200.
        """
        # Arrange - Create a request with valid signature but empty payload
        timestamp = str(int(time.time()))
        body = urlencode({"payload": ""})
        signature = self._create_slack_signature(timestamp, body)

        # Act
        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/x-www-form-urlencoded",
            HTTP_X_SLACK_SIGNATURE=signature,
            HTTP_X_SLACK_REQUEST_TIMESTAMP=timestamp,
        )

        # Assert - Empty payload defaults to {} which is valid, returns 200
        self.assertEqual(response.status_code, 200)
