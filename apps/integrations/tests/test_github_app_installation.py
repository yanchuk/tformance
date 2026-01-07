"""Tests for GitHubAppInstallation model.

RED phase: These tests are written BEFORE the model exists.
They should all FAIL until the model is implemented.
"""

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.teams.context import set_current_team, unset_current_team


class TestGitHubAppInstallationModelCreation(TestCase):
    """Tests for basic GitHubAppInstallation model creation."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_model_creation(self):
        """Test that GitHubAppInstallation can be created with all required fields."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        self.assertEqual(installation.team, self.team)
        self.assertEqual(installation.installation_id, 12345678)
        self.assertEqual(installation.account_type, "Organization")
        self.assertEqual(installation.account_login, "acme-corp")
        self.assertEqual(installation.account_id, 87654321)
        self.assertIsNotNone(installation.pk)
        self.assertIsNotNone(installation.created_at)
        self.assertIsNotNone(installation.updated_at)


class TestGitHubAppInstallationUniqueConstraint(TestCase):
    """Tests for GitHubAppInstallation uniqueness constraints."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_unique_installation_id(self):
        """Test that installation_id must be unique across all records."""
        from apps.integrations.models import GitHubAppInstallation

        # Create first installation
        GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        # Try to create second installation with same installation_id (different team)
        team2 = TeamFactory()
        with self.assertRaises(IntegrityError):
            GitHubAppInstallation.objects.create(
                team=team2,
                installation_id=12345678,  # Same installation_id
                account_type="Organization",
                account_login="other-corp",
                account_id=11111111,
            )


class TestGitHubAppInstallationTeamRelationship(TestCase):
    """Tests for GitHubAppInstallation team relationship from BaseTeamModel."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_team_relationship(self):
        """Test that GitHubAppInstallation inherits team relationship from BaseTeamModel."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        # Should have team FK from BaseTeamModel
        self.assertEqual(installation.team, self.team)
        self.assertEqual(installation.team.id, self.team.id)

        # Should have created_at and updated_at from BaseModel
        self.assertIsNotNone(installation.created_at)
        self.assertIsNotNone(installation.updated_at)

    def test_github_app_installation_team_scoped_manager(self):
        """Test that for_team manager filters by current team context."""
        from apps.integrations.models import GitHubAppInstallation

        team2 = TeamFactory()

        # Create installations for two different teams
        installation1 = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=11111111,
            account_type="Organization",
            account_login="team1-org",
            account_id=11111111,
        )
        installation2 = GitHubAppInstallation.objects.create(
            team=team2,
            installation_id=22222222,
            account_type="Organization",
            account_login="team2-org",
            account_id=22222222,
        )

        # Set current team context
        set_current_team(self.team)

        # Query using for_team manager
        installations = GitHubAppInstallation.for_team.all()

        # Should only return installation1
        self.assertEqual(installations.count(), 1)
        self.assertIn(installation1, installations)
        self.assertNotIn(installation2, installations)

        # Switch to team2
        set_current_team(team2)
        installations = GitHubAppInstallation.for_team.all()

        # Should only return installation2
        self.assertEqual(installations.count(), 1)
        self.assertIn(installation2, installations)
        self.assertNotIn(installation1, installations)


class TestGitHubAppInstallationDefaults(TestCase):
    """Tests for GitHubAppInstallation default field values."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_defaults(self):
        """Test that default values are set correctly for is_active, permissions, events, repository_selection."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        # Verify default values
        self.assertTrue(installation.is_active)
        self.assertEqual(installation.permissions, {})
        self.assertEqual(installation.events, [])
        self.assertEqual(installation.repository_selection, "selected")
        self.assertIsNone(installation.suspended_at)
        self.assertEqual(installation.cached_token, "")
        self.assertIsNone(installation.token_expires_at)

    def test_github_app_installation_is_active_default_true(self):
        """Test that is_active defaults to True."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        self.assertTrue(installation.is_active)

    def test_github_app_installation_permissions_default_empty_dict(self):
        """Test that permissions defaults to empty dict."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        self.assertEqual(installation.permissions, {})
        self.assertIsInstance(installation.permissions, dict)

    def test_github_app_installation_events_default_empty_list(self):
        """Test that events defaults to empty list."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        self.assertEqual(installation.events, [])
        self.assertIsInstance(installation.events, list)

    def test_github_app_installation_repository_selection_default(self):
        """Test that repository_selection defaults to 'selected'."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        self.assertEqual(installation.repository_selection, "selected")


class TestGitHubAppInstallationEncryptedToken(TestCase):
    """Tests for GitHubAppInstallation encrypted token field."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_encrypted_token(self):
        """Test that cached_token uses EncryptedTextField and stores encrypted values."""
        from django.db import connection

        from apps.integrations.models import GitHubAppInstallation

        plain_token = "ghs_abc123secrettoken456"
        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            cached_token=plain_token,
        )

        # Access via model returns plaintext
        self.assertEqual(installation.cached_token, plain_token)

        # Query raw database value
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT cached_token FROM integrations_github_app_installation WHERE id = %s",
                [installation.id],
            )
            raw_value = cursor.fetchone()[0]

        # Raw value should NOT equal plaintext (it's encrypted)
        self.assertNotEqual(raw_value, plain_token)
        # Raw value should start with gAAAAA (Fernet encrypted prefix)
        self.assertTrue(
            raw_value.startswith("gAAAAA"),
            f"Expected encrypted value to start with Fernet prefix, got: {raw_value[:20]}...",
        )

    def test_github_app_installation_token_decrypts_correctly_after_reload(self):
        """Test that cached_token can be saved and reloaded with correct decryption."""
        from apps.integrations.models import GitHubAppInstallation

        plain_token = "ghs_reloadableToken123456"
        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            cached_token=plain_token,
        )

        # Clear Django's cache by reloading from DB
        installation.refresh_from_db()

        # Should still return plaintext after reload
        self.assertEqual(installation.cached_token, plain_token)

    def test_github_app_installation_token_can_be_empty(self):
        """Test that cached_token can be blank (not yet fetched)."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            cached_token="",
        )

        self.assertEqual(installation.cached_token, "")


class TestGitHubAppInstallationAdditionalFields(TestCase):
    """Tests for additional GitHubAppInstallation fields."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_suspended_at_nullable(self):
        """Test that suspended_at can be null or set to a datetime."""
        from apps.integrations.models import GitHubAppInstallation

        # Create with null suspended_at
        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )
        self.assertIsNone(installation.suspended_at)

        # Update with a datetime
        suspended_time = timezone.now()
        installation.suspended_at = suspended_time
        installation.save()
        installation.refresh_from_db()
        self.assertEqual(installation.suspended_at, suspended_time)

    def test_github_app_installation_token_expires_at_nullable(self):
        """Test that token_expires_at can be null or set to a datetime."""
        from apps.integrations.models import GitHubAppInstallation

        # Create with null token_expires_at
        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )
        self.assertIsNone(installation.token_expires_at)

        # Update with a datetime
        expires_time = timezone.now() + timezone.timedelta(hours=1)
        installation.token_expires_at = expires_time
        installation.save()
        installation.refresh_from_db()
        self.assertEqual(installation.token_expires_at, expires_time)

    def test_github_app_installation_permissions_stores_json(self):
        """Test that permissions can store JSON permission data."""
        from apps.integrations.models import GitHubAppInstallation

        permissions = {
            "contents": "read",
            "issues": "write",
            "pull_requests": "write",
            "metadata": "read",
        }

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            permissions=permissions,
        )

        installation.refresh_from_db()
        self.assertEqual(installation.permissions, permissions)

    def test_github_app_installation_events_stores_list(self):
        """Test that events can store a list of event names."""
        from apps.integrations.models import GitHubAppInstallation

        events = ["push", "pull_request", "issues", "issue_comment"]

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            events=events,
        )

        installation.refresh_from_db()
        self.assertEqual(installation.events, events)

    def test_github_app_installation_account_type_organization(self):
        """Test that account_type accepts 'Organization' value."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        self.assertEqual(installation.account_type, "Organization")

    def test_github_app_installation_account_type_user(self):
        """Test that account_type accepts 'User' value."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345679,
            account_type="User",
            account_login="john-doe",
            account_id=87654322,
        )

        self.assertEqual(installation.account_type, "User")

    def test_github_app_installation_account_login_indexed(self):
        """Test that account_login is indexed and can be queried efficiently."""
        from apps.integrations.models import GitHubAppInstallation

        installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

        # Query by account_login
        result = GitHubAppInstallation.objects.filter(account_login="acme-corp").first()
        self.assertEqual(result, installation)


