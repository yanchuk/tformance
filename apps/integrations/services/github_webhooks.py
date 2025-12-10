"""GitHub webhook service for managing repository webhooks."""

import hashlib
import hmac

import requests

from apps.integrations.services.github_oauth import (
    GITHUB_API_BASE_URL,
    GITHUB_API_VERSION,
    GitHubOAuthError,
)


def _get_github_api_headers(access_token: str) -> dict[str, str]:
    """Build standard GitHub API headers with authentication.

    Args:
        access_token: The GitHub access token

    Returns:
        Dictionary of headers for GitHub API requests
    """
    return {
        "Authorization": f"token {access_token}",
        "Accept": GITHUB_API_VERSION,
    }


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
    url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/hooks"
    headers = _get_github_api_headers(access_token)
    payload = {
        "name": "web",
        "active": True,
        "events": ["pull_request", "pull_request_review"],
        "config": {
            "url": webhook_url,
            "content_type": "json",
            "secret": secret,
            "insecure_ssl": "0",
        },
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 201:
        return response.json()["id"]

    if response.status_code == 403:
        raise GitHubOAuthError(f"Insufficient permissions to create webhook for {repo_full_name}")
    if response.status_code == 404:
        raise GitHubOAuthError(f"Repository not found: {repo_full_name}")

    raise GitHubOAuthError(f"Failed to create webhook for {repo_full_name}: HTTP {response.status_code}")


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
    url = f"{GITHUB_API_BASE_URL}/repos/{repo_full_name}/hooks/{webhook_id}"
    headers = _get_github_api_headers(access_token)

    response = requests.delete(url, headers=headers)

    if response.status_code in [204, 404]:
        return True

    if response.status_code == 403:
        raise GitHubOAuthError(f"Insufficient permissions to delete webhook from {repo_full_name}")

    raise GitHubOAuthError(f"Failed to delete webhook from {repo_full_name}: HTTP {response.status_code}")


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
