"""Tests for welcome email notification service."""

from django.core import mail
from django.test import TestCase, override_settings

from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class WelcomeEmailTests(TestCase):
    """Tests for welcome email service."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="welcome@example.com",
            email="welcome@example.com",
            password="testpassword123",
            first_name="Alex",
        )
        self.team = TeamFactory(name="Test Company")
        self.team.members.add(self.user)

    def test_send_welcome_email_success(self):
        """Test that welcome email is sent successfully."""
        from apps.onboarding.services.notifications import send_welcome_email

        result = send_welcome_email(self.team, self.user)

        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)

    def test_welcome_email_has_correct_subject(self):
        """Test that welcome email has appropriate subject line."""
        from apps.onboarding.services.notifications import send_welcome_email

        send_welcome_email(self.team, self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Welcome", mail.outbox[0].subject)

    def test_welcome_email_addresses_user_by_name(self):
        """Test that welcome email addresses user by first name."""
        from apps.onboarding.services.notifications import send_welcome_email

        send_welcome_email(self.team, self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Alex", mail.outbox[0].body)

    def test_welcome_email_includes_team_name(self):
        """Test that welcome email includes the team name."""
        from apps.onboarding.services.notifications import send_welcome_email

        send_welcome_email(self.team, self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Test Company", mail.outbox[0].body)

    def test_welcome_email_sent_to_correct_recipient(self):
        """Test that welcome email is sent to the user's email."""
        from apps.onboarding.services.notifications import send_welcome_email

        send_welcome_email(self.team, self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["welcome@example.com"])

    def test_welcome_email_fallback_greeting_when_no_first_name(self):
        """Test that email uses 'there' when user has no first name."""
        from apps.onboarding.services.notifications import send_welcome_email

        self.user.first_name = ""
        self.user.save()

        send_welcome_email(self.team, self.user)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("there", mail.outbox[0].body)

    def test_welcome_email_returns_false_when_no_email(self):
        """Test that welcome email returns False when user has no email."""
        from apps.onboarding.services.notifications import send_welcome_email

        self.user.email = ""
        self.user.save()

        result = send_welcome_email(self.team, self.user)

        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    def test_welcome_email_includes_dashboard_link(self):
        """Test that welcome email includes link to dashboard."""
        from apps.onboarding.services.notifications import send_welcome_email

        send_welcome_email(self.team, self.user)

        self.assertEqual(len(mail.outbox), 1)
        # Check that email contains a link to the team dashboard
        self.assertIn(self.team.slug, mail.outbox[0].body)
