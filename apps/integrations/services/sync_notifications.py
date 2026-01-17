"""Sync notification service for email notifications."""

from django.conf import settings
from django.core.mail import send_mail

from apps.integrations.models import TrackedRepository


def send_sync_complete_notification(tracked_repo: TrackedRepository, stats: dict) -> bool:
    """Send email notification when repository sync completes.

    Args:
        tracked_repo: The TrackedRepository that was synced
        stats: Dict with sync stats (prs, reviews, commits, etc.)

    Returns:
        True if email was sent, False if skipped (no user/email)
    """
    from apps.teams.models import Membership
    from apps.teams.roles import ROLE_ADMIN

    # Get user who connected the integration
    # For GitHub App: get from team's first admin
    # For OAuth: get from credential's connected_by
    user = None

    if tracked_repo.app_installation:
        # Get the first admin of the team
        admin_membership = (
            Membership.objects.filter(team=tracked_repo.team, role=ROLE_ADMIN).select_related("user").first()
        )
        if admin_membership:
            user = admin_membership.user
    elif tracked_repo.integration and tracked_repo.integration.credential:
        user = tracked_repo.integration.credential.connected_by

    if not user or not user.email:
        return False

    # Build email content
    subject = f"Your repository {tracked_repo.full_name} is ready"

    # Simple text message with stats
    message = f"""Hi {user.first_name or "there"},

Great news! Your repository {tracked_repo.full_name} has been synced and is ready to view.

Sync Summary:
- Pull Requests: {stats.get("prs", 0)}
- Reviews: {stats.get("reviews", 0)}
- Commits: {stats.get("commits", 0)}

View your dashboard to see insights from your repository data.

Thanks,
The tformance Team
"""

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )

    return True
