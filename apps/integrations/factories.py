"""
Factory Boy factories for integrations models.

Usage in tests:
    from apps.integrations.factories import IntegrationCredentialFactory, GitHubIntegrationFactory

    # Create a single instance
    credential = IntegrationCredentialFactory()
    github_integration = GitHubIntegrationFactory()

    # Create with specific attributes
    credential = IntegrationCredentialFactory(provider="github", team=my_team)
    github_integration = GitHubIntegrationFactory(organization_slug="my-org", team=my_team)

    # Create multiple instances
    credentials = IntegrationCredentialFactory.create_batch(3)

    # Build without saving (for unit tests)
    credential = IntegrationCredentialFactory.build()
"""

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory

from apps.metrics.factories import TeamFactory
from apps.users.models import CustomUser

from .models import GitHubIntegration, IntegrationCredential
from .services.encryption import encrypt


class UserFactory(DjangoModelFactory):
    """Factory for CustomUser model."""

    class Meta:
        model = CustomUser

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True


class IntegrationCredentialFactory(DjangoModelFactory):
    """Factory for IntegrationCredential model."""

    class Meta:
        model = IntegrationCredential

    team = factory.SubFactory(TeamFactory)
    provider = factory.Iterator(["github", "jira", "slack"])
    access_token = factory.LazyFunction(lambda: encrypt("fake_access_token_12345"))
    refresh_token = factory.LazyFunction(lambda: encrypt("fake_refresh_token_67890"))
    token_expires_at = factory.LazyFunction(lambda: timezone.now() + timezone.timedelta(days=30))
    scopes = factory.List(["read:org", "repo"])
    connected_by = factory.SubFactory(UserFactory)


class GitHubIntegrationFactory(DjangoModelFactory):
    """Factory for GitHubIntegration model."""

    class Meta:
        model = GitHubIntegration

    team = factory.SubFactory(TeamFactory)
    credential = factory.SubFactory(
        IntegrationCredentialFactory,
        team=factory.SelfAttribute("..team"),
        provider=IntegrationCredential.PROVIDER_GITHUB,
    )
    organization_slug = factory.Sequence(lambda n: f"org-{n}")
    organization_id = factory.Sequence(lambda n: 10000000 + n)
    webhook_secret = factory.Faker("sha256")
    last_sync_at = None
    sync_status = "pending"


class TrackedRepositoryFactory(DjangoModelFactory):
    """Factory for TrackedRepository model."""

    class Meta:
        model = "integrations.TrackedRepository"

    team = factory.SubFactory(TeamFactory)
    integration = factory.SubFactory(
        GitHubIntegrationFactory,
        team=factory.SelfAttribute("..team"),
    )
    github_repo_id = factory.Sequence(lambda n: 20000000 + n)
    full_name = factory.Sequence(lambda n: f"owner-{n}/repo-{n}")
    is_active = True
    webhook_id = None
    last_sync_at = None
