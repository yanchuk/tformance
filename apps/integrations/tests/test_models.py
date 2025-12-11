"""Tests for IntegrationCredential and GitHubIntegration models."""

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    TrackedRepositoryFactory,
    UserFactory,
)
from apps.integrations.models import GitHubIntegration, IntegrationCredential, TrackedRepository
from apps.metrics.factories import TeamFactory
from apps.teams.context import set_current_team, unset_current_team


class TestIntegrationCredentialModel(TestCase):
    """Tests for IntegrationCredential model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.user = UserFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_integration_credential_creation_with_all_fields(self):
        """Test that IntegrationCredential can be created with all required fields."""
        expires_at = timezone.now() + timezone.timedelta(days=30)
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_access_token_123",
            refresh_token="test_refresh_token_456",
            token_expires_at=expires_at,
            scopes=["read:org", "repo", "read:user"],
            connected_by=self.user,
        )

        self.assertEqual(credential.team, self.team)
        self.assertEqual(credential.provider, "github")
        self.assertEqual(credential.access_token, "test_access_token_123")
        self.assertEqual(credential.refresh_token, "test_refresh_token_456")
        self.assertEqual(credential.token_expires_at, expires_at)
        self.assertEqual(credential.scopes, ["read:org", "repo", "read:user"])
        self.assertEqual(credential.connected_by, self.user)
        self.assertIsNotNone(credential.pk)
        self.assertIsNotNone(credential.created_at)
        self.assertIsNotNone(credential.updated_at)

    def test_integration_credential_creation_minimal_fields(self):
        """Test that IntegrationCredential can be created with minimal required fields."""
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="slack",
            access_token="test_token",
        )

        self.assertEqual(credential.team, self.team)
        self.assertEqual(credential.provider, "slack")
        self.assertEqual(credential.access_token, "test_token")
        self.assertIsNotNone(credential.pk)

    def test_integration_credential_default_scopes(self):
        """Test that scopes defaults to empty list."""
        credential = IntegrationCredential.objects.create(
            team=self.team,
            provider="github",
            access_token="test_token",
        )

        self.assertEqual(credential.scopes, [])

    def test_integration_credential_refresh_token_optional(self):
        """Test that refresh_token can be blank."""
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="jira",
            access_token="test_token",
            refresh_token="",
        )

        self.assertEqual(credential.refresh_token, "")
        self.assertIsNotNone(credential.pk)

    def test_integration_credential_token_expires_at_optional(self):
        """Test that token_expires_at can be null."""
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
            token_expires_at=None,
        )

        self.assertIsNone(credential.token_expires_at)
        self.assertIsNotNone(credential.pk)

    def test_integration_credential_connected_by_optional(self):
        """Test that connected_by can be null."""
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
            connected_by=None,
        )

        self.assertIsNone(credential.connected_by)
        self.assertIsNotNone(credential.pk)

    def test_integration_credential_unique_constraint(self):
        """Test that only one integration per provider per team is allowed."""
        # Create first credential
        IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="token1",
        )

        # Try to create second credential with same team and provider
        with self.assertRaises(IntegrityError):
            IntegrationCredentialFactory(
                team=self.team,
                provider="github",
                access_token="token2",
            )

    def test_integration_credential_same_provider_different_teams(self):
        """Test that same provider can be used by different teams."""
        team2 = TeamFactory()

        credential1 = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="token1",
        )
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider="github",
            access_token="token2",
        )

        self.assertEqual(credential1.provider, "github")
        self.assertEqual(credential2.provider, "github")
        self.assertNotEqual(credential1.team, credential2.team)

    def test_integration_credential_string_representation(self):
        """Test that string representation shows provider and team name."""
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
        )

        expected = f"github for {self.team.name}"
        self.assertEqual(str(credential), expected)

    def test_integration_credential_provider_choices(self):
        """Test that provider accepts valid choices."""
        for provider in ["github", "jira", "slack"]:
            credential = IntegrationCredentialFactory(
                team=TeamFactory(),  # New team for each to avoid unique constraint
                provider=provider,
                access_token="test_token",
            )
            self.assertEqual(credential.provider, provider)

    def test_integration_credential_team_scoped_manager(self):
        """Test that for_team manager filters by current team context."""
        team2 = TeamFactory()

        # Create credentials for two different teams
        credential1 = IntegrationCredentialFactory(team=self.team, provider="github")
        credential2 = IntegrationCredentialFactory(team=team2, provider="jira")

        # Set current team context
        set_current_team(self.team)

        # Query using for_team manager
        credentials = IntegrationCredential.for_team.all()

        # Should only return credential1
        self.assertEqual(credentials.count(), 1)
        self.assertIn(credential1, credentials)
        self.assertNotIn(credential2, credentials)

        # Switch to team2
        set_current_team(team2)
        credentials = IntegrationCredential.for_team.all()

        # Should only return credential2
        self.assertEqual(credentials.count(), 1)
        self.assertIn(credential2, credentials)
        self.assertNotIn(credential1, credentials)

    def test_integration_credential_connected_by_user_deletion(self):
        """Test that connected_by is set to null when user is deleted."""
        user = UserFactory()
        credential = IntegrationCredentialFactory(
            team=self.team,
            provider="github",
            access_token="test_token",
            connected_by=user,
        )

        user.delete()

        # Refresh from database
        credential.refresh_from_db()

        # connected_by should be null
        self.assertIsNone(credential.connected_by)


class TestGitHubIntegrationModel(TestCase):
    """Tests for GitHubIntegration model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_GITHUB,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_github_integration_creation_with_all_required_fields(self):
        """Test that GitHubIntegration can be created with all required fields."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="test-org",
            organization_id=12345678,
            webhook_secret="test_webhook_secret_123",
        )

        self.assertEqual(integration.team, self.team)
        self.assertEqual(integration.credential, self.credential)
        self.assertEqual(integration.organization_slug, "test-org")
        self.assertEqual(integration.organization_id, 12345678)
        self.assertEqual(integration.webhook_secret, "test_webhook_secret_123")
        self.assertIsNone(integration.last_sync_at)
        self.assertEqual(integration.sync_status, "pending")
        self.assertIsNotNone(integration.pk)
        self.assertIsNotNone(integration.created_at)
        self.assertIsNotNone(integration.updated_at)

    def test_github_integration_one_to_one_relationship_with_credential(self):
        """Test that GitHubIntegration has a one-to-one relationship with IntegrationCredential."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access integration from credential using related_name
        self.assertEqual(self.credential.github_integration, integration)

        # Cannot create another integration with the same credential
        with self.assertRaises(IntegrityError):
            GitHubIntegrationFactory(
                team=self.team,
                credential=self.credential,
            )

    def test_github_integration_sync_status_choices(self):
        """Test that sync_status accepts valid choices."""
        statuses = ["pending", "syncing", "complete", "error"]

        for status in statuses:
            team = TeamFactory()  # New team for each to avoid unique constraint
            integration = GitHubIntegrationFactory(
                team=team,
                credential=IntegrationCredentialFactory(
                    team=team,
                    provider=IntegrationCredential.PROVIDER_GITHUB,
                ),
                sync_status=status,
            )
            self.assertEqual(integration.sync_status, status)

    def test_github_integration_sync_status_default_value(self):
        """Test that sync_status defaults to 'pending'."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertEqual(integration.sync_status, "pending")

    def test_github_integration_string_representation(self):
        """Test that string representation shows GitHub: {organization_slug}."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="my-awesome-org",
        )

        expected = "GitHub: my-awesome-org"
        self.assertEqual(str(integration), expected)

    def test_github_integration_cascade_deletion_with_credential(self):
        """Test that deleting credential cascades to GitHubIntegration."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        integration_id = integration.id
        credential_id = self.credential.id

        # Delete the credential
        self.credential.delete()

        # GitHubIntegration should be deleted too
        with self.assertRaises(GitHubIntegration.DoesNotExist):
            GitHubIntegration.objects.get(pk=integration_id)

        # Verify credential is also deleted
        with self.assertRaises(IntegrationCredential.DoesNotExist):
            IntegrationCredential.objects.get(pk=credential_id)

    def test_github_integration_team_scoped_manager(self):
        """Test that for_team manager filters by current team context."""
        team2 = TeamFactory()
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider=IntegrationCredential.PROVIDER_GITHUB,
        )

        # Create integrations for two different teams
        integration1 = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            organization_slug="team1-org",
        )
        integration2 = GitHubIntegrationFactory(
            team=team2,
            credential=credential2,
            organization_slug="team2-org",
        )

        # Set current team context
        set_current_team(self.team)

        # Query using for_team manager
        integrations = GitHubIntegration.for_team.all()

        # Should only return integration1
        self.assertEqual(integrations.count(), 1)
        self.assertIn(integration1, integrations)
        self.assertNotIn(integration2, integrations)

        # Switch to team2
        set_current_team(team2)
        integrations = GitHubIntegration.for_team.all()

        # Should only return integration2
        self.assertEqual(integrations.count(), 1)
        self.assertIn(integration2, integrations)
        self.assertNotIn(integration1, integrations)

    def test_github_integration_last_sync_at_can_be_null(self):
        """Test that last_sync_at can be null (not yet synced)."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            last_sync_at=None,
        )

        self.assertIsNone(integration.last_sync_at)

    def test_github_integration_last_sync_at_can_be_set(self):
        """Test that last_sync_at can be set to a datetime."""
        sync_time = timezone.now()
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            last_sync_at=sync_time,
        )

        self.assertEqual(integration.last_sync_at, sync_time)


