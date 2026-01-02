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
