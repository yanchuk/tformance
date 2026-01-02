"""GitHub App webhook handlers for installation events."""

import logging

from django.utils import timezone

from apps.integrations.models import GitHubAppInstallation

logger = logging.getLogger(__name__)


def handle_installation_event(payload: dict) -> None:
    """Handle installation created/deleted/suspended/unsuspended events.

    Args:
        payload: The webhook payload from GitHub
    """
    action = payload.get("action")
    installation = payload.get("installation", {})
    installation_id = installation.get("id")

    if not installation_id:
        logger.warning("Missing installation ID in payload")
        return

    if action == "created":
        account = installation.get("account", {})
        GitHubAppInstallation.objects.create(
            installation_id=installation_id,
            account_type=account.get("type", ""),
            account_login=account.get("login", ""),
            account_id=account.get("id", 0),
            is_active=True,
            suspended_at=None,
            permissions=installation.get("permissions", {}),
            events=installation.get("events", []),
            repository_selection=installation.get("repository_selection", "selected"),
            team=None,  # Team is set later during onboarding callback
        )
        logger.info(f"Created GitHub App installation {installation_id} for {account.get('login')}")

    elif action == "deleted":
        try:
            inst = GitHubAppInstallation.objects.get(installation_id=installation_id)  # noqa: TEAM001 - Webhook lookup by installation_id
            inst.is_active = False
            inst.save(update_fields=["is_active", "updated_at"])
            logger.info(f"Marked GitHub App installation {installation_id} as inactive")
        except GitHubAppInstallation.DoesNotExist:
            logger.warning(f"Installation {installation_id} not found for deletion")

    elif action == "suspended":
        try:
            inst = GitHubAppInstallation.objects.get(installation_id=installation_id)  # noqa: TEAM001 - Webhook lookup by installation_id
            inst.is_active = False
            inst.suspended_at = timezone.now()
            inst.save(update_fields=["is_active", "suspended_at", "updated_at"])
            logger.info(f"Suspended GitHub App installation {installation_id}")
        except GitHubAppInstallation.DoesNotExist:
            logger.warning(f"Installation {installation_id} not found for suspension")

    elif action == "unsuspended":
        try:
            inst = GitHubAppInstallation.objects.get(installation_id=installation_id)  # noqa: TEAM001 - Webhook lookup by installation_id
            inst.is_active = True
            inst.suspended_at = None
            inst.save(update_fields=["is_active", "suspended_at", "updated_at"])
            logger.info(f"Unsuspended GitHub App installation {installation_id}")
        except GitHubAppInstallation.DoesNotExist:
            logger.warning(f"Installation {installation_id} not found for unsuspension")

    else:
        logger.debug(f"Ignoring unknown installation action: {action}")


def handle_installation_repositories_event(payload: dict) -> None:
    """Handle repositories added/removed from installation.

    Args:
        payload: The webhook payload from GitHub
    """
    action = payload.get("action")
    installation = payload.get("installation", {})
    installation_id = installation.get("id")

    if action == "added":
        repositories = payload.get("repositories_added", [])
        repo_names = [repo.get("full_name", "") for repo in repositories]
        logger.info(f"Repositories added to installation {installation_id}: {repo_names}")

    elif action == "removed":
        repositories = payload.get("repositories_removed", [])
        repo_names = [repo.get("full_name", "") for repo in repositories]
        logger.info(f"Repositories removed from installation {installation_id}: {repo_names}")

    else:
        logger.debug(f"Ignoring unknown installation_repositories action: {action}")