class TestGitHubAppInstallationDbTable(TestCase):
    """Tests for GitHubAppInstallation database table configuration."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_app_installation_db_table_name(self):
        """Test that the model uses the correct db_table name."""
        from apps.integrations.models import GitHubAppInstallation

        self.assertEqual(
            GitHubAppInstallation._meta.db_table,
            "integrations_github_app_installation",
        )


class TestGitHubAppInstallationGetAccessToken(TestCase):
    """Tests for GitHubAppInstallation.get_access_token() method."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.models import GitHubAppInstallation

        self.team = TeamFactory()
        self.installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_get_access_token_returns_cached_if_valid(self):
        """Test that get_access_token returns cached token when not expired."""
        from datetime import timedelta

        # Set cached token with expiry more than 5 minutes in the future
        cached_token = "ghs_cached_token_valid"
        self.installation.cached_token = cached_token
        self.installation.token_expires_at = timezone.now() + timedelta(hours=1)
        self.installation.save()

        # Should return cached token without calling GitHub API
        result = self.installation.get_access_token()
        self.assertEqual(result, cached_token)

    def test_get_access_token_refreshes_if_expired(self):
        """Test that get_access_token refreshes token when expired."""
        from datetime import timedelta
        from unittest.mock import patch

        # Set expired token
        self.installation.cached_token = "ghs_old_expired_token"
        self.installation.token_expires_at = timezone.now() - timedelta(hours=1)
        self.installation.save()

        new_token = "ghs_new_refreshed_token"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            result = self.installation.get_access_token()

            # Should return new token
            self.assertEqual(result, new_token)
            # Should have called the refresh function
            mock_get_token.assert_called_once_with(self.installation.installation_id)

    def test_get_access_token_refreshes_within_buffer(self):
        """Test that get_access_token refreshes when within 5-minute buffer of expiry."""
        from datetime import timedelta
        from unittest.mock import patch

        # Set token expiring in 3 minutes (within 5-min buffer)
        self.installation.cached_token = "ghs_expiring_soon_token"
        self.installation.token_expires_at = timezone.now() + timedelta(minutes=3)
        self.installation.save()

        new_token = "ghs_refreshed_before_buffer"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            result = self.installation.get_access_token()

            # Should return new token even though old one isn't technically expired
            self.assertEqual(result, new_token)
            mock_get_token.assert_called_once()

    def test_get_access_token_caches_new_token(self):
        """Test that get_access_token caches the new token after refresh."""
        from datetime import timedelta
        from unittest.mock import patch

        # No cached token
        self.installation.cached_token = ""
        self.installation.token_expires_at = None
        self.installation.save()

        new_token = "ghs_brand_new_token"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            result = self.installation.get_access_token()

            # Verify token returned
            self.assertEqual(result, new_token)

            # Reload from DB to verify caching
            self.installation.refresh_from_db()
            self.assertEqual(self.installation.cached_token, new_token)
            self.assertEqual(self.installation.token_expires_at, new_expiry)


