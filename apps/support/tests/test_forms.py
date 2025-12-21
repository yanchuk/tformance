"""Tests for support app forms."""

from django.test import TestCase

from apps.support.forms import HijackUserForm
from apps.users.models import CustomUser


class TestHijackUserForm(TestCase):
    """Tests for HijackUserForm."""

    def setUp(self):
        """Create test users."""
        self.user1 = CustomUser.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="testpass123",
        )
        self.user2 = CustomUser.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="testpass123",
        )

    def test_form_has_user_pk_field(self):
        """Test that form has user_pk field."""
        form = HijackUserForm()
        self.assertIn("user_pk", form.fields)

    def test_form_user_pk_queryset_contains_users(self):
        """Test that user_pk queryset contains created users."""
        form = HijackUserForm()
        queryset = form.fields["user_pk"].queryset
        self.assertIn(self.user1, queryset)
        self.assertIn(self.user2, queryset)

    def test_form_valid_with_existing_user(self):
        """Test that form is valid when selecting existing user."""
        form = HijackUserForm(data={"user_pk": self.user1.pk})
        self.assertTrue(form.is_valid())

    def test_form_invalid_with_nonexistent_user(self):
        """Test that form is invalid with nonexistent user pk."""
        form = HijackUserForm(data={"user_pk": 99999})
        self.assertFalse(form.is_valid())
        self.assertIn("user_pk", form.errors)

    def test_form_invalid_without_user_pk(self):
        """Test that form is invalid without user_pk."""
        form = HijackUserForm(data={})
        self.assertFalse(form.is_valid())

    def test_form_queryset_ordered_by_email(self):
        """Test that queryset is ordered by email."""
        form = HijackUserForm()
        queryset = form.fields["user_pk"].queryset
        emails = list(queryset.values_list("email", flat=True))
        self.assertEqual(emails, sorted(emails))
