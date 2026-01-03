"""Tests for A-017: GitHub avatar import.

Users who sign in with GitHub should see their GitHub avatar.
"""

from unittest.mock import patch

from django.test import TestCase

from apps.users.models import CustomUser


class TestAvatarUrl(TestCase):
    """Tests for user avatar URL property."""

    def setUp(self):
        """Set up test fixtures."""
        self.user = CustomUser.objects.create_user(
            username="avatar_test@example.com",
            email="avatar_test@example.com",
            password="testpassword123",
        )

    def test_avatar_url_uses_local_avatar_first(self):
        """Test that local avatar takes priority over GitHub avatar."""
        self.user.avatar = "profile-pictures/test.png"
        self.user.save()

        # Should use local avatar URL (mocked since file doesn't exist)
        with patch.object(type(self.user.avatar), "url", "/media/profile-pictures/test.png"):
            url = self.user.avatar_url
            self.assertEqual(url, "/media/profile-pictures/test.png")

    def test_avatar_url_uses_github_avatar_when_no_local(self):
        """Test that GitHub avatar is used when no local avatar is set."""
        from allauth.socialaccount.models import SocialAccount

        # Create a GitHub social account
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="123456",
            extra_data={"avatar_url": "https://avatars.githubusercontent.com/u/123456"},
        )

        url = self.user.avatar_url
        self.assertEqual(url, "https://avatars.githubusercontent.com/u/123456")

    def test_avatar_url_falls_back_to_gravatar(self):
        """Test that Gravatar is used when no local or GitHub avatar exists."""
        url = self.user.avatar_url
        self.assertIn("gravatar.com", url)
        self.assertIn("identicon", url)

    def test_avatar_url_handles_github_without_avatar(self):
        """Test graceful handling when GitHub account has no avatar_url."""
        from allauth.socialaccount.models import SocialAccount

        # Create a GitHub social account without avatar_url
        SocialAccount.objects.create(
            user=self.user,
            provider="github",
            uid="123456",
            extra_data={"login": "testuser"},  # No avatar_url
        )

        url = self.user.avatar_url
        # Should fall back to Gravatar
        self.assertIn("gravatar.com", url)

    def test_avatar_url_ignores_other_providers(self):
        """Test that non-GitHub social accounts don't provide avatar."""
        from allauth.socialaccount.models import SocialAccount

        # Create a Google social account (not GitHub)
        SocialAccount.objects.create(
            user=self.user,
            provider="google",
            uid="123456",
            extra_data={"picture": "https://google.com/avatar.png"},
        )

        url = self.user.avatar_url
        # Should fall back to Gravatar (Google avatar not used)
        self.assertIn("gravatar.com", url)