class TestTrackedRepositoryModel(TestCase):
    """Tests for TrackedRepository model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_GITHUB,
        )
        self.integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_tracked_repository_creation_with_all_required_fields(self):
        """Test that TrackedRepository can be created with all required fields."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=123456789,
            full_name="owner/repo",
        )

        self.assertEqual(repo.team, self.team)
        self.assertEqual(repo.integration, self.integration)
        self.assertEqual(repo.github_repo_id, 123456789)
        self.assertEqual(repo.full_name, "owner/repo")
        self.assertTrue(repo.is_active)
        self.assertIsNone(repo.webhook_id)
        self.assertIsNone(repo.last_sync_at)
        self.assertIsNotNone(repo.pk)
        self.assertIsNotNone(repo.created_at)
        self.assertIsNotNone(repo.updated_at)

    def test_tracked_repository_foreign_key_relationship_with_integration(self):
        """Test that TrackedRepository has a ForeignKey relationship with GitHubIntegration."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
        )

        # Access repositories from integration using related_name
        self.assertIn(repo, self.integration.tracked_repositories.all())
        self.assertEqual(repo.integration, self.integration)

    def test_tracked_repository_is_active_default_value(self):
        """Test that is_active defaults to True."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
        )

        self.assertTrue(repo.is_active)

    def test_tracked_repository_webhook_id_can_be_null(self):
        """Test that webhook_id can be null (not yet registered)."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            webhook_id=None,
        )

        self.assertIsNone(repo.webhook_id)

    def test_tracked_repository_webhook_id_can_be_set(self):
        """Test that webhook_id can be set to a value."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            webhook_id=987654321,
        )

        self.assertEqual(repo.webhook_id, 987654321)

    def test_tracked_repository_unique_constraint_team_github_repo_id(self):
        """Test that only one repository per team+github_repo_id is allowed."""
        # Create first repository
        TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=123456789,
            full_name="owner/repo1",
        )

        # Try to create second repository with same team and github_repo_id
        with self.assertRaises(IntegrityError):
            TrackedRepositoryFactory(
                team=self.team,
                integration=self.integration,
                github_repo_id=123456789,
                full_name="owner/repo2",  # Different name, same ID
            )

    def test_tracked_repository_same_github_repo_id_different_teams(self):
        """Test that same github_repo_id can be used by different teams."""
        team2 = TeamFactory()
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider=IntegrationCredential.PROVIDER_GITHUB,
        )
        integration2 = GitHubIntegrationFactory(
            team=team2,
            credential=credential2,
        )

        repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            github_repo_id=123456789,
            full_name="owner/repo",
        )
        repo2 = TrackedRepositoryFactory(
            team=team2,
            integration=integration2,
            github_repo_id=123456789,
            full_name="owner/repo",
        )

        self.assertEqual(repo1.github_repo_id, 123456789)
        self.assertEqual(repo2.github_repo_id, 123456789)
        self.assertNotEqual(repo1.team, repo2.team)

    def test_tracked_repository_string_representation(self):
        """Test that string representation shows full_name."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="my-org/awesome-repo",
        )

        self.assertEqual(str(repo), "my-org/awesome-repo")

    def test_tracked_repository_cascade_deletion_with_integration(self):
        """Test that deleting GitHubIntegration cascades to TrackedRepository."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
        )

        repo_id = repo.id
        integration_id = self.integration.id

        # Delete the integration
        self.integration.delete()

        # TrackedRepository should be deleted too
        with self.assertRaises(TrackedRepository.DoesNotExist):
            TrackedRepository.objects.get(pk=repo_id)

        # Verify integration is also deleted
        with self.assertRaises(GitHubIntegration.DoesNotExist):
            GitHubIntegration.objects.get(pk=integration_id)

    def test_tracked_repository_team_scoped_manager(self):
        """Test that for_team manager filters by current team context."""
        team2 = TeamFactory()
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider=IntegrationCredential.PROVIDER_GITHUB,
        )
        integration2 = GitHubIntegrationFactory(
            team=team2,
            credential=credential2,
        )

        # Create repositories for two different teams
        repo1 = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            full_name="team1/repo1",
        )
        repo2 = TrackedRepositoryFactory(
            team=team2,
            integration=integration2,
            full_name="team2/repo2",
        )

        # Set current team context
        set_current_team(self.team)

        # Query using for_team manager
        repos = TrackedRepository.for_team.all()

        # Should only return repo1
        self.assertEqual(repos.count(), 1)
        self.assertIn(repo1, repos)
        self.assertNotIn(repo2, repos)

        # Switch to team2
        set_current_team(team2)
        repos = TrackedRepository.for_team.all()

        # Should only return repo2
        self.assertEqual(repos.count(), 1)
        self.assertIn(repo2, repos)
        self.assertNotIn(repo1, repos)

    def test_tracked_repository_last_sync_at_can_be_null(self):
        """Test that last_sync_at can be null (not yet synced)."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            last_sync_at=None,
        )

        self.assertIsNone(repo.last_sync_at)

    def test_tracked_repository_last_sync_at_can_be_set(self):
        """Test that last_sync_at can be set to a datetime."""
        sync_time = timezone.now()
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            last_sync_at=sync_time,
        )

        self.assertEqual(repo.last_sync_at, sync_time)

    def test_tracked_repository_sync_status_default_value(self):
        """Test that sync_status defaults to 'pending'."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
        )

        self.assertEqual(repo.sync_status, "pending")

    def test_tracked_repository_sync_status_choices(self):
        """Test that sync_status accepts valid choices."""
        statuses = ["pending", "syncing", "complete", "error"]

        for status in statuses:
            team = TeamFactory()  # New team for each to avoid unique constraint
            integration = GitHubIntegrationFactory(
                team=team,
                credential=IntegrationCredentialFactory(
                    team=team,
                    provider=IntegrationCredential.PROVIDER_GITHUB,
                ),
            )
            repo = TrackedRepositoryFactory(
                team=team,
                integration=integration,
                sync_status=status,
            )
            self.assertEqual(repo.sync_status, status)

    def test_tracked_repository_last_sync_error_can_be_null(self):
        """Test that last_sync_error can be null (no error)."""
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            last_sync_error=None,
        )

        self.assertIsNone(repo.last_sync_error)

    def test_tracked_repository_last_sync_error_can_be_set(self):
        """Test that last_sync_error can be set to an error message."""
        error_message = "GitHub API rate limit exceeded"
        repo = TrackedRepositoryFactory(
            team=self.team,
            integration=self.integration,
            last_sync_error=error_message,
        )

        self.assertEqual(repo.last_sync_error, error_message)
