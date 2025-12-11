"""GitHub webhook service for managing repository webhooks."""

import hashlib
import hmac

from github import Github, GithubException, UnknownObjectException

from apps.integrations.services.github_oauth import GitHubOAuthError


def create_repository_webhook(access_token: str, repo_full_name: str, webhook_url: str, secret: str) -> int:
    """Create a webhook for a GitHub repository.

    Args:
        access_token: The GitHub access token
        repo_full_name: Full repository name (e.g., 'owner/repo')
        webhook_url: The URL to send webhook events to
        secret: Secret for webhook signature validation

    Returns:
        The webhook ID from GitHub

    Raises:
        GitHubOAuthError: If webhook creation fails
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get the repository
        repo = github.get_repo(repo_full_name)

        # Create the webhook
        hook = repo.create_hook(
            name="web",
            config={
                "url": webhook_url,
                "content_type": "json",
                "secret": secret,
                "insecure_ssl": "0",
            },
            events=["pull_request", "pull_request_review"],
            active=True,
        )

        return hook.id

    except UnknownObjectException as e:
        raise GitHubOAuthError(f"Repository not found: {e.status} - {e.data}") from e
    except GithubException as e:
        if e.status == 403:
            raise GitHubOAuthError(f"Insufficient permissions to create webhook for {repo_full_name}") from e
        if e.status == 404:
            raise GitHubOAuthError(f"Repository not found: {repo_full_name}") from e

        raise GitHubOAuthError(f"Failed to create webhook for {repo_full_name}: {e.status} - {e.data}") from e


def delete_repository_webhook(access_token: str, repo_full_name: str, webhook_id: int) -> bool:
    """Delete a webhook from a GitHub repository.

    Args:
        access_token: The GitHub access token
        repo_full_name: Full repository name (e.g., 'owner/repo')
        webhook_id: The ID of the webhook to delete

    Returns:
        True if deleted successfully or webhook doesn't exist (404)

    Raises:
        GitHubOAuthError: If webhook deletion fails (except 404)
    """
    try:
        # Create Github client with access token
        github = Github(access_token)

        # Get the repository
        repo = github.get_repo(repo_full_name)

        # Get the hook
        hook = repo.get_hook(webhook_id)

        # Delete the hook - returns None on success
        hook.delete()

        return True

    except UnknownObjectException:
        # Webhook doesn't exist (404) - already deleted, return True (idempotent)
        return True
    except GithubException as e:
        if e.status == 403:
            raise GitHubOAuthError(f"Insufficient permissions to delete webhook from {repo_full_name}") from e

        raise GitHubOAuthError(f"Failed to delete webhook from {repo_full_name}: {e.status} - {e.data}") from e


def validate_webhook_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """Validate the signature of a GitHub webhook payload.

    Uses HMAC-SHA256 to verify the X-Hub-Signature-256 header.

    Args:
        payload: The raw webhook payload bytes
        signature_header: The X-Hub-Signature-256 header value
        secret: The webhook secret used to sign the payload

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    try:
        # Extract the signature hash from the header
        signature_hash = signature_header[7:]  # Remove "sha256=" prefix

        # Calculate the expected signature
        mac = hmac.new(secret.encode(), msg=payload, digestmod=hashlib.sha256)
        expected_hash = mac.hexdigest()

        # Use timing-safe comparison
        return hmac.compare_digest(signature_hash, expected_hash)
    except Exception:
        return False
