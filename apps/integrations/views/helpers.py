"""Helper functions for integration views."""

import logging
import secrets

from django.contrib import messages
from django.shortcuts import redirect

from apps.integrations.models import GitHubIntegration, IntegrationCredential
from apps.integrations.services import github_webhooks, member_sync
from apps.integrations.services.github_oauth import GitHubOAuthError

logger = logging.getLogger(__name__)


def _create_repository_webhook(access_token, repo_full_name, webhook_url, secret):
    """Create a GitHub webhook for a repository.

    Attempts to create a webhook and returns the webhook ID. If creation fails,
    logs the error and returns None (graceful degradation).

    Args:
        access_token: The GitHub OAuth access token.
        repo_full_name: The full name of the repository (e.g., "org/repo").
        webhook_url: The URL for the webhook endpoint.
        secret: The webhook secret for signature verification.

    Returns:
        int or None: The webhook ID if successful, None if creation failed.
    """
    try:
        return github_webhooks.create_repository_webhook(
            access_token=access_token,
            repo_full_name=repo_full_name,
            webhook_url=webhook_url,
            secret=secret,
        )
    except GitHubOAuthError as e:
        logger.error(f"Failed to create webhook for {repo_full_name}: {e}")
        return None


def _delete_repository_webhook(access_token, repo_full_name, webhook_id):
    """Delete a GitHub webhook from a repository.

    Attempts to delete a webhook. If deletion fails, logs the error but doesn't
    raise an exception (graceful degradation).

    Args:
        access_token: The GitHub OAuth access token.
        repo_full_name: The full name of the repository (e.g., "org/repo").
        webhook_id: The ID of the webhook to delete.
    """
    try:
        github_webhooks.delete_repository_webhook(
            access_token=access_token,
            repo_full_name=repo_full_name,
            webhook_id=webhook_id,
        )
    except GitHubOAuthError as e:
        logger.error(f"Failed to delete webhook for {repo_full_name}: {e}")


def _create_integration_credential(team, access_token, provider, user):
    """Create an encrypted integration credential for a team.

    Args:
        team: The team to create the credential for.
        access_token: The OAuth access token (will be encrypted).
        provider: The provider type (e.g., PROVIDER_GITHUB, PROVIDER_JIRA).
        user: The user who connected the integration.

    Returns:
        IntegrationCredential: The created credential object.
    """
    # EncryptedTextField handles encryption automatically
    return IntegrationCredential.objects.create(
        team=team,
        provider=provider,
        access_token=access_token,
        connected_by=user,
    )


def _validate_oauth_callback(request, team, verify_state_func, oauth_error_class, provider_name):
    """Validate OAuth callback parameters and state.

    Args:
        request: The HTTP request object.
        team: The team object.
        verify_state_func: Function to verify the state parameter.
        oauth_error_class: The OAuth error exception class to catch.
        provider_name: The name of the provider (e.g., "GitHub", "Jira").

    Returns:
        tuple: (code, None) if validation succeeds, (None, redirect_response) if validation fails.
    """
    # Check for OAuth denial
    if request.GET.get("error") == "access_denied":
        messages.error(request, f"{provider_name} authorization was cancelled.")
        return None, redirect("integrations:integrations_home")

    # Get code and state from query params
    code = request.GET.get("code")
    state = request.GET.get("state")

    # Validate parameters
    if not code:
        messages.error(request, f"Missing authorization code from {provider_name}.")
        return None, redirect("integrations:integrations_home")

    if not state:
        messages.error(request, f"Missing state parameter from {provider_name}.")
        return None, redirect("integrations:integrations_home")

    # Verify state
    try:
        state_data = verify_state_func(state)
        team_id = state_data.get("team_id")

        # Verify team_id matches current team
        if team_id != team.id:
            messages.error(request, "Invalid state parameter.")
            return None, redirect("integrations:integrations_home")
    except oauth_error_class:
        messages.error(request, "Invalid state parameter.")
        return None, redirect("integrations:integrations_home")

    return code, None


def _create_github_integration(team, credential, org):
    """Create a GitHub integration for a team.

    Args:
        team: The team to create the integration for.
        credential: The IntegrationCredential to associate.
        org: Dictionary with 'login' and 'id' keys for the GitHub organization.

    Returns:
        GitHubIntegration: The created integration object.
    """
    return GitHubIntegration.objects.create(
        team=team,
        credential=credential,
        organization_slug=org["login"],
        organization_id=org["id"],
        webhook_secret=secrets.token_urlsafe(32),
    )


def _sync_github_members_after_connection(team, access_token, org_slug):
    """Sync GitHub organization members after connecting an integration.

    This is called after successfully creating a GitHubIntegration to import
    team members from the GitHub organization.

    Args:
        team: The team to sync members for.
        access_token: The GitHub OAuth access token.
        org_slug: The GitHub organization slug.

    Returns:
        int: The number of members created, or 0 if sync fails.
    """
    try:
        result = member_sync.sync_github_members(team, access_token, org_slug)
        return result["created"]
    except Exception as e:
        # Log error but don't fail the OAuth flow
        logger.error(f"Failed to sync GitHub members for team {team.slug}: {e}")
        return 0
