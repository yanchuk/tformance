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
        account_id = account.get("id", 0)

        # Edge case #6: Check for old installation with same account_id (reinstall scenario)
        # If found, migrate team and TrackedRepository records to new installation
        old_installation = None
        team = None
        if account_id:
            old_installation = (
                GitHubAppInstallation.objects.filter(  # noqa: TEAM001 - Webhook lookup by account_id
                    account_id=account_id,
                )
                .exclude(installation_id=installation_id)
                .first()
            )

            if old_installation:
                team = old_installation.team
                # Deactivate old installation
                old_installation.is_active = False
                old_installation.save(update_fields=["is_active", "updated_at"])
                logger.info(f"Deactivated old installation {old_installation.installation_id} for account {account_id}")

        # EC-13: Check for account type changes before update
        # This can happen when a GitHub user converts to an organization
        new_account_type = account.get("type", "")
        existing_installation = GitHubAppInstallation.objects.filter(  # noqa: TEAM001 - Webhook lookup
            installation_id=installation_id
        ).first()
        if existing_installation and existing_installation.account_type != new_account_type:
            logger.warning(
                f"Account type changed for installation {installation_id}: "
                f"'{existing_installation.account_type}' → '{new_account_type}' "
                f"(account: {account.get('login')}). This may require admin attention."
            )

        # EC-11: Use update_or_create to handle duplicate webhooks gracefully
        # When user cancels/retries install flow, or GitHub retries webhook,
        # we may receive "created" event for an installation_id that already exists.
        defaults = {
            "account_type": new_account_type,
            "account_login": account.get("login", ""),
            "account_id": account_id,
            "is_active": True,
            "suspended_at": None,
            "permissions": installation.get("permissions", {}),
            "events": installation.get("events", []),
            "repository_selection": installation.get("repository_selection", "selected"),
        }
        # Only set team if we have one from reinstall scenario - don't override existing team with None
        if team:
            defaults["team"] = team

        new_installation, created = GitHubAppInstallation.objects.update_or_create(
            installation_id=installation_id,
            defaults=defaults,
        )
        if created:
            logger.info(f"Created GitHub App installation {installation_id} for {account.get('login')}")
        else:
            logger.info(f"Updated existing GitHub App installation {installation_id} for {account.get('login')}")

        # Migrate TrackedRepository records from old installation to new
        if old_installation:
            from apps.integrations.models import TrackedRepository

            migrated_count = TrackedRepository.objects.filter(  # noqa: TEAM001 - Webhook cross-team migration
                app_installation=old_installation
            ).update(app_installation=new_installation)
            if migrated_count:
                logger.info(f"Migrated {migrated_count} tracked repositories to new installation {installation_id}")

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
