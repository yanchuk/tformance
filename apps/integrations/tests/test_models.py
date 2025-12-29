"""Tests for IntegrationCredential, GitHubIntegration, and JiraIntegration models."""

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.integrations.factories import (
    GitHubIntegrationFactory,
    IntegrationCredentialFactory,
    JiraIntegrationFactory,
    TrackedRepositoryFactory,
    UserFactory,
)
from apps.integrations.models import (
    GitHubIntegration,
    IntegrationCredential,
    JiraIntegration,
    SlackIntegration,
    TrackedRepository,
)
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


class TestJiraIntegrationModel(TestCase):
    """Tests for JiraIntegration model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_JIRA,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_jira_integration_creation_with_all_required_fields(self):
        """Test that JiraIntegration can be created with all required fields."""
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            cloud_id="aaaaa-bbbbb-ccccc-ddddd",
            site_name="Acme Corp",
            site_url="https://acme.atlassian.net",
        )

        self.assertEqual(integration.team, self.team)
        self.assertEqual(integration.credential, self.credential)
        self.assertEqual(integration.cloud_id, "aaaaa-bbbbb-ccccc-ddddd")
        self.assertEqual(integration.site_name, "Acme Corp")
        self.assertEqual(integration.site_url, "https://acme.atlassian.net")
        self.assertIsNone(integration.last_sync_at)
        self.assertEqual(integration.sync_status, "pending")
        self.assertIsNotNone(integration.pk)
        self.assertIsNotNone(integration.created_at)
        self.assertIsNotNone(integration.updated_at)

    def test_jira_integration_one_to_one_relationship_with_credential(self):
        """Test that JiraIntegration has a one-to-one relationship with IntegrationCredential."""
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access integration from credential using related_name
        self.assertEqual(self.credential.jira_integration, integration)

        # Cannot create another integration with the same credential
        with self.assertRaises(IntegrityError):
            JiraIntegrationFactory(
                team=self.team,
                credential=self.credential,
            )

    def test_jira_integration_cloud_id_is_indexed_and_queryable(self):
        """Test that cloud_id is indexed and can be queried efficiently."""
        cloud_id = "aaaaa-bbbbb-ccccc-ddddd"
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            cloud_id=cloud_id,
        )

        # Query by cloud_id
        result = JiraIntegration.objects.filter(cloud_id=cloud_id).first()
        self.assertEqual(result, integration)

    def test_jira_integration_sync_status_defaults_to_pending(self):
        """Test that sync_status defaults to 'pending'."""
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertEqual(integration.sync_status, "pending")

    def test_jira_integration_last_sync_at_can_be_null(self):
        """Test that last_sync_at can be null (not yet synced)."""
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            last_sync_at=None,
        )

        self.assertIsNone(integration.last_sync_at)

    def test_jira_integration_last_sync_at_can_be_set(self):
        """Test that last_sync_at can be set to a datetime."""
        sync_time = timezone.now()
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            last_sync_at=sync_time,
        )

        self.assertEqual(integration.last_sync_at, sync_time)

    def test_jira_integration_cascade_deletion_with_credential(self):
        """Test that deleting credential cascades to JiraIntegration."""
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        integration_id = integration.id
        credential_id = self.credential.id

        # Delete the credential
        self.credential.delete()

        # JiraIntegration should be deleted too
        with self.assertRaises(JiraIntegration.DoesNotExist):
            JiraIntegration.objects.get(pk=integration_id)

        # Verify credential is also deleted
        with self.assertRaises(IntegrationCredential.DoesNotExist):
            IntegrationCredential.objects.get(pk=credential_id)

    def test_jira_integration_factory_creates_valid_instances(self):
        """Test that JiraIntegrationFactory creates valid instances."""
        # Let factory create its own team to avoid unique constraint conflict
        integration = JiraIntegrationFactory()

        # Factory should create valid credential automatically
        self.assertIsNotNone(integration.credential)
        self.assertEqual(integration.credential.provider, IntegrationCredential.PROVIDER_JIRA)
        self.assertEqual(integration.credential.team, integration.team)

        # Factory should populate all fields
        self.assertIsNotNone(integration.cloud_id)
        self.assertIsNotNone(integration.site_name)
        self.assertIsNotNone(integration.site_url)
        self.assertEqual(integration.sync_status, "pending")
        self.assertIsNone(integration.last_sync_at)

    def test_jira_integration_sync_status_choices(self):
        """Test that sync_status accepts valid choices."""
        statuses = ["pending", "syncing", "complete", "error"]

        for status in statuses:
            team = TeamFactory()  # New team for each to avoid unique constraint
            integration = JiraIntegrationFactory(
                team=team,
                credential=IntegrationCredentialFactory(
                    team=team,
                    provider=IntegrationCredential.PROVIDER_JIRA,
                ),
                sync_status=status,
            )
            self.assertEqual(integration.sync_status, status)

    def test_jira_integration_string_representation(self):
        """Test that string representation shows Jira: {site_name}."""
        integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            site_name="Acme Corp",
        )

        expected = "Jira: Acme Corp"
        self.assertEqual(str(integration), expected)

    def test_jira_integration_team_scoped_manager(self):
        """Test that for_team manager filters by current team context."""
        team2 = TeamFactory()
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider=IntegrationCredential.PROVIDER_JIRA,
        )

        # Create integrations for two different teams
        integration1 = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            site_name="Team 1 Jira",
        )
        integration2 = JiraIntegrationFactory(
            team=team2,
            credential=credential2,
            site_name="Team 2 Jira",
        )

        # Set current team context
        set_current_team(self.team)

        # Query using for_team manager
        integrations = JiraIntegration.for_team.all()

        # Should only return integration1
        self.assertEqual(integrations.count(), 1)
        self.assertIn(integration1, integrations)
        self.assertNotIn(integration2, integrations)

        # Switch to team2
        set_current_team(team2)
        integrations = JiraIntegration.for_team.all()

        # Should only return integration2
        self.assertEqual(integrations.count(), 1)
        self.assertIn(integration2, integrations)
        self.assertNotIn(integration1, integrations)

    def test_jira_integration_indexes_sync_status_and_last_sync_at(self):
        """Test that sync_status + last_sync_at is indexed for efficient queries."""
        # Create integrations with different sync statuses and times
        now = timezone.now()
        older_time = now - timezone.timedelta(hours=2)

        integration1 = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
            sync_status="complete",
            last_sync_at=older_time,
        )

        team2 = TeamFactory()
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider=IntegrationCredential.PROVIDER_JIRA,
        )
        integration2 = JiraIntegrationFactory(
            team=team2,
            credential=credential2,
            sync_status="pending",
            last_sync_at=None,
        )

        # Query by sync_status
        pending = JiraIntegration.objects.filter(sync_status="pending")
        self.assertIn(integration2, pending)
        self.assertNotIn(integration1, pending)

        # Query by sync_status and last_sync_at (compound index)
        stale = JiraIntegration.objects.filter(
            sync_status="complete", last_sync_at__lt=now - timezone.timedelta(hours=1)
        )
        self.assertIn(integration1, stale)
        self.assertNotIn(integration2, stale)


class TestTrackedJiraProjectModel(TestCase):
    """Tests for TrackedJiraProject model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_JIRA,
        )
        self.integration = JiraIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_tracked_jira_project_creation_with_all_required_fields(self):
        """Test that TrackedJiraProject can be created with all required fields."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_id="10001",
            jira_project_key="PROJ",
            name="My Project",
        )

        self.assertEqual(project.team, self.team)
        self.assertEqual(project.integration, self.integration)
        self.assertEqual(project.jira_project_id, "10001")
        self.assertEqual(project.jira_project_key, "PROJ")
        self.assertEqual(project.name, "My Project")
        self.assertTrue(project.is_active)
        self.assertIsNone(project.last_sync_at)
        self.assertEqual(project.sync_status, "pending")
        self.assertIsNone(project.last_sync_error)
        self.assertIsNotNone(project.pk)
        self.assertIsNotNone(project.created_at)
        self.assertIsNotNone(project.updated_at)

    def test_tracked_jira_project_foreign_key_relationship_with_integration(self):
        """Test that TrackedJiraProject has a ForeignKey relationship with JiraIntegration."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
        )

        # Access projects from integration using related_name
        self.assertIn(project, self.integration.tracked_jira_projects.all())
        self.assertEqual(project.integration, self.integration)

    def test_tracked_jira_project_key_is_indexed_and_queryable(self):
        """Test that jira_project_key is indexed and can be queried efficiently."""
        from apps.integrations.factories import TrackedJiraProjectFactory
        from apps.integrations.models import TrackedJiraProject

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="TEST",
        )

        # Query by jira_project_key
        result = TrackedJiraProject.objects.filter(jira_project_key="TEST").first()
        self.assertEqual(result, project)

    def test_tracked_jira_project_sync_status_defaults_to_pending(self):
        """Test that sync_status defaults to 'pending'."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
        )

        self.assertEqual(project.sync_status, "pending")

    def test_tracked_jira_project_is_active_defaults_to_true(self):
        """Test that is_active defaults to True."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
        )

        self.assertTrue(project.is_active)

    def test_tracked_jira_project_last_sync_at_can_be_null(self):
        """Test that last_sync_at can be null (not yet synced)."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            last_sync_at=None,
        )

        self.assertIsNone(project.last_sync_at)

    def test_tracked_jira_project_cascade_deletion_with_integration(self):
        """Test that deleting JiraIntegration cascades to TrackedJiraProject."""
        from apps.integrations.factories import TrackedJiraProjectFactory
        from apps.integrations.models import TrackedJiraProject

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
        )

        project_id = project.id
        integration_id = self.integration.id

        # Delete the integration
        self.integration.delete()

        # TrackedJiraProject should be deleted too
        with self.assertRaises(TrackedJiraProject.DoesNotExist):
            TrackedJiraProject.objects.get(pk=project_id)

        # Verify integration is also deleted
        with self.assertRaises(JiraIntegration.DoesNotExist):
            JiraIntegration.objects.get(pk=integration_id)

    def test_tracked_jira_project_unique_constraint_team_jira_project_id(self):
        """Test that only one project per team+jira_project_id is allowed."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        # Create first project
        TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_id="10001",
            jira_project_key="PROJ1",
            name="Project 1",
        )

        # Try to create second project with same team and jira_project_id
        with self.assertRaises(IntegrityError):
            TrackedJiraProjectFactory(
                team=self.team,
                integration=self.integration,
                jira_project_id="10001",
                jira_project_key="PROJ2",  # Different key, same ID
                name="Project 2",
            )

    def test_tracked_jira_project_factory_creates_valid_instances(self):
        """Test that TrackedJiraProjectFactory creates valid instances."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory()

        # Factory should populate all required fields
        self.assertIsNotNone(project.integration)
        self.assertIsNotNone(project.jira_project_id)
        self.assertIsNotNone(project.jira_project_key)
        self.assertIsNotNone(project.name)
        self.assertTrue(project.is_active)
        self.assertEqual(project.sync_status, "pending")
        self.assertIsNone(project.last_sync_at)
        self.assertIsNone(project.last_sync_error)

    def test_tracked_jira_project_multiple_projects_per_integration(self):
        """Test that multiple projects can be tracked per integration."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project1 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_id="10001",
            jira_project_key="PROJ1",
        )
        project2 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_id="10002",
            jira_project_key="PROJ2",
        )

        # Both projects should be linked to the same integration
        self.assertEqual(project1.integration, self.integration)
        self.assertEqual(project2.integration, self.integration)
        self.assertEqual(self.integration.tracked_jira_projects.count(), 2)

    def test_tracked_jira_project_string_representation(self):
        """Test that string representation shows project key and name."""
        from apps.integrations.factories import TrackedJiraProjectFactory

        project = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="ACME",
            name="Acme Project",
        )

        expected = "ACME: Acme Project"
        self.assertEqual(str(project), expected)

    def test_tracked_jira_project_team_scoped_manager(self):
        """Test that for_team manager filters by current team context."""
        from apps.integrations.factories import TrackedJiraProjectFactory
        from apps.integrations.models import TrackedJiraProject

        team2 = TeamFactory()
        credential2 = IntegrationCredentialFactory(
            team=team2,
            provider=IntegrationCredential.PROVIDER_JIRA,
        )
        integration2 = JiraIntegrationFactory(
            team=team2,
            credential=credential2,
        )

        # Create projects for two different teams
        project1 = TrackedJiraProjectFactory(
            team=self.team,
            integration=self.integration,
            jira_project_key="TEAM1",
        )
        project2 = TrackedJiraProjectFactory(
            team=team2,
            integration=integration2,
            jira_project_key="TEAM2",
        )

        # Set current team context
        set_current_team(self.team)

        # Query using for_team manager
        projects = TrackedJiraProject.for_team.all()

        # Should only return project1
        self.assertEqual(projects.count(), 1)
        self.assertIn(project1, projects)
        self.assertNotIn(project2, projects)

        # Switch to team2
        set_current_team(team2)
        projects = TrackedJiraProject.for_team.all()

        # Should only return project2
        self.assertEqual(projects.count(), 1)
        self.assertIn(project2, projects)
        self.assertNotIn(project1, projects)


