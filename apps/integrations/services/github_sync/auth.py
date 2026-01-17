"""Authentication helpers for GitHub sync.

Provides unified access token retrieval that supports both GitHub App
installations and legacy OAuth credentials.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.integrations.models import TrackedRepository


def get_access_token(tracked_repo: TrackedRepository) -> str:
    """Get access token, preferring App installation over OAuth.

    This function provides a unified way to get GitHub API credentials
    regardless of whether the repository was added via GitHub App or OAuth.

    Priority:
    1. GitHub App installation token (preferred - supports "no code access")
    2. OAuth credential token (legacy path)

    Args:
        tracked_repo: TrackedRepository instance

    Returns:
        Valid access token string

    Raises:
        GitHubAuthError: If no valid authentication method is available
    """
    from apps.integrations.exceptions import GitHubAuthError

    # Prefer App installation token (supports "no code access" claim)
    if tracked_repo.app_installation:
        return tracked_repo.app_installation.get_access_token()

    # Fall back to OAuth credential (deprecated path)
    if tracked_repo.integration and tracked_repo.integration.credential:
        return tracked_repo.integration.credential.access_token

    # Neither available - raise explicit error
    raise GitHubAuthError(
        f"Repository {tracked_repo.full_name} has no valid authentication. "
        f"Please re-add the repository via Integrations settings."
    )
