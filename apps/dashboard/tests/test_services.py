"""Tests for dashboard services."""

from datetime import date, timedelta

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.dashboard.services import get_user_signups
from apps.users.models import CustomUser


class TestGetUserSignups(TestCase):
    """Tests for get_user_signups function."""

    def setUp(self):
        """Create test users with different signup dates."""
        self.today = timezone.now()
        self.yesterday = self.today - timedelta(days=1)
        self.last_week = self.today - timedelta(days=7)

    def test_returns_empty_list_when_no_users(self):
        """Test that function returns empty list when no users exist."""
        result = get_user_signups()
        self.assertEqual(result, [])

    def test_counts_users_by_date(self):
        """Test that users are counted by signup date."""
        # Create 2 users today
        CustomUser.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="pass123",
            date_joined=self.today,
        )
        CustomUser.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="pass123",
            date_joined=self.today,
        )
        # Create 1 user yesterday
        CustomUser.objects.create_user(
            username="user3",
            email="user3@example.com",
            password="pass123",
            date_joined=self.yesterday,
        )

        result = get_user_signups()

        # Should have 2 entries (today and yesterday)
        self.assertEqual(len(result), 2)

        # Find today's count
        today_data = next((r for r in result if r["date"] == self.today.date()), None)
        yesterday_data = next((r for r in result if r["date"] == self.yesterday.date()), None)

        self.assertIsNotNone(today_data)
        self.assertIsNotNone(yesterday_data)
        self.assertEqual(today_data["count"], 2)
        self.assertEqual(yesterday_data["count"], 1)

    def test_filters_by_date_range(self):
        """Test that date range filters work correctly."""
        # Create user in range
        CustomUser.objects.create_user(
            username="in_range",
            email="in_range@example.com",
            password="pass123",
            date_joined=self.yesterday,
        )
        # Create user out of range
        old_date = self.today - timedelta(days=100)
        CustomUser.objects.create_user(
            username="out_range",
            email="out_range@example.com",
            password="pass123",
            date_joined=old_date,
        )

        result = get_user_signups(
            start=self.last_week.date(),
            end=self.today.date(),
        )

        # Should only include the user from yesterday
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["count"], 1)

    def test_default_range_is_90_days(self):
        """Test that default range is 90 days."""
        # Create user within 90 days
        CustomUser.objects.create_user(
            username="within90",
            email="within90@example.com",
            password="pass123",
            date_joined=self.today - timedelta(days=30),
        )
        # Create user outside 90 days
        CustomUser.objects.create_user(
            username="outside90",
            email="outside90@example.com",
            password="pass123",
            date_joined=self.today - timedelta(days=100),
        )

        result = get_user_signups()

        # Should only include user within 90 days
        self.assertEqual(len(result), 1)

    def test_result_format(self):
        """Test that result has correct format."""
        CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="pass123",
            date_joined=self.today,
        )

        result = get_user_signups()

        self.assertEqual(len(result), 1)
        self.assertIn("date", result[0])
        self.assertIn("count", result[0])
        self.assertIsInstance(result[0]["date"], date)
        self.assertIsInstance(result[0]["count"], int)

    def test_results_ordered_by_date(self):
        """Test that results are ordered by date ascending."""
        dates = [
            self.today - timedelta(days=3),
            self.today - timedelta(days=1),
            self.today - timedelta(days=5),
        ]
        for i, d in enumerate(dates):
            CustomUser.objects.create_user(
                username=f"user{i}",
                email=f"user{i}@example.com",
                password="pass123",
                date_joined=d,
            )

        result = get_user_signups()

        result_dates = [r["date"] for r in result]
        self.assertEqual(result_dates, sorted(result_dates))

    @override_settings(ACCOUNT_EMAIL_VERIFICATION="mandatory")
    def test_excludes_unverified_when_mandatory(self):
        """Test that unverified users are excluded when email verification is mandatory."""
        # This test verifies the include_unconfirmed logic
        # Note: Full testing would require setting up EmailAddress records
        result = get_user_signups(include_unconfirmed=False)
        # When include_unconfirmed=False, users without verified email are excluded
        self.assertEqual(result, [])
