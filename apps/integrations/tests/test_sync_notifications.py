"""Tests for sync completion email notification service."""

from unittest.mock import patch

from django.test import TestCase

from apps.integrations.factories import TrackedRepositoryFactory, UserFactory
from apps.integrations.services.sync_notifications import send_sync_complete_notification


class TestSendSyncCompleteNotification(TestCase):
    """Tests for send_sync_complete_notification service function."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.user = UserFactory(email="developer@example.com")
        self.tracked_repo = TrackedRepositoryFactory()
        # Set the connected_by user on the credential
        self.tracked_repo.integration.credential.connected_by = self.user
        self.tracked_repo.integration.credential.save()

        self.stats = {
            "prs": 10,
            "reviews": 25,
            "commits": 150,
        }

    @patch("apps.integrations.services.sync_notifications.send_mail")
    def test_send_notification_sends_email(self, mock_send_mail):
        """Test that send_mail is called with correct subject and recipient."""
        send_sync_complete_notification(self.tracked_repo, self.stats)

        # Verify send_mail was called
        mock_send_mail.assert_called_once()

        # Verify correct subject
        call_kwargs = mock_send_mail.call_args[1]
        self.assertIn("subject", call_kwargs)
        self.assertIn(self.tracked_repo.full_name, call_kwargs["subject"])
        self.assertIn("ready", call_kwargs["subject"].lower())

        # Verify correct recipient
        self.assertEqual(call_kwargs["recipient_list"], [self.user.email])

    @patch("apps.integrations.services.sync_notifications.send_mail")
    def test_send_notification_returns_true_on_success(self, mock_send_mail):
        """Test that the function returns True when email is sent successfully."""
        result = send_sync_complete_notification(self.tracked_repo, self.stats)

        self.assertTrue(result)
        mock_send_mail.assert_called_once()

    def test_send_notification_returns_false_when_no_user(self):
        """Test that the function returns False if connected_by is None."""
        # Set connected_by to None
        self.tracked_repo.integration.credential.connected_by = None
        self.tracked_repo.integration.credential.save()

        result = send_sync_complete_notification(self.tracked_repo, self.stats)

        self.assertFalse(result)

    @patch("apps.integrations.services.sync_notifications.send_mail")
    def test_send_notification_returns_false_when_no_email(self, mock_send_mail):
        """Test that the function returns False if user has no email."""
        # Create user without email
        user_no_email = UserFactory(email="")
        self.tracked_repo.integration.credential.connected_by = user_no_email
        self.tracked_repo.integration.credential.save()

        result = send_sync_complete_notification(self.tracked_repo, self.stats)

        self.assertFalse(result)
        mock_send_mail.assert_not_called()

    @patch("apps.integrations.services.sync_notifications.send_mail")
    def test_send_notification_includes_stats_in_context(self, mock_send_mail):
        """Test that email context includes sync stats."""
        send_sync_complete_notification(self.tracked_repo, self.stats)

        # Verify send_mail was called
        mock_send_mail.assert_called_once()

        # Get the context by checking if the rendered message contains stats
        call_kwargs = mock_send_mail.call_args[1]

        # Check that message (plaintext) was provided
        self.assertIn("message", call_kwargs)
        message = call_kwargs["message"]

        # Verify stats appear in the message
        self.assertIn(str(self.stats["prs"]), message)
        self.assertIn(str(self.stats["reviews"]), message)
        self.assertIn(str(self.stats["commits"]), message)
        self.assertIn(self.tracked_repo.full_name, message)