class TestGitHubIntegrationMemberSyncFields(TestCase):
    """Tests for GitHubIntegration member sync fields.

    These fields track the status and results of member synchronization
    from GitHub org to TeamMember records.
    """

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

    def test_member_sync_status_field_exists(self):
        """Test that member_sync_status field exists on GitHubIntegration."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access the field to verify it exists
        self.assertTrue(hasattr(integration, "member_sync_status"))

    def test_member_sync_status_default_value(self):
        """Test that member_sync_status defaults to 'pending'."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertEqual(integration.member_sync_status, "pending")

    def test_member_sync_status_choices(self):
        """Test that member_sync_status accepts valid sync status choices."""
        statuses = ["pending", "syncing", "complete", "error"]

        for status in statuses:
            team = TeamFactory()
            integration = GitHubIntegrationFactory(
                team=team,
                credential=IntegrationCredentialFactory(
                    team=team,
                    provider=IntegrationCredential.PROVIDER_GITHUB,
                ),
                member_sync_status=status,
            )
            self.assertEqual(integration.member_sync_status, status)

    def test_member_sync_started_at_field_exists(self):
        """Test that member_sync_started_at field exists on GitHubIntegration."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access the field to verify it exists
        self.assertTrue(hasattr(integration, "member_sync_started_at"))

    def test_member_sync_started_at_default_is_null(self):
        """Test that member_sync_started_at defaults to null."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertIsNone(integration.member_sync_started_at)

    def test_member_sync_started_at_can_be_set(self):
        """Test that member_sync_started_at can be set to a datetime."""
        sync_time = timezone.now()
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            member_sync_started_at=sync_time,
        )

        self.assertEqual(integration.member_sync_started_at, sync_time)

    def test_member_sync_completed_at_field_exists(self):
        """Test that member_sync_completed_at field exists on GitHubIntegration."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access the field to verify it exists
        self.assertTrue(hasattr(integration, "member_sync_completed_at"))

    def test_member_sync_completed_at_default_is_null(self):
        """Test that member_sync_completed_at defaults to null."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertIsNone(integration.member_sync_completed_at)

    def test_member_sync_completed_at_can_be_set(self):
        """Test that member_sync_completed_at can be set to a datetime."""
        sync_time = timezone.now()
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            member_sync_completed_at=sync_time,
        )

        self.assertEqual(integration.member_sync_completed_at, sync_time)

    def test_member_sync_error_field_exists(self):
        """Test that member_sync_error field exists on GitHubIntegration."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access the field to verify it exists
        self.assertTrue(hasattr(integration, "member_sync_error"))

    def test_member_sync_error_default_is_blank(self):
        """Test that member_sync_error defaults to empty string."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertEqual(integration.member_sync_error, "")

    def test_member_sync_error_can_store_error_message(self):
        """Test that member_sync_error can store an error message."""
        error_message = "Failed to fetch org members: API rate limit exceeded"
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            member_sync_error=error_message,
        )

        self.assertEqual(integration.member_sync_error, error_message)

    def test_member_sync_result_field_exists(self):
        """Test that member_sync_result field exists on GitHubIntegration."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        # Access the field to verify it exists
        self.assertTrue(hasattr(integration, "member_sync_result"))

    def test_member_sync_result_default_is_null(self):
        """Test that member_sync_result defaults to null."""
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
        )

        self.assertIsNone(integration.member_sync_result)

    def test_member_sync_result_can_store_json_data(self):
        """Test that member_sync_result can store JSON sync result data."""
        result_data = {
            "members_created": 5,
            "members_updated": 3,
            "members_skipped": 1,
            "total_fetched": 9,
        }
        integration = GitHubIntegrationFactory(
            team=self.team,
            credential=self.credential,
            member_sync_result=result_data,
        )

        self.assertEqual(integration.member_sync_result, result_data)


class TestSlackIntegrationModel(TestCase):
    """Tests for SlackIntegration model."""

    def setUp(self):
        """Set up test fixtures using factories."""
        self.team = TeamFactory()
        self.credential = IntegrationCredentialFactory(
            team=self.team,
            provider=IntegrationCredential.PROVIDER_SLACK,
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_slack_integration_creation_with_all_fields(self):
        """Test that SlackIntegration can be created with all fields."""
        from datetime import time

        integration = SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id="T12345678",
            workspace_name="Acme Corp",
            bot_user_id="U12345678",
            leaderboard_channel_id="C12345678",
            leaderboard_day=3,
            leaderboard_time=time(14, 30),
            leaderboard_enabled=False,
            surveys_enabled=False,
            reveals_enabled=False,
        )

        self.assertEqual(integration.team, self.team)
        self.assertEqual(integration.credential, self.credential)
        self.assertEqual(integration.workspace_id, "T12345678")
        self.assertEqual(integration.workspace_name, "Acme Corp")
        self.assertEqual(integration.bot_user_id, "U12345678")
        self.assertEqual(integration.leaderboard_channel_id, "C12345678")
        self.assertEqual(integration.leaderboard_day, 3)
        self.assertEqual(integration.leaderboard_time, time(14, 30))
        self.assertFalse(integration.leaderboard_enabled)
        self.assertFalse(integration.surveys_enabled)
        self.assertFalse(integration.reveals_enabled)
        self.assertIsNone(integration.last_sync_at)
        self.assertEqual(integration.sync_status, "pending")
        self.assertIsNotNone(integration.pk)
        self.assertIsNotNone(integration.created_at)
        self.assertIsNotNone(integration.updated_at)

    def test_slack_integration_default_values(self):
        """Test that SlackIntegration has correct default values."""
        from datetime import time

        integration = SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id="T12345678",
            workspace_name="Acme Corp",
            bot_user_id="U12345678",
        )

        self.assertEqual(integration.leaderboard_day, 0)  # Monday
        self.assertEqual(integration.leaderboard_time, time(9, 0))  # 09:00
        self.assertTrue(integration.leaderboard_enabled)
        self.assertTrue(integration.surveys_enabled)
        self.assertTrue(integration.reveals_enabled)
        self.assertEqual(integration.leaderboard_channel_id, "")
        self.assertIsNone(integration.last_sync_at)
        self.assertEqual(integration.sync_status, "pending")

    def test_slack_integration_one_to_one_relationship_with_credential(self):
        """Test that SlackIntegration has a one-to-one relationship with IntegrationCredential."""

        integration = SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id="T12345678",
            workspace_name="Acme Corp",
            bot_user_id="U12345678",
        )

        # Access integration from credential using related_name
        self.assertEqual(self.credential.slack_integration, integration)

        # Cannot create another integration with the same credential
        with self.assertRaises(IntegrityError):
            SlackIntegration.objects.create(
                team=self.team,
                credential=self.credential,
                workspace_id="T87654321",
                workspace_name="Another Corp",
                bot_user_id="U87654321",
            )

    def test_slack_integration_team_relationship_from_base_team_model(self):
        """Test that SlackIntegration inherits team relationship from BaseTeamModel."""

        integration = SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id="T12345678",
            workspace_name="Acme Corp",
            bot_user_id="U12345678",
        )

        self.assertEqual(integration.team, self.team)
        self.assertIsNotNone(integration.created_at)
        self.assertIsNotNone(integration.updated_at)

    def test_slack_integration_unique_constraint_team_workspace_id(self):
        """Test that only one integration per team+workspace_id is allowed."""

        # Create first integration
        SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id="T12345678",
            workspace_name="Acme Corp",
            bot_user_id="U12345678",
        )

        # Create another credential for the same team
        credential2 = IntegrationCredentialFactory(
            team=TeamFactory(),  # Different team to avoid team+provider unique constraint
            provider=IntegrationCredential.PROVIDER_SLACK,
        )

        # Try to create second integration with same team and workspace_id
        with self.assertRaises(IntegrityError):
            SlackIntegration.objects.create(
                team=self.team,
                credential=credential2,
                workspace_id="T12345678",  # Same workspace_id
                workspace_name="Acme Corp 2",
                bot_user_id="U87654321",
            )

    def test_slack_integration_string_representation(self):
        """Test that string representation shows 'Slack: {workspace_name}'."""

        integration = SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id="T12345678",
            workspace_name="Acme Engineering",
            bot_user_id="U12345678",
        )

        expected = "Slack: Acme Engineering"
        self.assertEqual(str(integration), expected)

    def test_slack_integration_workspace_id_is_indexed(self):
        """Test that workspace_id is indexed and can be queried efficiently."""

        workspace_id = "T12345678"
        integration = SlackIntegration.objects.create(
            team=self.team,
            credential=self.credential,
            workspace_id=workspace_id,
            workspace_name="Acme Corp",
            bot_user_id="U12345678",
        )

        # Query by workspace_id
        result = SlackIntegration.objects.filter(workspace_id=workspace_id).first()
        self.assertEqual(result, integration)

    def test_slack_integration_sync_status_choices_match_constants(self):
        """Test that sync_status accepts valid choices from SYNC_STATUS_CHOICES."""

        statuses = ["pending", "syncing", "complete", "error"]

        for status in statuses:
            team = TeamFactory()  # New team for each to avoid unique constraint
            credential = IntegrationCredentialFactory(
                team=team,
                provider=IntegrationCredential.PROVIDER_SLACK,
            )
            integration = SlackIntegration.objects.create(
                team=team,
                credential=credential,
                workspace_id=f"T{status}1234",  # Unique workspace_id
                workspace_name=f"Test {status}",
                bot_user_id="U12345678",
                sync_status=status,
            )
            self.assertEqual(integration.sync_status, status)