class TestGetAccessTokenRaceCondition(TestCase):
    """Edge case #1: Race condition in token refresh.

    Tests that multiple concurrent requests to get_access_token() do not
    all call the GitHub API simultaneously when the token is expired.
    Uses select_for_update() database locking to prevent race conditions.

    Note: We use TestCase (not TransactionTestCase) and test the locking
    logic without actual threading to avoid test database isolation issues.
    The actual concurrent behavior is tested via the locking mechanism.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.integrations.models import GitHubAppInstallation

        self.team = TeamFactory()
        self.installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            cached_token="",
            token_expires_at=None,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_uses_select_for_update_locking(self):
        """Verify that get_access_token() uses select_for_update() for locking.

        This test verifies the locking mechanism is in place by checking that
        select_for_update() is called during token refresh.
        """
        from datetime import timedelta
        from unittest.mock import patch

        new_token = "ghs_locked_token"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            # Patch select_for_update to track it was called
            with patch.object(
                type(self.installation)._default_manager,
                "select_for_update",
                wraps=type(self.installation)._default_manager.select_for_update,
            ) as mock_select_for_update:
                token = self.installation.get_access_token()

                # Verify select_for_update was called (locking mechanism)
                mock_select_for_update.assert_called_once()
                self.assertEqual(token, new_token)

    def test_second_call_returns_cached_without_api_call(self):
        """Second call should return cached token without calling GitHub API.

        After the first call refreshes and caches the token, subsequent calls
        should return the cached value without making any API calls.
        """
        from datetime import timedelta
        from unittest.mock import patch

        new_token = "ghs_cached_after_refresh"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            # First call - should fetch from API
            token1 = self.installation.get_access_token()
            self.assertEqual(mock_get_token.call_count, 1)
            self.assertEqual(token1, new_token)

            # Second call - should use cache (no additional API call)
            token2 = self.installation.get_access_token()
            self.assertEqual(mock_get_token.call_count, 1)  # Still 1, not 2
            self.assertEqual(token2, new_token)

            # Third call - should still use cache
            token3 = self.installation.get_access_token()
            self.assertEqual(mock_get_token.call_count, 1)  # Still 1
            self.assertEqual(token3, new_token)

    def test_locked_refresh_updates_self_instance(self):
        """After locked refresh, self instance should have updated token values.

        The get_access_token() method should update self.cached_token and
        self.token_expires_at after refreshing, even though it saves via
        the locked instance.
        """
        from datetime import timedelta
        from unittest.mock import patch

        new_token = "ghs_self_updated_token"
        new_expiry = timezone.now() + timedelta(hours=1)

        with patch("apps.integrations.services.github_app.get_installation_token_with_expiry") as mock_get_token:
            mock_get_token.return_value = (new_token, new_expiry)

            # Call get_access_token
            result = self.installation.get_access_token()

            # Verify self instance is updated
            self.assertEqual(result, new_token)
            self.assertEqual(self.installation.cached_token, new_token)
            self.assertEqual(self.installation.token_expires_at, new_expiry)


class TestGetAccessTokenIsActiveCheck(TestCase):
    """Edge case #7: Check is_active before returning token.

    Tests that get_access_token() checks the is_active flag before
    returning a cached token. This prevents using stale tokens after
    the installation has been deleted/deactivated.
    """

    def setUp(self):
        """Set up test fixtures using factories."""
        from datetime import timedelta

        from apps.integrations.models import GitHubAppInstallation

        self.team = TeamFactory()
        self.installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            cached_token="ghs_valid_cached_token",
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_get_access_token_raises_when_inactive(self):
        """get_access_token() should raise GitHubAppDeactivatedError when is_active=False.

        Even if there's a valid cached token, it should not be returned
        if the installation has been deactivated (e.g., user uninstalled App).
        """
        from apps.integrations.exceptions import GitHubAppDeactivatedError

        # Deactivate installation
        self.installation.is_active = False
        self.installation.save()

        with self.assertRaises(GitHubAppDeactivatedError) as context:
            self.installation.get_access_token()

        # Error message should include account login for debugging
        self.assertIn("acme-corp", str(context.exception))

    def test_get_access_token_returns_token_when_active(self):
        """get_access_token() should return token normally when is_active=True."""
        # Installation is active by default from setUp
        self.assertTrue(self.installation.is_active)

        token = self.installation.get_access_token()

        # Should return the cached token
        self.assertEqual(token, "ghs_valid_cached_token")

    def test_get_access_token_error_includes_reinstall_guidance(self):
        """Error message should guide user to reinstall the App."""
        from apps.integrations.exceptions import GitHubAppDeactivatedError

        self.installation.is_active = False
        self.installation.save()

        with self.assertRaises(GitHubAppDeactivatedError) as context:
            self.installation.get_access_token()

        error_msg = str(context.exception).lower()
        # Should mention reinstall or reconnect
        self.assertTrue(
            "reinstall" in error_msg or "reconnect" in error_msg,
            f"Error should guide user to reinstall, got: {context.exception}",
        )


class TestSuspendedVsDeletedErrorMessages(TestCase):
    """Edge case #9: Suspended vs Deleted Not Distinguished.

    Tests that error messages differ for suspended vs deleted installations
    to provide appropriate guidance to users.
    """

    def setUp(self):
        """Set up test fixtures."""
        from apps.integrations.factories import GitHubAppInstallationFactory

        self.team = TeamFactory()
        self.installation = GitHubAppInstallationFactory(
            team=self.team,
            installation_id=99999999,
            account_login="acme-corp",
            is_active=True,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_error_message_for_suspended_installation(self):
        """Suspended installation should mention 'suspended' and org admin contact."""
        from apps.integrations.exceptions import GitHubAppDeactivatedError

        # Suspend the installation
        self.installation.is_active = False
        self.installation.suspended_at = timezone.now()
        self.installation.save()

        with self.assertRaises(GitHubAppDeactivatedError) as context:
            self.installation.get_access_token()

        error_msg = str(context.exception).lower()
        # Should mention suspended, not deleted
        self.assertIn("suspended", error_msg, f"Error should mention 'suspended': {context.exception}")
        # Should guide to contact org admin
        self.assertTrue(
            "admin" in error_msg or "organization" in error_msg,
            f"Should suggest contacting org admin: {context.exception}",
        )

    def test_error_message_for_deleted_installation(self):
        """Deleted installation should mention 'reinstall' guidance."""
        from apps.integrations.exceptions import GitHubAppDeactivatedError

        # Delete the installation (is_active=False but suspended_at=None)
        self.installation.is_active = False
        self.installation.suspended_at = None
        self.installation.save()

        with self.assertRaises(GitHubAppDeactivatedError) as context:
            self.installation.get_access_token()

        error_msg = str(context.exception).lower()
        # Should NOT mention suspended
        self.assertNotIn("suspended", error_msg, f"Deleted installation shouldn't say 'suspended': {context.exception}")
        # Should mention reinstall
        self.assertIn("reinstall", error_msg, f"Should guide user to reinstall: {context.exception}")


class TestRaceBetweenWebhookAndSyncCheck(TestCase):
    """Edge case #12: Race Between Webhook and Sync Check.

    Tests that get_access_token() detects deactivation even when:
    1. Python object has is_active=True (from initial load)
    2. Database has been updated to is_active=False (by webhook)
    3. Token is still cached and valid

    This simulates a webhook arriving during a long-running sync task.
    """

    def setUp(self):
        """Set up test fixtures."""
        from datetime import timedelta

        from apps.integrations.models import GitHubAppInstallation

        self.team = TeamFactory()
        self.installation = GitHubAppInstallation.objects.create(
            team=self.team,
            installation_id=12345678,
            account_type="Organization",
            account_login="acme-corp",
            account_id=87654321,
            cached_token="ghs_valid_cached_token",
            token_expires_at=timezone.now() + timedelta(hours=1),
            is_active=True,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_detects_deactivation_from_database(self):
        """get_access_token() should refresh from DB to detect deactivation.

        Simulates: Task loads installation, webhook deactivates it, task calls get_access_token().
        """
        from apps.integrations.exceptions import GitHubAppDeactivatedError
        from apps.integrations.models import GitHubAppInstallation

        # Verify initial state - object and DB both active
        self.assertTrue(self.installation.is_active)

        # Simulate webhook updating DB directly (installation object not refreshed)
        GitHubAppInstallation.objects.filter(pk=self.installation.pk).update(is_active=False)

        # Object still thinks it's active
        self.assertTrue(self.installation.is_active)

        # get_access_token should detect the deactivation from DB
        with self.assertRaises(GitHubAppDeactivatedError):
            self.installation.get_access_token()
