"""Tests for weekly insights email feature."""

from datetime import date, timedelta

from django.core import mail
from django.test import TestCase, override_settings

from apps.metrics.factories import TeamFactory
from apps.metrics.models import DailyInsight
from apps.teams.models import Membership
from apps.teams.roles import ROLE_ADMIN, ROLE_MEMBER
from apps.users.models import CustomUser


def get_monday_of_current_week() -> date:
    """Return the Monday of the current week."""
    today = date.today()
    return today - timedelta(days=today.weekday())


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestGetLatestWeeklyInsight(TestCase):
    """Tests for get_latest_weekly_insight function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(name="Test Team")
        self.monday = get_monday_of_current_week()

    def test_get_latest_weekly_insight_returns_insight_when_exists(self):
        """Test that function returns insight when one exists for current week."""
        from apps.insights.services.weekly_email import get_latest_weekly_insight

        # Create a weekly insight for current week
        insight = DailyInsight.objects.create(
            team=self.team,
            date=self.monday,
            category="llm_insight",
            comparison_period="7",
            title="Weekly Summary",
            description="Your team had a great week.",
            metric_type="llm_dashboard_insight",
            metric_value={
                "headline": "AI adoption grew 15%",
                "detail": "Your team merged 25 PRs with AI assistance.",
            },
            priority="medium",
        )

        result = get_latest_weekly_insight(self.team)

        self.assertIsNotNone(result)
        self.assertEqual(result.pk, insight.pk)
        self.assertEqual(result.category, "llm_insight")
        self.assertEqual(result.comparison_period, "7")

    def test_get_latest_weekly_insight_returns_none_when_no_insight(self):
        """Test that function returns None when no weekly insight exists."""
        from apps.insights.services.weekly_email import get_latest_weekly_insight

        # No insights created for this team
        result = get_latest_weekly_insight(self.team)

        self.assertIsNone(result)

    def test_get_latest_weekly_insight_filters_by_team(self):
        """Test that function only returns insights for the specified team."""
        from apps.insights.services.weekly_email import get_latest_weekly_insight

        other_team = TeamFactory(name="Other Team")

        # Create insight for other team
        DailyInsight.objects.create(
            team=other_team,
            date=self.monday,
            category="llm_insight",
            comparison_period="7",
            title="Other Team Weekly",
            description="Other team summary.",
            metric_type="llm_dashboard_insight",
            metric_value={"headline": "Other team headline", "detail": "Other detail"},
            priority="medium",
        )

        # Create insight for our team
        our_insight = DailyInsight.objects.create(
            team=self.team,
            date=self.monday,
            category="llm_insight",
            comparison_period="7",
            title="Our Team Weekly",
            description="Our team summary.",
            metric_type="llm_dashboard_insight",
            metric_value={"headline": "Our headline", "detail": "Our detail"},
            priority="medium",
        )

        result = get_latest_weekly_insight(self.team)

        self.assertIsNotNone(result)
        self.assertEqual(result.pk, our_insight.pk)
        self.assertEqual(result.team, self.team)

    def test_get_latest_weekly_insight_ignores_old_dates(self):
        """Test that function ignores insights from previous weeks."""
        from apps.insights.services.weekly_email import get_latest_weekly_insight

        # Create insight for last week
        last_monday = self.monday - timedelta(days=7)
        DailyInsight.objects.create(
            team=self.team,
            date=last_monday,
            category="llm_insight",
            comparison_period="7",
            title="Last Week Summary",
            description="Last week was good.",
            metric_type="llm_dashboard_insight",
            metric_value={"headline": "Old headline", "detail": "Old detail"},
            priority="medium",
        )

        result = get_latest_weekly_insight(self.team)

        self.assertIsNone(result)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class TestSendWeeklyInsightEmail(TestCase):
    """Tests for send_weekly_insight_email function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory(name="Acme Corp")
        self.monday = get_monday_of_current_week()

        # Create an admin user with email
        self.admin_user = CustomUser.objects.create_user(
            username="admin@example.com",
            email="admin@example.com",
            password="testpassword123",
            first_name="Alice",
        )
        Membership.objects.create(team=self.team, user=self.admin_user, role=ROLE_ADMIN)

        # Create a weekly insight
        self.insight = DailyInsight.objects.create(
            team=self.team,
            date=self.monday,
            category="llm_insight",
            comparison_period="7",
            title="Weekly Summary",
            description="Your team had a productive week.",
            metric_type="llm_dashboard_insight",
            metric_value={
                "headline": "AI adoption grew 15%",
                "detail": "Your team merged 25 PRs with AI assistance this week.",
            },
            priority="medium",
        )

    def test_send_email_success_when_insight_exists(self):
        """Test that email is sent successfully when insight exists."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        result = send_weekly_insight_email(self.team)

        self.assertEqual(result["sent_to"], 1)
        self.assertIsNone(result["skipped_reason"])
        self.assertEqual(len(mail.outbox), 1)

    def test_send_email_returns_skipped_when_no_insight(self):
        """Test that function returns skipped reason when no insight exists."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        # Delete the insight
        self.insight.delete()

        result = send_weekly_insight_email(self.team)

        self.assertEqual(result["sent_to"], 0)
        self.assertEqual(result["skipped_reason"], "no_insight")
        self.assertEqual(len(mail.outbox), 0)

    def test_send_email_returns_skipped_when_no_admins_with_email(self):
        """Test that function returns skipped reason when no admins have email."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        # Remove email from admin
        self.admin_user.email = ""
        self.admin_user.save()

        result = send_weekly_insight_email(self.team)

        self.assertEqual(result["sent_to"], 0)
        self.assertEqual(result["skipped_reason"], "no_admin_emails")
        self.assertEqual(len(mail.outbox), 0)

    def test_email_subject_contains_headline(self):
        """Test that email subject contains the insight headline."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        send_weekly_insight_email(self.team)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Weekly Insight:", email.subject)
        self.assertIn("AI adoption grew 15%", email.subject)

    def test_email_body_contains_team_name_and_summary(self):
        """Test that email body contains team name and insight summary."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        send_weekly_insight_email(self.team)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Acme Corp", email.body)
        self.assertIn("Your team merged 25 PRs with AI assistance", email.body)

    def test_email_body_contains_dashboard_link(self):
        """Test that email body contains a link to the dashboard."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        send_weekly_insight_email(self.team)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("/app/", email.body)

    def test_multiple_admins_all_receive_email(self):
        """Test that all team admins with email receive the email."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        # Create second admin
        admin2 = CustomUser.objects.create_user(
            username="admin2@example.com",
            email="admin2@example.com",
            password="testpassword123",
            first_name="Bob",
        )
        Membership.objects.create(team=self.team, user=admin2, role=ROLE_ADMIN)

        # Create a member (should not receive email)
        member = CustomUser.objects.create_user(
            username="member@example.com",
            email="member@example.com",
            password="testpassword123",
            first_name="Charlie",
        )
        Membership.objects.create(team=self.team, user=member, role=ROLE_MEMBER)

        result = send_weekly_insight_email(self.team)

        self.assertEqual(result["sent_to"], 2)
        self.assertEqual(len(mail.outbox), 2)

        # Verify recipients (order may vary)
        recipients = {mail.outbox[0].to[0], mail.outbox[1].to[0]}
        self.assertEqual(recipients, {"admin@example.com", "admin2@example.com"})

    def test_email_greeting_uses_first_name(self):
        """Test that email greeting uses admin's first name."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        send_weekly_insight_email(self.team)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Hi Alice,", email.body)

    def test_email_greeting_fallback_when_no_first_name(self):
        """Test that email greeting falls back to 'there' when no first name."""
        from apps.insights.services.weekly_email import send_weekly_insight_email

        # Remove first name from admin
        self.admin_user.first_name = ""
        self.admin_user.save()

        send_weekly_insight_email(self.team)

        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Hi there,", email.body)
